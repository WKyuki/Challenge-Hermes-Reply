#!/usr/bin/env python3
"""
Smart Maintenance SaaS - Sistema Integrado
==========================================

Script principal para executar todo o sistema integrado:
- Data Ingestion Service (MQTT)
- ETL Pipeline 
- ML Pipeline
- Dashboard (Streamlit)

Uso:
    python run_integrated_system.py --mode all
    python run_integrated_system.py --mode dashboard
    python run_integrated_system.py --mode etl
    python run_integrated_system.py --mode ingestion

Autor: Challenge Hermes Reply Team
"""

import sys
import os
import argparse
import subprocess
import threading
import time
import logging
import signal
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

# Adicionar diretório atual ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Importar nossos módulos
from data_ingestion_service import DataIngestionService
from etl_pipeline import SmartMaintenanceETLPipeline
from ml_pipeline import SmartMaintenanceMLPipeline

# ===========================================
# CONFIGURAÇÕES
# ===========================================

SYSTEM_CONFIG = {
    'log_level': logging.INFO,
    'startup_delay': 5,  # segundos entre inicializações de componentes
    'shutdown_timeout': 30,  # timeout para shutdown graceful
}

# ===========================================
# CLASSE PRINCIPAL - ORQUESTRADOR
# ===========================================

class SmartMaintenanceOrchestrator:
    """
    Orquestrador principal do sistema Smart Maintenance SaaS
    """
    
    def __init__(self):
        self.setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Componentes do sistema
        self.data_ingestion = None
        self.etl_pipeline = None
        self.ml_pipeline = None
        self.dashboard_process = None
        
        # Controle
        self.is_running = False
        self.services_threads = []
        
        self.logger.info("Smart Maintenance Orchestrator inicializado")
    
    def setup_logging(self):
        """Configurar logging"""
        logging.basicConfig(
            level=SYSTEM_CONFIG['log_level'],
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f'/tmp/smart_maintenance_{datetime.now().strftime("%Y%m%d")}.log'),
                logging.StreamHandler()
            ]
        )
    
    def check_dependencies(self) -> bool:
        """Verificar dependências do sistema"""
        try:
            self.logger.info("Verificando dependências...")
            
            # Verificar imports principais
            required_modules = [
                'pandas', 'numpy', 'streamlit', 'plotly', 'sklearn', 
                'paho.mqtt.client', 'cx_Oracle', 'sqlalchemy'
            ]
            
            missing_modules = []
            for module in required_modules:
                try:
                    __import__(module)
                except ImportError:
                    missing_modules.append(module)
            
            if missing_modules:
                self.logger.error(f"Módulos ausentes: {', '.join(missing_modules)}")
                self.logger.error("Execute: pip install -r requirements.txt")
                return False
            
            # Verificar estrutura de diretórios
            required_dirs = ['logs', 'models', 'data', 'reports']
            for dir_name in required_dirs:
                Path(dir_name).mkdir(exist_ok=True)
            
            self.logger.info("Todas as dependências verificadas com sucesso")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro na verificação de dependências: {str(e)}")
            return False
    
    def start_data_ingestion(self) -> bool:
        """Iniciar serviço de ingestão de dados"""
        try:
            self.logger.info("Iniciando Data Ingestion Service...")
            
            self.data_ingestion = DataIngestionService()
            
            def run_ingestion():
                if self.data_ingestion.start():
                    self.logger.info("Data Ingestion Service rodando")
                    while self.is_running:
                        time.sleep(1)
                    self.data_ingestion.stop()
                else:
                    self.logger.error("Falha ao iniciar Data Ingestion Service")
            
            thread = threading.Thread(target=run_ingestion, daemon=True)
            thread.start()
            self.services_threads.append(thread)
            
            time.sleep(SYSTEM_CONFIG['startup_delay'])
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao iniciar Data Ingestion: {str(e)}")
            return False
    
    def start_etl_pipeline(self) -> bool:
        """Iniciar ETL Pipeline"""
        try:
            self.logger.info("Iniciando ETL Pipeline...")
            
            self.etl_pipeline = SmartMaintenanceETLPipeline()
            
            def run_etl():
                if self.etl_pipeline.start():
                    self.logger.info("ETL Pipeline rodando")
                    while self.is_running:
                        time.sleep(1)
                    self.etl_pipeline.stop()
                else:
                    self.logger.error("Falha ao iniciar ETL Pipeline")
            
            thread = threading.Thread(target=run_etl, daemon=True)
            thread.start()
            self.services_threads.append(thread)
            
            time.sleep(SYSTEM_CONFIG['startup_delay'])
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao iniciar ETL Pipeline: {str(e)}")
            return False
    
    def start_ml_pipeline(self) -> bool:
        """Iniciar ML Pipeline (treinamento inicial)"""
        try:
            self.logger.info("Iniciando ML Pipeline (treinamento inicial)...")
            
            self.ml_pipeline = SmartMaintenanceMLPipeline()
            
            def run_initial_training():
                success = self.ml_pipeline.run_full_pipeline()
                if success:
                    self.logger.info("Treinamento inicial ML concluído")
                else:
                    self.logger.warning("Falha no treinamento inicial ML")
            
            thread = threading.Thread(target=run_initial_training, daemon=True)
            thread.start()
            self.services_threads.append(thread)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao iniciar ML Pipeline: {str(e)}")
            return False
    
    def start_dashboard(self) -> bool:
        """Iniciar Dashboard Streamlit"""
        try:
            self.logger.info("Iniciando Dashboard Streamlit...")
            
            dashboard_script = Path(__file__).parent / "dashboard_alerts.py"
            
            if not dashboard_script.exists():
                self.logger.error("Script do dashboard não encontrado")
                return False
            
            # Iniciar Streamlit em subprocesso
            cmd = [
                sys.executable, "-m", "streamlit", "run", 
                str(dashboard_script),
                "--server.port", "8501",
                "--server.address", "0.0.0.0",
                "--server.headless", "true"
            ]
            
            self.dashboard_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            time.sleep(SYSTEM_CONFIG['startup_delay'])
            
            # Verificar se processo está rodando
            if self.dashboard_process.poll() is None:
                self.logger.info("Dashboard Streamlit iniciado em http://localhost:8501")
                return True
            else:
                self.logger.error("Falha ao iniciar Dashboard")
                return False
            
        except Exception as e:
            self.logger.error(f"Erro ao iniciar Dashboard: {str(e)}")
            return False
    
    def generate_test_data(self) -> bool:
        """Gerar dados de teste para demonstração"""
        try:
            self.logger.info("Gerando dados de teste...")
            
            # Script para gerar dados simulados
            test_data_script = """
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import cx_Oracle
from sqlalchemy import create_engine

# Configuração do banco
DB_CONFIG = {
    'user': 'your_db_user',
    'password': 'your_db_password',
    'dsn': 'localhost:1521/xe'
}

def generate_sample_data():
    # Gerar dados sintéticos
    n_records = 500
    n_equipment = 5
    
    data = []
    start_time = datetime.now() - timedelta(hours=24)
    
    for i in range(n_records):
        for eq_id in range(1, n_equipment + 1):
            timestamp = start_time + timedelta(minutes=i*3)
            
            # Simular diferentes condições
            base_temp = 70 + eq_id * 5
            temp_variation = np.sin(i * 0.1) * 10 + np.random.normal(0, 3)
            temperature = base_temp + temp_variation
            
            # Simular falha ocasional
            fault_probability = 0.05
            if temperature > 95:
                fault_probability = 0.8
            
            is_fault = np.random.random() < fault_probability
            
            record = {
                'id_sensor': f'SENS_{eq_id:03d}',
                'id_maquina': f'PUMP_{eq_id:03d}',
                'dataHora_medicao': timestamp,
                'vl_temperatura': temperature,
                'vl_pressao': np.random.normal(1013, 20),
                'vl_vibracao': np.random.exponential(2),
                'vl_humidade': np.random.uniform(30, 80),
                'vl_vibr_x': np.random.normal(0, 2),
                'vl_vibr_y': np.random.normal(0, 2),
                'vl_vibr_z': np.random.normal(9.8, 1),
                'vl_gyro_x': np.random.normal(0, 0.5),
                'vl_gyro_y': np.random.normal(0, 0.5),
                'vl_gyro_z': np.random.normal(0, 0.1),
                'flag_falha': 'S' if is_fault else 'N',
                'fonte_dados': 'SIMULACAO'
            }
            
            data.append(record)
    
    return pd.DataFrame(data)

# Executar se chamado diretamente
if __name__ == "__main__":
    df = generate_sample_data()
    print(f"Gerados {len(df)} registros de teste")
    
    # Salvar CSV
    df.to_csv('test_data.csv', index=False)
    print("Dados salvos em test_data.csv")
"""
            
            # Salvar script temporário
            test_script_path = Path("/tmp/generate_test_data.py")
            with open(test_script_path, 'w') as f:
                f.write(test_data_script)
            
            # Executar script
            result = subprocess.run([sys.executable, str(test_script_path)], 
                                 capture_output=True, text=True)
            
            if result.returncode == 0:
                self.logger.info("Dados de teste gerados com sucesso")
                return True
            else:
                self.logger.error(f"Erro ao gerar dados: {result.stderr}")
                return False
            
        except Exception as e:
            self.logger.error(f"Erro ao gerar dados de teste: {str(e)}")
            return False
    
    def start_system(self, mode: str = "all") -> bool:
        """Iniciar sistema completo ou componentes específicos"""
        try:
            self.logger.info(f"=== Iniciando Smart Maintenance System (modo: {mode}) ===")
            
            if not self.check_dependencies():
                return False
            
            self.is_running = True
            
            # Inicializar componentes baseado no modo
            success = True
            
            if mode in ["all", "ingestion"]:
                success &= self.start_data_ingestion()
            
            if mode in ["all", "etl"]:
                success &= self.start_etl_pipeline()
            
            if mode in ["all", "ml"]:
                success &= self.start_ml_pipeline()
            
            if mode in ["all", "dashboard"]:
                success &= self.start_dashboard()
            
            # Gerar dados de teste se necessário
            if mode == "demo":
                success &= self.generate_test_data()
                success &= self.start_dashboard()
            
            if success:
                self.logger.info("Sistema iniciado com sucesso!")
                self.print_system_status()
                return True
            else:
                self.logger.error("Falha na inicialização de alguns componentes")
                return False
            
        except Exception as e:
            self.logger.error(f"Erro ao iniciar sistema: {str(e)}")
            return False
    
    def print_system_status(self):
        """Imprimir status do sistema"""
        print("\n" + "="*60)
        print("         SMART MAINTENANCE SAAS - SISTEMA ATIVO")
        print("="*60)
        print("🏭 Sistema de Manutenção Preditiva Industrial")
        print("")
        print("Componentes ativos:")
        if self.data_ingestion:
            print("  ✅ Data Ingestion Service (MQTT)")
        if self.etl_pipeline:
            print("  ✅ ETL Pipeline")
        if self.ml_pipeline:
            print("  ✅ ML Pipeline")
        if self.dashboard_process and self.dashboard_process.poll() is None:
            print("  ✅ Dashboard Web: http://localhost:8501")
        
        print("")
        print("Logs disponíveis em:")
        print("  📄 /tmp/smart_maintenance_*.log")
        print("  📊 ./logs/")
        print("")
        print("Para parar o sistema: Ctrl+C")
        print("="*60)
    
    def stop_system(self):
        """Parar sistema gracefully"""
        self.logger.info("Parando Smart Maintenance System...")
        
        self.is_running = False
        
        # Parar componentes
        if self.data_ingestion:
            self.data_ingestion.stop()
        
        if self.etl_pipeline:
            self.etl_pipeline.stop()
        
        # Parar dashboard
        if self.dashboard_process:
            self.dashboard_process.terminate()
            try:
                self.dashboard_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.dashboard_process.kill()
        
        # Aguardar threads
        for thread in self.services_threads:
            thread.join(timeout=SYSTEM_CONFIG['shutdown_timeout'])
        
        self.logger.info("Sistema parado")

# ===========================================
# HANDLERS DE SINAL
# ===========================================

orchestrator = None

def signal_handler(signum, frame):
    """Handler para sinais de interrupção"""
    global orchestrator
    if orchestrator:
        orchestrator.stop_system()
    sys.exit(0)

# ===========================================
# MAIN - EXECUÇÃO PRINCIPAL
# ===========================================

def main():
    """Função principal"""
    global orchestrator
    
    parser = argparse.ArgumentParser(description="Smart Maintenance SaaS - Sistema Integrado")
    parser.add_argument(
        "--mode",
        choices=["all", "dashboard", "etl", "ingestion", "ml", "demo"],
        default="all",
        help="Modo de execução"
    )
    parser.add_argument(
        "--test-data",
        action="store_true",
        help="Gerar dados de teste"
    )
    
    args = parser.parse_args()
    
    # Configurar handlers de sinal
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Criar orquestrador
    orchestrator = SmartMaintenanceOrchestrator()
    
    try:
        # Gerar dados de teste se solicitado
        if args.test_data:
            orchestrator.generate_test_data()
            return
        
        # Iniciar sistema
        if orchestrator.start_system(args.mode):
            print("Sistema em execução. Pressione Ctrl+C para parar.")
            
            # Manter sistema rodando
            while True:
                time.sleep(1)
        else:
            print("Falha ao iniciar sistema")
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\nInterrupção detectada")
    except Exception as e:
        print(f"Erro inesperado: {str(e)}")
    finally:
        if orchestrator:
            orchestrator.stop_system()

if __name__ == "__main__":
    main()
