#!/usr/bin/env python3
"""
Smart Maintenance SaaS - Data Ingestion Service
============================================

Serviço Python para receber dados do ESP32 via MQTT e inserir no Oracle DB.
Funciona como ponte entre IoT e banco de dados.

Funcionalidades:
- Cliente MQTT para receber dados dos sensores
- Conexão Oracle Database
- Processamento e validação de dados JSON
- Inserção automática nas tabelas modeladas
- Logs detalhados e tratamento de erros
- Buffer local para garantir entrega dos dados

Autor: Challenge Hermes Reply Team
"""

import json
import logging
import time
import threading
from datetime import datetime
from typing import Dict, List, Optional
from queue import Queue
from dataclasses import dataclass

import paho.mqtt.client as mqtt
import cx_Oracle
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import pandas as pd
import schedule

# ===========================================
# CONFIGURAÇÕES
# ===========================================

# MQTT Configuration
MQTT_CONFIG = {
    'broker': 'broker.emqx.io',  # Broker público para testes
    'port': 1883,
    'topics': [
        'hermes/sensors/data',
        'hermes/sensors/status',
        'hermes/+/heartbeat'
    ],
    'client_id': 'hermes_ingestion_service',
    'keepalive': 60
}

# Database Configuration (ajuste conforme necessário)
DB_CONFIG = {
    'user': 'your_db_user',
    'password': 'your_db_password', 
    'dsn': 'localhost:1521/xe',  # Ajuste para seu Oracle DB
    'encoding': 'UTF-8'
}

# Sistema Configuration
SYSTEM_CONFIG = {
    'log_level': logging.INFO,
    'buffer_size': 1000,
    'batch_insert_size': 50,
    'processing_interval': 5,  # seconds
    'heartbeat_interval': 30,  # seconds
    'max_retries': 3
}

# ===========================================
# ESTRUTURAS DE DADOS
# ===========================================

@dataclass
class SensorReading:
    """Estrutura para dados de sensores"""
    device_id: str
    timestamp: datetime
    location: str
    equipment_type: str
    sensors: Dict[str, float]
    fault_detected: bool
    source: str = "MQTT"
    
    def to_dict(self) -> Dict:
        return {
            'device_id': self.device_id,
            'timestamp': self.timestamp,
            'location': self.location,
            'equipment_type': self.equipment_type,
            'sensors': self.sensors,
            'fault_detected': self.fault_detected,
            'source': self.source
        }

@dataclass  
class DatabaseStats:
    """Estatísticas do banco de dados"""
    total_records: int = 0
    records_today: int = 0
    last_insert: Optional[datetime] = None
    failed_inserts: int = 0
    active_devices: int = 0

# ===========================================
# CLASSE PRINCIPAL - DATA INGESTION SERVICE
# ===========================================

class DataIngestionService:
    """
    Serviço principal para ingestão de dados do MQTT para Oracle DB
    """
    
    def __init__(self):
        self.setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Componentes principais
        self.mqtt_client = None
        self.db_connection = None
        self.db_engine = None
        
        # Controle de dados
        self.data_queue = Queue(maxsize=SYSTEM_CONFIG['buffer_size'])
        self.stats = DatabaseStats()
        self.is_running = False
        
        # Threading
        self.processing_thread = None
        self.heartbeat_thread = None
        
        self.logger.info("Data Ingestion Service inicializado")
        
    def setup_logging(self):
        """Configurar sistema de logging"""
        logging.basicConfig(
            level=SYSTEM_CONFIG['log_level'],
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('/tmp/hermes_ingestion.log'),
                logging.StreamHandler()
            ]
        )
        
    def connect_database(self) -> bool:
        """Conectar ao Oracle Database"""
        try:
            # Usando cx_Oracle para conexão nativa
            dsn = cx_Oracle.makedsn(
                host=DB_CONFIG['dsn'].split(':')[0],
                port=int(DB_CONFIG['dsn'].split(':')[1].split('/')[0]),
                service_name=DB_CONFIG['dsn'].split('/')[-1]
            )
            
            self.db_connection = cx_Oracle.connect(
                user=DB_CONFIG['user'],
                password=DB_CONFIG['password'],
                dsn=dsn,
                encoding=DB_CONFIG['encoding']
            )
            
            # Criar engine SQLAlchemy para operações avançadas
            connection_string = f"oracle+cx_oracle://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['dsn']}"
            self.db_engine = create_engine(connection_string)
            
            self.logger.info("Conexão com Oracle Database estabelecida")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao conectar com banco de dados: {str(e)}")
            return False
    
    def connect_mqtt(self) -> bool:
        """Conectar ao broker MQTT"""
        try:
            self.mqtt_client = mqtt.Client(MQTT_CONFIG['client_id'])
            self.mqtt_client.on_connect = self.on_mqtt_connect
            self.mqtt_client.on_message = self.on_mqtt_message
            self.mqtt_client.on_disconnect = self.on_mqtt_disconnect
            
            self.mqtt_client.connect(
                MQTT_CONFIG['broker'], 
                MQTT_CONFIG['port'], 
                MQTT_CONFIG['keepalive']
            )
            
            self.mqtt_client.loop_start()
            self.logger.info("Cliente MQTT conectado e escutando")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao conectar MQTT: {str(e)}")
            return False
    
    def on_mqtt_connect(self, client, userdata, flags, rc):
        """Callback de conexão MQTT"""
        if rc == 0:
            self.logger.info("Conectado ao broker MQTT com sucesso")
            # Subscrever aos tópicos
            for topic in MQTT_CONFIG['topics']:
                client.subscribe(topic)
                self.logger.info(f"Subscrito ao tópico: {topic}")
        else:
            self.logger.error(f"Falha na conexão MQTT, código: {rc}")
    
    def on_mqtt_message(self, client, userdata, msg):
        """Callback de mensagem MQTT"""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            
            self.logger.debug(f"Mensagem recebida do tópico {topic}: {payload[:100]}...")
            
            # Processar diferentes tipos de mensagens
            if 'sensors/data' in topic:
                self.process_sensor_data(payload)
            elif 'heartbeat' in topic:
                self.process_heartbeat(payload)
            elif 'status' in topic:
                self.process_status_message(payload)
                
        except Exception as e:
            self.logger.error(f"Erro ao processar mensagem MQTT: {str(e)}")
    
    def on_mqtt_disconnect(self, client, userdata, rc):
        """Callback de desconexão MQTT"""
        self.logger.warning(f"Cliente MQTT desconectado, código: {rc}")
        
    def process_sensor_data(self, payload: str):
        """Processar dados de sensores recebidos via MQTT"""
        try:
            # Parse JSON
            data = json.loads(payload)
            
            # Validar estrutura básica
            required_fields = ['device_id', 'timestamp', 'sensors']
            if not all(field in data for field in required_fields):
                self.logger.warning(f"Dados incompletos recebidos: {data}")
                return
            
            # Converter timestamp
            if isinstance(data['timestamp'], str):
                timestamp = datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
            else:
                timestamp = datetime.fromtimestamp(data['timestamp'] / 1000)  # milissegundos
            
            # Criar objeto SensorReading
            sensor_reading = SensorReading(
                device_id=data['device_id'],
                timestamp=timestamp,
                location=data.get('location', 'Unknown'),
                equipment_type=data.get('equipment_type', 'Unknown'),
                sensors=data['sensors'],
                fault_detected=data.get('fault_detected', False)
            )
            
            # Adicionar à fila de processamento
            if not self.data_queue.full():
                self.data_queue.put(sensor_reading)
                self.logger.debug(f"Dados de {sensor_reading.device_id} adicionados à fila")
            else:
                self.logger.warning("Fila de dados cheia! Dados podem ser perdidos")
                
        except json.JSONDecodeError as e:
            self.logger.error(f"Erro ao decodificar JSON: {str(e)}")
        except Exception as e:
            self.logger.error(f"Erro ao processar dados de sensor: {str(e)}")
    
    def process_heartbeat(self, payload: str):
        """Processar heartbeat de dispositivos"""
        try:
            data = json.loads(payload)
            device_id = data.get('device_id', 'Unknown')
            self.logger.debug(f"Heartbeat recebido de {device_id}")
            # Aqui poderia atualizar status de conectividade dos dispositivos
        except Exception as e:
            self.logger.error(f"Erro ao processar heartbeat: {str(e)}")
    
    def process_status_message(self, payload: str):
        """Processar mensagens de status"""
        try:
            data = json.loads(payload)
            self.logger.info(f"Status recebido: {data}")
        except Exception as e:
            self.logger.error(f"Erro ao processar status: {str(e)}")
    
    def insert_sensor_data(self, reading: SensorReading) -> bool:
        """Inserir dados de sensor no banco de dados"""
        try:
            cursor = self.db_connection.cursor()
            
            # Determinar IDs de equipamento e sensor
            equipment_id = self.get_or_create_equipment(reading)
            sensor_id = self.get_or_create_sensor(reading)
            
            # Extrair valores dos sensores
            sensors = reading.sensors
            temperature = sensors.get('temperature', None)
            temperature_dht = sensors.get('temperature_dht', None)
            humidity = sensors.get('humidity', None)
            pressure = sensors.get('pressure', None)
            vibr_x = sensors.get('vibration_x', sensors.get('vibr_x', None))
            vibr_y = sensors.get('vibration_y', sensors.get('vibr_y', None))
            vibr_z = sensors.get('vibration_z', sensors.get('vibr_z', None))
            gyro_x = sensors.get('gyro_x', None)
            gyro_y = sensors.get('gyro_y', None)
            gyro_z = sensors.get('gyro_z', None)
            
            # Calcular vibração total se componentes disponíveis
            vibration_total = None
            if all(v is not None for v in [vibr_x, vibr_y, vibr_z]):
                vibration_total = (vibr_x**2 + vibr_y**2 + vibr_z**2)**0.5
            
            # Usar stored procedure para inserção
            cursor.callproc('SP_INSERT_MEDICAO', [
                sensor_id,                           # p_id_sensor
                equipment_id,                        # p_id_maquina  
                temperature,                         # p_temperatura
                pressure,                           # p_pressao
                vibration_total,                    # p_vibracao
                humidity,                           # p_humidade
                vibr_x,                            # p_vibr_x
                vibr_y,                            # p_vibr_y
                vibr_z,                            # p_vibr_z
                gyro_x,                            # p_gyro_x
                gyro_y,                            # p_gyro_y
                gyro_z,                            # p_gyro_z
                'S' if reading.fault_detected else 'N',  # p_flag_falha
                reading.source                      # p_fonte
            ])
            
            self.db_connection.commit()
            self.stats.total_records += 1
            self.stats.last_insert = datetime.now()
            
            self.logger.debug(f"Dados inseridos com sucesso para {reading.device_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao inserir dados no banco: {str(e)}")
            self.db_connection.rollback()
            self.stats.failed_inserts += 1
            return False
    
    def get_or_create_equipment(self, reading: SensorReading) -> str:
        """Obter ou criar equipamento"""
        equipment_id = reading.device_id.replace('ESP32_', '').replace('_', '') + '_EQ'
        
        cursor = self.db_connection.cursor()
        
        # Verificar se equipamento existe
        cursor.execute(
            "SELECT COUNT(*) FROM T_EQUIPAMENTO WHERE id_maquina = :1",
            [equipment_id]
        )
        
        if cursor.fetchone()[0] == 0:
            # Criar equipamento
            cursor.execute(
                """INSERT INTO T_EQUIPAMENTO 
                   (id_maquina, tipo_maquina, localizacao) 
                   VALUES (:1, :2, :3)""",
                [equipment_id, reading.equipment_type[:16], reading.location[:50]]
            )
            self.logger.info(f"Novo equipamento criado: {equipment_id}")
        
        cursor.close()
        return equipment_id
    
    def get_or_create_sensor(self, reading: SensorReading) -> str:
        """Obter ou criar sensor"""
        sensor_id = reading.device_id.replace('ESP32_', 'SENS_')
        
        cursor = self.db_connection.cursor()
        
        # Verificar se sensor existe  
        cursor.execute(
            "SELECT COUNT(*) FROM T_SENSOR WHERE id_sensor = :1",
            [sensor_id]
        )
        
        if cursor.fetchone()[0] == 0:
            # Criar sensor
            cursor.execute(
                """INSERT INTO T_SENSOR 
                   (id_sensor, tipo_sensor, unidade_medida) 
                   VALUES (:1, :2, :3)""",
                [sensor_id, 'ESP32_Multi', 'Mixed']
            )
            self.logger.info(f"Novo sensor criado: {sensor_id}")
        
        cursor.close()
        return sensor_id
    
    def data_processing_loop(self):
        """Loop principal de processamento de dados"""
        self.logger.info("Iniciando loop de processamento de dados")
        
        while self.is_running:
            try:
                # Processar dados em lotes
                batch = []
                batch_size = SYSTEM_CONFIG['batch_insert_size']
                
                # Coletar dados da fila
                while len(batch) < batch_size and not self.data_queue.empty():
                    try:
                        reading = self.data_queue.get(timeout=1)
                        batch.append(reading)
                    except:
                        break
                
                # Inserir lote no banco de dados
                if batch:
                    successful_inserts = 0
                    for reading in batch:
                        if self.insert_sensor_data(reading):
                            successful_inserts += 1
                    
                    self.logger.info(
                        f"Lote processado: {successful_inserts}/{len(batch)} inserções bem-sucedidas"
                    )
                
                # Aguardar próximo ciclo
                time.sleep(SYSTEM_CONFIG['processing_interval'])
                
            except Exception as e:
                self.logger.error(f"Erro no loop de processamento: {str(e)}")
                time.sleep(5)  # Esperar mais tempo em caso de erro
    
    def heartbeat_loop(self):
        """Loop de heartbeat e estatísticas"""
        self.logger.info("Iniciando loop de heartbeat")
        
        while self.is_running:
            try:
                # Atualizar estatísticas
                self.update_stats()
                
                # Log de status
                self.logger.info(
                    f"Status: {self.stats.total_records} registros total, "
                    f"{self.data_queue.qsize()} na fila, "
                    f"{self.stats.failed_inserts} falhas"
                )
                
                # Aguardar próximo heartbeat
                time.sleep(SYSTEM_CONFIG['heartbeat_interval'])
                
            except Exception as e:
                self.logger.error(f"Erro no heartbeat: {str(e)}")
                time.sleep(10)
    
    def update_stats(self):
        """Atualizar estatísticas do sistema"""
        try:
            if self.db_connection:
                cursor = self.db_connection.cursor()
                
                # Total de registros
                cursor.execute("SELECT COUNT(*) FROM T_MEDICAO")
                self.stats.total_records = cursor.fetchone()[0]
                
                # Registros de hoje
                cursor.execute(
                    """SELECT COUNT(*) FROM T_MEDICAO 
                       WHERE dataHora_medicao >= TRUNC(SYSDATE)"""
                )
                self.stats.records_today = cursor.fetchone()[0]
                
                # Dispositivos ativos (últimas 24h)
                cursor.execute(
                    """SELECT COUNT(DISTINCT id_maquina) FROM T_MEDICAO 
                       WHERE dataHora_medicao >= SYSDATE - 1"""
                )
                self.stats.active_devices = cursor.fetchone()[0]
                
                cursor.close()
                
        except Exception as e:
            self.logger.error(f"Erro ao atualizar estatísticas: {str(e)}")
    
    def start(self):
        """Iniciar o serviço"""
        self.logger.info("=== Iniciando Data Ingestion Service ===")
        
        # Conectar aos serviços
        if not self.connect_database():
            self.logger.error("Falha ao conectar com banco de dados. Abortando.")
            return False
            
        if not self.connect_mqtt():
            self.logger.error("Falha ao conectar com MQTT. Abortando.")
            return False
        
        # Iniciar threads
        self.is_running = True
        
        self.processing_thread = threading.Thread(target=self.data_processing_loop)
        self.processing_thread.start()
        
        self.heartbeat_thread = threading.Thread(target=self.heartbeat_loop)
        self.heartbeat_thread.start()
        
        self.logger.info("Serviço iniciado com sucesso")
        return True
    
    def stop(self):
        """Parar o serviço"""
        self.logger.info("Parando Data Ingestion Service...")
        
        self.is_running = False
        
        # Parar threads
        if self.processing_thread:
            self.processing_thread.join(timeout=10)
        if self.heartbeat_thread:
            self.heartbeat_thread.join(timeout=10)
        
        # Desconectar serviços
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
        
        if self.db_connection:
            self.db_connection.close()
        
        self.logger.info("Serviço parado")

# ===========================================
# FUNCÕES UTILITÁRIAS
# ===========================================

def simulate_sensor_data():
    """Função para simular dados de sensores (útil para testes)"""
    import random
    
    sample_data = {
        "device_id": "ESP32_HERMES_001",
        "timestamp": datetime.now().isoformat(),
        "location": "Factory_A",
        "equipment_type": "Pump",
        "sensors": {
            "temperature": round(random.uniform(20, 100), 2),
            "temperature_dht": round(random.uniform(20, 100), 2),
            "humidity": round(random.uniform(30, 80), 1),
            "pressure": round(random.uniform(950, 1050), 2),
            "vibration_x": round(random.uniform(-10, 10), 2),
            "vibration_y": round(random.uniform(-10, 10), 2),
            "vibration_z": round(random.uniform(8, 12), 2),
            "gyro_x": round(random.uniform(-5, 5), 2),
            "gyro_y": round(random.uniform(-5, 5), 2),
            "gyro_z": round(random.uniform(-1, 1), 2)
        },
        "fault_detected": random.choice([True, False]),
        "avg_temp_5min": round(random.uniform(20, 100), 2),
        "max_vibration_5min": round(random.uniform(5, 15), 2)
    }
    
    return json.dumps(sample_data)

# ===========================================
# MAIN - EXECUÇÃO PRINCIPAL
# ===========================================

if __name__ == "__main__":
    # Configurar logs
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Criar e iniciar serviço
    service = DataIngestionService()
    
    try:
        if service.start():
            logger.info("Serviço em execução. Pressione Ctrl+C para parar.")
            
            # Manter serviço em execução
            while True:
                time.sleep(1)
                
    except KeyboardInterrupt:
        logger.info("Interrupção detectada")
    except Exception as e:
        logger.error(f"Erro inesperado: {str(e)}")
    finally:
        service.stop()
        logger.info("Data Ingestion Service finalizado")
