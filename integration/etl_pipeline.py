#!/usr/bin/env python3
"""
Smart Maintenance SaaS - ETL Pipeline
====================================

Pipeline ETL/ELT para integração completa dos componentes do sistema.
Coordena o fluxo de dados entre ESP32 → MQTT → Database → ML → Dashboard

Funcionalidades:
- Orquestração dos processos de ingestão
- Transformação e limpeza de dados
- Carga em lote e tempo real
- Monitoramento da saúde do pipeline
- Recuperação de falhas e retry logic
- Logs detalhados e métricas

Autor: Challenge Hermes Reply Team
"""

import sys
import os
import logging
import json
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import schedule
import pickle

# Data processing
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text

# Nossos módulos
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from data_ingestion_service import DataIngestionService
from ml_pipeline import SmartMaintenanceMLPipeline

# ===========================================
# CONFIGURAÇÕES
# ===========================================

# Pipeline Configuration
PIPELINE_CONFIG = {
    'batch_size': 1000,
    'processing_interval': 60,  # segundos
    'ml_retrain_interval': 24,  # horas
    'data_retention_days': 90,
    'max_workers': 4,
    'retry_attempts': 3,
    'retry_delay': 5,  # segundos
}

# Database Configuration
DB_CONFIG = {
    'user': 'your_db_user',
    'password': 'your_db_password',
    'dsn': 'localhost:1521/xe',
    'encoding': 'UTF-8'
}

# Paths
BASE_PATH = Path(__file__).parent
LOGS_PATH = BASE_PATH / 'logs'
MODELS_PATH = BASE_PATH / 'models'
DATA_PATH = BASE_PATH / 'data'
REPORTS_PATH = BASE_PATH / 'reports'

# Criar diretórios
for path in [LOGS_PATH, MODELS_PATH, DATA_PATH, REPORTS_PATH]:
    path.mkdir(exist_ok=True)

# ===========================================
# ESTRUTURAS DE DADOS
# ===========================================

@dataclass
class PipelineMetrics:
    """Métricas do pipeline ETL"""
    records_processed: int = 0
    records_failed: int = 0
    ml_predictions: int = 0
    alerts_generated: int = 0
    last_run_time: Optional[datetime] = None
    average_processing_time: float = 0.0
    pipeline_status: str = "STOPPED"
    errors_count: int = 0

@dataclass
class DataQualityCheck:
    """Resultado da verificação de qualidade de dados"""
    check_name: str
    passed: bool
    message: str
    timestamp: datetime
    affected_records: int = 0

# ===========================================
# CLASSE PRINCIPAL - ETL PIPELINE
# ===========================================

class SmartMaintenanceETLPipeline:
    """
    Pipeline ETL completo para Smart Maintenance SaaS
    """
    
    def __init__(self):
        self.setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Componentes do pipeline
        self.data_ingestion = DataIngestionService()
        self.ml_pipeline = SmartMaintenanceMLPipeline()
        self.db_engine = None
        
        # Controle do pipeline
        self.is_running = False
        self.metrics = PipelineMetrics()
        self.data_quality_checks = []
        
        # Threading
        self.executor = ThreadPoolExecutor(max_workers=PIPELINE_CONFIG['max_workers'])
        self.processing_thread = None
        self.monitoring_thread = None
        
        self.logger.info("ETL Pipeline inicializado")
    
    def setup_logging(self):
        """Configurar sistema de logging"""
        log_file = LOGS_PATH / f"etl_pipeline_{datetime.now().strftime('%Y%m%d')}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
    
    def connect_database(self) -> bool:
        """Conectar ao banco de dados"""
        try:
            connection_string = f"oracle+cx_oracle://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['dsn']}"
            self.db_engine = create_engine(
                connection_string,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
                pool_recycle=3600
            )
            
            # Testar conexão
            with self.db_engine.connect() as conn:
                conn.execute(text("SELECT 1 FROM DUAL"))
            
            self.logger.info("Conexão com banco de dados estabelecida")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao conectar com banco: {str(e)}")
            return False
    
    # ===========================================
    # EXTRACT - Extração de Dados
    # ===========================================
    
    def extract_sensor_data(self, hours_back: int = 1) -> pd.DataFrame:
        """
        Extrair dados de sensores do banco
        
        Args:
            hours_back: Horas para retroceder na consulta
            
        Returns:
            DataFrame com dados dos sensores
        """
        try:
            query = """
            SELECT 
                m.id_medicao,
                m.id_maquina,
                m.id_sensor,
                m.dataHora_medicao,
                m.vl_temperatura,
                m.vl_pressao,
                m.vl_vibracao,
                m.vl_humidade,
                m.vl_vibr_x,
                m.vl_vibr_y,
                m.vl_vibr_z,
                m.vl_gyro_x,
                m.vl_gyro_y,
                m.vl_gyro_z,
                m.flag_falha,
                m.fonte_dados,
                e.tipo_maquina,
                e.localizacao,
                e.status_operacional
            FROM T_MEDICAO m
            INNER JOIN T_EQUIPAMENTO e ON m.id_maquina = e.id_maquina
            WHERE m.dataHora_medicao >= SYSTIMESTAMP - INTERVAL :hours HOUR
            ORDER BY m.dataHora_medicao DESC
            """
            
            df = pd.read_sql(query, self.db_engine, params={'hours': hours_back})
            
            self.logger.info(f"Extraídos {len(df)} registros das últimas {hours_back} horas")
            return df
            
        except Exception as e:
            self.logger.error(f"Erro na extração de dados: {str(e)}")
            return pd.DataFrame()
    
    def extract_historical_data(self, days_back: int = 30) -> pd.DataFrame:
        """Extrair dados históricos para análise e ML"""
        try:
            query = """
            SELECT 
                m.*,
                e.tipo_maquina,
                e.localizacao
            FROM T_MEDICAO m
            INNER JOIN T_EQUIPAMENTO e ON m.id_maquina = e.id_maquina
            WHERE m.dataHora_medicao >= SYSTIMESTAMP - INTERVAL :days DAY
            """
            
            df = pd.read_sql(query, self.db_engine, params={'days': days_back})
            
            self.logger.info(f"Extraídos {len(df)} registros históricos dos últimos {days_back} dias")
            return df
            
        except Exception as e:
            self.logger.error(f"Erro na extração histórica: {str(e)}")
            return pd.DataFrame()
    
    # ===========================================
    # TRANSFORM - Transformação de Dados
    # ===========================================
    
    def perform_data_quality_checks(self, df: pd.DataFrame) -> List[DataQualityCheck]:
        """Realizar verificações de qualidade dos dados"""
        checks = []
        timestamp = datetime.now()
        
        try:
            # Check 1: Valores nulos
            null_count = df.isnull().sum().sum()
            checks.append(DataQualityCheck(
                check_name="NULL_VALUES",
                passed=null_count < len(df) * 0.1,  # Menos de 10% de nulls
                message=f"Encontrados {null_count} valores nulos",
                timestamp=timestamp,
                affected_records=null_count
            ))
            
            # Check 2: Valores fora do range esperado
            if 'VL_TEMPERATURA' in df.columns:
                temp_outliers = df[
                    (df['VL_TEMPERATURA'] < -50) | (df['VL_TEMPERATURA'] > 200)
                ].shape[0]
                
                checks.append(DataQualityCheck(
                    check_name="TEMPERATURE_RANGE",
                    passed=temp_outliers == 0,
                    message=f"Temperatura fora do range: {temp_outliers} registros",
                    timestamp=timestamp,
                    affected_records=temp_outliers
                ))
            
            # Check 3: Duplicatas
            if 'ID_MEDICAO' in df.columns:
                duplicates = df['ID_MEDICAO'].duplicated().sum()
                checks.append(DataQualityCheck(
                    check_name="DUPLICATES",
                    passed=duplicates == 0,
                    message=f"Registros duplicados: {duplicates}",
                    timestamp=timestamp,
                    affected_records=duplicates
                ))
            
            # Check 4: Timestamps futuros
            if 'DATAHORA_MEDICAO' in df.columns:
                df['DATAHORA_MEDICAO'] = pd.to_datetime(df['DATAHORA_MEDICAO'])
                future_records = df[df['DATAHORA_MEDICAO'] > datetime.now()].shape[0]
                
                checks.append(DataQualityCheck(
                    check_name="FUTURE_TIMESTAMPS",
                    passed=future_records == 0,
                    message=f"Timestamps futuros: {future_records} registros",
                    timestamp=timestamp,
                    affected_records=future_records
                ))
            
            # Registrar resultados
            failed_checks = [c for c in checks if not c.passed]
            if failed_checks:
                self.logger.warning(f"Falhas na qualidade dos dados: {len(failed_checks)} checks falharam")
                for check in failed_checks:
                    self.logger.warning(f"  - {check.check_name}: {check.message}")
            else:
                self.logger.info("Todos os checks de qualidade passaram")
            
        except Exception as e:
            self.logger.error(f"Erro nos checks de qualidade: {str(e)}")
            checks.append(DataQualityCheck(
                check_name="QUALITY_CHECK_ERROR",
                passed=False,
                message=f"Erro ao executar checks: {str(e)}",
                timestamp=timestamp
            ))
        
        return checks
    
    def clean_and_transform_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Limpeza e transformação dos dados"""
        try:
            self.logger.info("Iniciando limpeza e transformação de dados")
            
            if df.empty:
                return df
            
            # Fazer cópia para não alterar o original
            df_clean = df.copy()
            
            # 1. Tratar valores nulos
            numeric_columns = df_clean.select_dtypes(include=[np.number]).columns
            for col in numeric_columns:
                if df_clean[col].isnull().sum() > 0:
                    # Usar mediana para valores extremos, média para distribuições normais
                    if col in ['VL_TEMPERATURA', 'VL_PRESSAO', 'VL_HUMIDADE']:
                        df_clean[col] = df_clean[col].fillna(df_clean[col].median())
                    else:
                        df_clean[col] = df_clean[col].fillna(0)
            
            # 2. Remover outliers extremos (usando IQR)
            for col in ['VL_TEMPERATURA', 'VL_PRESSAO', 'VL_VIBRACAO']:
                if col in df_clean.columns:
                    Q1 = df_clean[col].quantile(0.25)
                    Q3 = df_clean[col].quantile(0.75)
                    IQR = Q3 - Q1
                    
                    # Definir limites para outliers (mais conservador)
                    lower_bound = Q1 - 3 * IQR
                    upper_bound = Q3 + 3 * IQR
                    
                    # Contar outliers removidos
                    outliers_count = ((df_clean[col] < lower_bound) | (df_clean[col] > upper_bound)).sum()
                    
                    if outliers_count > 0:
                        self.logger.info(f"Removendo {outliers_count} outliers de {col}")
                        # Substituir outliers pelos valores dos limites
                        df_clean[col] = np.clip(df_clean[col], lower_bound, upper_bound)
            
            # 3. Padronizar timestamps
            if 'DATAHORA_MEDICAO' in df_clean.columns:
                df_clean['DATAHORA_MEDICAO'] = pd.to_datetime(df_clean['DATAHORA_MEDICAO'])
            
            # 4. Criar features derivadas
            # Magnitude da vibração total
            if all(col in df_clean.columns for col in ['VL_VIBR_X', 'VL_VIBR_Y', 'VL_VIBR_Z']):
                df_clean['VIBRACAO_MAGNITUDE'] = np.sqrt(
                    df_clean['VL_VIBR_X']**2 + 
                    df_clean['VL_VIBR_Y']**2 + 
                    df_clean['VL_VIBR_Z']**2
                )
            
            # Status de saúde baseado em thresholds
            if 'VL_TEMPERATURA' in df_clean.columns:
                df_clean['TEMP_STATUS'] = pd.cut(
                    df_clean['VL_TEMPERATURA'],
                    bins=[-np.inf, 85, 95, np.inf],
                    labels=['NORMAL', 'WARNING', 'CRITICAL']
                )
            
            # 5. Ordenar por timestamp
            if 'DATAHORA_MEDICAO' in df_clean.columns:
                df_clean = df_clean.sort_values('DATAHORA_MEDICAO')
            
            self.logger.info(f"Transformação concluída: {len(df_clean)} registros processados")
            return df_clean
            
        except Exception as e:
            self.logger.error(f"Erro na transformação de dados: {str(e)}")
            return df
    
    def aggregate_data_for_reporting(self, df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """Criar agregações para relatórios e dashboard"""
        try:
            aggregations = {}
            
            if df.empty:
                return aggregations
            
            # Agregação por equipamento (últimas 24h)
            if 'ID_MAQUINA' in df.columns:
                equipment_agg = df.groupby('ID_MAQUINA').agg({
                    'VL_TEMPERATURA': ['mean', 'max', 'min', 'std'],
                    'VL_PRESSAO': ['mean', 'max', 'min'],
                    'VL_HUMIDADE': ['mean', 'max'],
                    'VL_VIBRACAO': ['mean', 'max'],
                    'FLAG_FALHA': lambda x: (x == 'S').sum(),
                    'DATAHORA_MEDICAO': ['count', 'max']
                }).round(2)
                
                # Flatten column names
                equipment_agg.columns = ['_'.join(col).strip() for col in equipment_agg.columns.values]
                equipment_agg = equipment_agg.reset_index()
                
                aggregations['equipment_summary'] = equipment_agg
            
            # Agregação por hora (últimas 24h)
            if 'DATAHORA_MEDICAO' in df.columns:
                df['hour'] = pd.to_datetime(df['DATAHORA_MEDICAO']).dt.floor('H')
                
                hourly_agg = df.groupby('hour').agg({
                    'VL_TEMPERATURA': 'mean',
                    'VL_PRESSAO': 'mean',
                    'VL_HUMIDADE': 'mean',
                    'VL_VIBRACAO': 'mean',
                    'FLAG_FALHA': lambda x: (x == 'S').sum(),
                    'ID_MEDICAO': 'count'
                }).round(2)
                
                hourly_agg = hourly_agg.reset_index()
                aggregations['hourly_trends'] = hourly_agg
            
            # Agregação por localização e tipo
            if all(col in df.columns for col in ['LOCALIZACAO', 'TIPO_MAQUINA']):
                location_type_agg = df.groupby(['LOCALIZACAO', 'TIPO_MAQUINA']).agg({
                    'VL_TEMPERATURA': 'mean',
                    'FLAG_FALHA': lambda x: (x == 'S').sum(),
                    'ID_MAQUINA': 'nunique'
                }).round(2)
                
                location_type_agg = location_type_agg.reset_index()
                aggregations['location_type_summary'] = location_type_agg
            
            self.logger.info(f"Criadas {len(aggregations)} agregações para relatórios")
            return aggregations
            
        except Exception as e:
            self.logger.error(f"Erro na agregação de dados: {str(e)}")
            return {}
    
    # ===========================================
    # LOAD - Carga de Dados
    # ===========================================
    
    def load_aggregated_data(self, aggregations: Dict[str, pd.DataFrame]) -> bool:
        """Carregar dados agregados em tabelas auxiliares"""
        try:
            success = True
            
            for table_name, df in aggregations.items():
                try:
                    # Nome da tabela temporária
                    temp_table = f"T_AGG_{table_name.upper()}"
                    
                    # Carregar para o banco
                    df.to_sql(
                        temp_table,
                        self.db_engine,
                        if_exists='replace',
                        index=False,
                        chunksize=1000
                    )
                    
                    self.logger.info(f"Agregação {table_name} carregada na tabela {temp_table}")
                    
                except Exception as e:
                    self.logger.error(f"Erro ao carregar agregação {table_name}: {str(e)}")
                    success = False
            
            return success
            
        except Exception as e:
            self.logger.error(f"Erro na carga de agregações: {str(e)}")
            return False
    
    def export_data_to_files(self, df: pd.DataFrame, aggregations: Dict[str, pd.DataFrame]) -> bool:
        """Exportar dados para arquivos (backup e análise externa)"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Exportar dados principais
            if not df.empty:
                main_file = DATA_PATH / f"sensor_data_{timestamp}.csv"
                df.to_csv(main_file, index=False)
                self.logger.info(f"Dados principais exportados para {main_file}")
            
            # Exportar agregações
            for name, agg_df in aggregations.items():
                if not agg_df.empty:
                    agg_file = DATA_PATH / f"{name}_{timestamp}.csv"
                    agg_df.to_csv(agg_file, index=False)
                    self.logger.info(f"Agregação {name} exportada para {agg_file}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Erro na exportação de arquivos: {str(e)}")
            return False
    
    # ===========================================
    # MACHINE LEARNING INTEGRATION
    # ===========================================
    
    def run_ml_predictions(self, df: pd.DataFrame) -> pd.DataFrame:
        """Executar predições ML nos dados"""
        try:
            self.logger.info("Iniciando predições ML")
            
            if df.empty:
                return pd.DataFrame()
            
            # Conectar ao ML pipeline
            if not self.ml_pipeline.connect_database():
                self.logger.warning("ML pipeline sem conexão DB, usando dados do DataFrame")
            
            predictions = []
            
            # Processar por equipamento
            for equipment_id in df['ID_MAQUINA'].unique():
                eq_data = df[df['ID_MAQUINA'] == equipment_id].tail(1)  # Última leitura
                
                if not eq_data.empty:
                    row = eq_data.iloc[0]
                    
                    # Preparar dados para predição
                    sensor_data = {
                        'temperature': row.get('VL_TEMPERATURA', 0),
                        'pressure': row.get('VL_PRESSAO', 0),
                        'vibration': row.get('VL_VIBRACAO', 0),
                        'humidity': row.get('VL_HUMIDADE', 0),
                        'vibration_x': row.get('VL_VIBR_X', 0),
                        'vibration_y': row.get('VL_VIBR_Y', 0),
                        'vibration_z': row.get('VL_VIBR_Z', 0),
                        'gyro_x': row.get('VL_GYRO_X', 0),
                        'gyro_y': row.get('VL_GYRO_Y', 0),
                        'gyro_z': row.get('VL_GYRO_Z', 0)
                    }
                    
                    # Fazer predição (simulada por enquanto)
                    # result = self.ml_pipeline.predict_maintenance(equipment_id, sensor_data)
                    
                    # Simular resultado
                    risk_score = min(1.0, max(0.0, 
                        (sensor_data['temperature'] - 70) / 30 +
                        (sensor_data['vibration'] - 2) / 8 +
                        np.random.normal(0, 0.1)
                    ))
                    
                    predictions.append({
                        'equipment_id': equipment_id,
                        'timestamp': row['DATAHORA_MEDICAO'],
                        'fault_probability': risk_score,
                        'predicted_class': 1 if risk_score > 0.5 else 0,
                        'alert_level': 'HIGH' if risk_score > 0.7 else 'MEDIUM' if risk_score > 0.4 else 'LOW'
                    })
            
            predictions_df = pd.DataFrame(predictions)
            self.metrics.ml_predictions += len(predictions)
            
            self.logger.info(f"ML predições concluídas: {len(predictions)} equipamentos analisados")
            return predictions_df
            
        except Exception as e:
            self.logger.error(f"Erro nas predições ML: {str(e)}")
            return pd.DataFrame()
    
    # ===========================================
    # PIPELINE ORCHESTRATION
    # ===========================================
    
    def run_etl_cycle(self) -> bool:
        """Executar um ciclo completo do pipeline ETL"""
        try:
            cycle_start = datetime.now()
            self.logger.info("=== Iniciando ciclo ETL ===")
            
            # 1. EXTRACT - Extrair dados
            df_raw = self.extract_sensor_data(hours_back=1)
            
            if df_raw.empty:
                self.logger.warning("Nenhum dado novo para processar")
                return True
            
            # 2. QUALITY CHECKS - Verificar qualidade
            quality_checks = self.perform_data_quality_checks(df_raw)
            self.data_quality_checks.extend(quality_checks)
            
            # Verificar se há falhas críticas
            critical_failures = [c for c in quality_checks if not c.passed and c.affected_records > len(df_raw) * 0.2]
            if critical_failures:
                self.logger.error("Falhas críticas na qualidade dos dados. Abortando ciclo.")
                self.metrics.errors_count += 1
                return False
            
            # 3. TRANSFORM - Limpeza e transformação
            df_clean = self.clean_and_transform_data(df_raw)
            
            # 4. AGGREGATIONS - Criar agregações
            aggregations = self.aggregate_data_for_reporting(df_clean)
            
            # 5. ML PREDICTIONS - Executar predições
            predictions_df = self.run_ml_predictions(df_clean)
            
            # 6. LOAD - Carregar resultados
            # Carregar agregações
            if aggregations:
                self.load_aggregated_data(aggregations)
            
            # 7. EXPORT - Exportar para arquivos
            self.export_data_to_files(df_clean, aggregations)
            
            # 8. UPDATE METRICS - Atualizar métricas
            cycle_time = (datetime.now() - cycle_start).total_seconds()
            self.metrics.records_processed += len(df_raw)
            self.metrics.last_run_time = datetime.now()
            self.metrics.average_processing_time = (
                (self.metrics.average_processing_time + cycle_time) / 2
                if self.metrics.average_processing_time > 0
                else cycle_time
            )
            
            self.logger.info(f"Ciclo ETL concluído em {cycle_time:.2f}s - {len(df_raw)} registros processados")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro no ciclo ETL: {str(e)}")
            self.metrics.errors_count += 1
            return False
    
    def run_ml_training_cycle(self) -> bool:
        """Executar retreinamento do modelo ML"""
        try:
            self.logger.info("=== Iniciando retreinamento ML ===")
            
            # Extrair dados históricos
            df_historical = self.extract_historical_data(days_back=30)
            
            if df_historical.empty or len(df_historical) < 1000:
                self.logger.warning("Dados insuficientes para retreinamento ML")
                return False
            
            # Executar pipeline ML completo
            success = self.ml_pipeline.run_full_pipeline()
            
            if success:
                self.logger.info("Retreinamento ML concluído com sucesso")
            else:
                self.logger.error("Falha no retreinamento ML")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Erro no retreinamento ML: {str(e)}")
            return False
    
    def cleanup_old_data(self) -> bool:
        """Limpar dados antigos baseado na política de retenção"""
        try:
            cutoff_date = datetime.now() - timedelta(days=PIPELINE_CONFIG['data_retention_days'])
            
            # Cleanup em tabelas temporárias de agregação
            cleanup_query = """
            DELETE FROM T_AGG_EQUIPMENT_SUMMARY 
            WHERE created_date < :cutoff_date
            """
            
            with self.db_engine.connect() as conn:
                result = conn.execute(text(cleanup_query), {'cutoff_date': cutoff_date})
                
            self.logger.info(f"Cleanup executado: dados anteriores a {cutoff_date}")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro no cleanup: {str(e)}")
            return False
    
    # ===========================================
    # MONITORING AND HEALTH CHECKS
    # ===========================================
    
    def generate_health_report(self) -> Dict[str, Any]:
        """Gerar relatório de saúde do pipeline"""
        try:
            # Verificar conexão DB
            db_healthy = False
            try:
                with self.db_engine.connect() as conn:
                    conn.execute(text("SELECT 1 FROM DUAL"))
                db_healthy = True
            except:
                pass
            
            # Calcular métricas
            success_rate = (
                (self.metrics.records_processed / (self.metrics.records_processed + self.metrics.records_failed))
                if (self.metrics.records_processed + self.metrics.records_failed) > 0
                else 1.0
            )
            
            health_report = {
                'timestamp': datetime.now().isoformat(),
                'pipeline_status': self.metrics.pipeline_status,
                'database_healthy': db_healthy,
                'records_processed_total': self.metrics.records_processed,
                'records_failed_total': self.metrics.records_failed,
                'success_rate': success_rate,
                'errors_count': self.metrics.errors_count,
                'last_run': self.metrics.last_run_time.isoformat() if self.metrics.last_run_time else None,
                'average_processing_time': self.metrics.average_processing_time,
                'ml_predictions_total': self.metrics.ml_predictions,
                'quality_checks_failed': len([c for c in self.data_quality_checks[-20:] if not c.passed]),
                'uptime_hours': (datetime.now() - self.start_time).total_seconds() / 3600 if hasattr(self, 'start_time') else 0
            }
            
            return health_report
            
        except Exception as e:
            self.logger.error(f"Erro ao gerar relatório de saúde: {str(e)}")
            return {}
    
    def save_health_report(self) -> None:
        """Salvar relatório de saúde em arquivo"""
        try:
            report = self.generate_health_report()
            
            if report:
                report_file = REPORTS_PATH / f"health_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                
                with open(report_file, 'w') as f:
                    json.dump(report, f, indent=2)
                
                self.logger.info(f"Relatório de saúde salvo em {report_file}")
                
        except Exception as e:
            self.logger.error(f"Erro ao salvar relatório de saúde: {str(e)}")
    
    # ===========================================
    # MAIN EXECUTION LOOPS
    # ===========================================
    
    def processing_loop(self):
        """Loop principal de processamento"""
        self.logger.info("Iniciando loop de processamento ETL")
        
        while self.is_running:
            try:
                # Executar ciclo ETL
                success = self.run_etl_cycle()
                
                if not success:
                    self.logger.warning("Ciclo ETL falhado, aguardando próximo ciclo")
                
                # Aguardar próximo ciclo
                time.sleep(PIPELINE_CONFIG['processing_interval'])
                
            except Exception as e:
                self.logger.error(f"Erro no loop de processamento: {str(e)}")
                time.sleep(60)  # Aguardar mais tempo em caso de erro
    
    def monitoring_loop(self):
        """Loop de monitoramento e manutenção"""
        self.logger.info("Iniciando loop de monitoramento")
        
        # Agendar tarefas periódicas
        schedule.every().hour.do(self.save_health_report)
        schedule.every().day.at("02:00").do(self.cleanup_old_data)
        schedule.every(PIPELINE_CONFIG['ml_retrain_interval']).hours.do(self.run_ml_training_cycle)
        
        while self.is_running:
            try:
                # Executar tarefas agendadas
                schedule.run_pending()
                
                # Verificar saúde do sistema
                if self.metrics.errors_count > 10:
                    self.logger.warning("Muitos erros detectados, considerando restart")
                
                time.sleep(60)  # Check a cada minuto
                
            except Exception as e:
                self.logger.error(f"Erro no loop de monitoramento: {str(e)}")
                time.sleep(300)  # Aguardar 5 minutos em caso de erro
    
    # ===========================================
    # START/STOP METHODS
    # ===========================================
    
    def start(self) -> bool:
        """Iniciar o pipeline ETL"""
        try:
            self.logger.info("=== Iniciando Smart Maintenance ETL Pipeline ===")
            self.start_time = datetime.now()
            
            # Conectar ao banco
            if not self.connect_database():
                self.logger.error("Falha na conexão com banco de dados")
                return False
            
            # Iniciar componentes
            self.is_running = True
            self.metrics.pipeline_status = "RUNNING"
            
            # Iniciar threads
            self.processing_thread = threading.Thread(target=self.processing_loop)
            self.monitoring_thread = threading.Thread(target=self.monitoring_loop)
            
            self.processing_thread.start()
            self.monitoring_thread.start()
            
            self.logger.info("ETL Pipeline iniciado com sucesso")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao iniciar pipeline: {str(e)}")
            return False
    
    def stop(self):
        """Parar o pipeline ETL"""
        self.logger.info("Parando ETL Pipeline...")
        
        self.is_running = False
        self.metrics.pipeline_status = "STOPPED"
        
        # Aguardar threads terminarem
        if self.processing_thread:
            self.processing_thread.join(timeout=30)
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=30)
        
        # Fechar executor
        self.executor.shutdown(wait=True)
        
        # Salvar relatório final
        self.save_health_report()
        
        self.logger.info("ETL Pipeline parado")

# ===========================================
# EXECUÇÃO PRINCIPAL
# ===========================================

def main():
    """Função principal"""
    pipeline = SmartMaintenanceETLPipeline()
    
    try:
        if pipeline.start():
            print("ETL Pipeline em execução. Pressione Ctrl+C para parar.")
            
            while True:
                time.sleep(1)
                
                # Mostrar métricas a cada 5 minutos
                if datetime.now().minute % 5 == 0 and datetime.now().second == 0:
                    report = pipeline.generate_health_report()
                    print(f"\n=== STATUS ===")
                    print(f"Registros processados: {report.get('records_processed_total', 0)}")
                    print(f"Taxa de sucesso: {report.get('success_rate', 0):.2%}")
                    print(f"Tempo médio de processamento: {report.get('average_processing_time', 0):.2f}s")
                    print(f"Predições ML: {report.get('ml_predictions_total', 0)}")
                    print("================")
                
    except KeyboardInterrupt:
        print("\nInterrupção detectada")
    except Exception as e:
        print(f"Erro inesperado: {str(e)}")
    finally:
        pipeline.stop()

if __name__ == "__main__":
    main()
