#!/usr/bin/env python3
"""
Smart Maintenance SaaS - ML Pipeline Integrado
============================================

Pipeline de Machine Learning integrado com banco Oracle.
Funcionalidades:
- Extração de features do banco de dados
- Pré-processamento automatizado
- Treinamento de modelos (KNN, Random Forest, SVM)
- Inferência em tempo real
- Métricas e visualizações
- Sistema de alertas baseado em ML

Autor: Challenge Hermes Reply Team
"""

import numpy as np
import pandas as pd
import logging
import pickle
import json
import warnings
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass

# Data Science Libraries
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.preprocessing import StandardScaler, LabelEncoder, RobustScaler
from sklearn.neighbors import KNeighborsClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, classification_report, confusion_matrix,
    roc_auc_score, f1_score, precision_score, recall_score
)

# Visualização
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.dates import DateFormatter

# Database
import cx_Oracle
from sqlalchemy import create_engine, text
import warnings
warnings.filterwarnings('ignore')

# ===========================================
# CONFIGURAÇÕES
# ===========================================

# Database Configuration
DB_CONFIG = {
    'user': 'your_db_user',
    'password': 'your_db_password',
    'dsn': 'localhost:1521/xe',
    'encoding': 'UTF-8'
}

# ML Configuration
ML_CONFIG = {
    'test_size': 0.2,
    'random_state': 42,
    'cv_folds': 5,
    'model_path': './models/',
    'scaler_path': './models/scaler.pkl',
    'results_path': './results/'
}

# Feature Engineering
FEATURE_CONFIG = {
    'temperature_threshold': 95.0,
    'pressure_min': 960.0,
    'pressure_max': 1040.0,
    'humidity_threshold': 80.0,
    'vibration_threshold': 10.0,
    'window_size': 10,  # Para features temporais
    'lag_features': [1, 2, 5, 10]  # Lags para análise temporal
}

# ===========================================
# ESTRUTURAS DE DADOS
# ===========================================

@dataclass
class MLMetrics:
    """Métricas do modelo ML"""
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    auc_roc: float
    confusion_matrix: np.ndarray
    classification_report: str

@dataclass
class PredictionResult:
    """Resultado de predição"""
    equipment_id: str
    timestamp: datetime
    fault_probability: float
    predicted_class: int
    confidence: float
    features_used: Dict[str, float]
    alert_level: str  # LOW, MEDIUM, HIGH, CRITICAL

# ===========================================
# CLASSE PRINCIPAL - ML PIPELINE
# ===========================================

class SmartMaintenanceMLPipeline:
    """
    Pipeline completo de Machine Learning para Smart Maintenance
    """
    
    def __init__(self):
        self.setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Database connection
        self.db_connection = None
        self.db_engine = None
        
        # ML Components
        self.models = {}
        self.scaler = None
        self.feature_columns = []
        self.label_encoder = None
        
        # Data
        self.train_data = None
        self.test_data = None
        self.current_metrics = {}
        
        # Paths
        self.model_path = Path(ML_CONFIG['model_path'])
        self.results_path = Path(ML_CONFIG['results_path'])
        self.model_path.mkdir(exist_ok=True)
        self.results_path.mkdir(exist_ok=True)
        
        self.logger.info("ML Pipeline inicializado")
    
    def setup_logging(self):
        """Configurar sistema de logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('/tmp/hermes_ml.log'),
                logging.StreamHandler()
            ]
        )
    
    def connect_database(self) -> bool:
        """Conectar ao Oracle Database"""
        try:
            # Conexão nativa Oracle
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
            
            # SQLAlchemy engine para pandas
            connection_string = f"oracle+cx_oracle://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['dsn']}"
            self.db_engine = create_engine(connection_string)
            
            self.logger.info("Conexão com Oracle Database estabelecida")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao conectar com banco de dados: {str(e)}")
            return False
    
    def extract_features_from_db(self, 
                                days_back: int = 30,
                                include_synthetic: bool = True) -> pd.DataFrame:
        """
        Extrair features do banco de dados Oracle
        
        Args:
            days_back: Número de dias para retroceder na consulta
            include_synthetic: Incluir dados sintéticos para treinamento
        
        Returns:
            DataFrame com features preparadas para ML
        """
        try:
            self.logger.info(f"Extraindo features dos últimos {days_back} dias")
            
            # Query principal para dados de medições
            base_query = """
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
            WHERE m.dataHora_medicao >= SYSTIMESTAMP - INTERVAL '{days_back}' DAY
            ORDER BY m.dataHora_medicao
            """
            
            # Executar query
            df = pd.read_sql(base_query, self.db_engine)
            
            if df.empty:
                self.logger.warning("Nenhum dado encontrado na consulta")
                
                if include_synthetic:
                    # Usar dados sintéticos do Sprint 3
                    self.logger.info("Carregando dados sintéticos para treinamento")
                    df = self.load_synthetic_data()
                else:
                    return pd.DataFrame()
            
            # Preparar features
            df_features = self.prepare_features(df)
            
            self.logger.info(f"Features extraídas: {df_features.shape[0]} registros, {df_features.shape[1]} colunas")
            return df_features
            
        except Exception as e:
            self.logger.error(f"Erro ao extrair features: {str(e)}")
            return pd.DataFrame()
    
    def load_synthetic_data(self) -> pd.DataFrame:
        """Carregar dados sintéticos para treinamento inicial"""
        try:
            # Carregar dataset do Sprint 3
            synthetic_path = Path(__file__).parent.parent / 'assets' / 'Sprint_3-Dataset_maquinas_ind.csv'
            
            if synthetic_path.exists():
                df = pd.read_csv(synthetic_path)
                self.logger.info(f"Dados sintéticos carregados: {df.shape}")
                
                # Adaptar colunas para o formato do banco
                df_adapted = pd.DataFrame()
                df_adapted['id_medicao'] = range(len(df))
                df_adapted['id_maquina'] = df['equipment'].astype(str) + '_SYN'
                df_adapted['id_sensor'] = 'SYNTHETIC_001'
                df_adapted['dataHora_medicao'] = pd.date_range(
                    start='2024-01-01', periods=len(df), freq='H'
                )
                df_adapted['vl_temperatura'] = df['temperature']
                df_adapted['vl_pressao'] = df['pressure']
                df_adapted['vl_vibracao'] = df['vibration']
                df_adapted['vl_humidade'] = df['humidity']
                df_adapted['vl_vibr_x'] = df['vibration'] * 0.6
                df_adapted['vl_vibr_y'] = df['vibration'] * 0.3
                df_adapted['vl_vibr_z'] = df['vibration'] * 0.1
                df_adapted['vl_gyro_x'] = np.random.normal(0, 1, len(df))
                df_adapted['vl_gyro_y'] = np.random.normal(0, 1, len(df))
                df_adapted['vl_gyro_z'] = np.random.normal(0, 1, len(df))
                df_adapted['flag_falha'] = df['faulty'].map({1.0: 'S', 0.0: 'N'})
                df_adapted['fonte_dados'] = 'SYNTHETIC'
                df_adapted['tipo_maquina'] = df['equipment']
                df_adapted['localizacao'] = df['location']
                df_adapted['status_operacional'] = 'A'
                
                return df_adapted
                
            else:
                self.logger.warning("Arquivo de dados sintéticos não encontrado")
                return pd.DataFrame()
                
        except Exception as e:
            self.logger.error(f"Erro ao carregar dados sintéticos: {str(e)}")
            return pd.DataFrame()
    
    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Preparar features para ML (feature engineering)
        
        Args:
            df: DataFrame com dados brutos
            
        Returns:
            DataFrame com features processadas
        """
        try:
            self.logger.info("Iniciando feature engineering")
            
            # Fazer cópia para não alterar original
            df_features = df.copy()
            
            # ==========================================
            # 1. FEATURES BÁSICAS E LIMPEZA
            # ==========================================
            
            # Converter timestamp
            if 'dataHora_medicao' in df_features.columns:
                df_features['dataHora_medicao'] = pd.to_datetime(df_features['dataHora_medicao'])
            
            # Tratar valores nulos
            numeric_columns = ['vl_temperatura', 'vl_pressao', 'vl_vibracao', 'vl_humidade', 
                              'vl_vibr_x', 'vl_vibr_y', 'vl_vibr_z', 'vl_gyro_x', 'vl_gyro_y', 'vl_gyro_z']
            
            for col in numeric_columns:
                if col in df_features.columns:
                    df_features[col] = pd.to_numeric(df_features[col], errors='coerce')
                    df_features[col] = df_features[col].fillna(df_features[col].median())
            
            # ==========================================
            # 2. FEATURES DERIVADAS
            # ==========================================
            
            # Vibração total magnitude
            if all(col in df_features.columns for col in ['vl_vibr_x', 'vl_vibr_y', 'vl_vibr_z']):
                df_features['vibration_magnitude'] = np.sqrt(
                    df_features['vl_vibr_x']**2 + 
                    df_features['vl_vibr_y']**2 + 
                    df_features['vl_vibr_z']**2
                )
            
            # Gyro total magnitude
            if all(col in df_features.columns for col in ['vl_gyro_x', 'vl_gyro_y', 'vl_gyro_z']):
                df_features['gyro_magnitude'] = np.sqrt(
                    df_features['vl_gyro_x']**2 + 
                    df_features['vl_gyro_y']**2 + 
                    df_features['vl_gyro_z']**2
                )
            
            # ==========================================
            # 3. FEATURES TEMPORAIS (se temos dados suficientes)
            # ==========================================
            
            if 'dataHora_medicao' in df_features.columns and len(df_features) > 50:
                df_features = df_features.sort_values('dataHora_medicao')
                
                # Features de hora/dia
                df_features['hour'] = df_features['dataHora_medicao'].dt.hour
                df_features['day_of_week'] = df_features['dataHora_medicao'].dt.dayofweek
                
                # Rolling statistics (por equipamento)
                for col in ['vl_temperatura', 'vl_pressao', 'vl_humidade']:
                    if col in df_features.columns:
                        # Média móvel
                        df_features[f'{col}_rolling_mean'] = df_features.groupby('id_maquina')[col].transform(
                            lambda x: x.rolling(window=5, min_periods=1).mean()
                        )
                        # Desvio padrão móvel
                        df_features[f'{col}_rolling_std'] = df_features.groupby('id_maquina')[col].transform(
                            lambda x: x.rolling(window=5, min_periods=1).std()
                        )
                        # Diferença da média
                        df_features[f'{col}_diff_mean'] = df_features[col] - df_features[f'{col}_rolling_mean']
            
            # ==========================================
            # 4. FEATURES CATEGÓRICAS
            # ==========================================
            
            # Encoding para tipo de máquina
            if 'tipo_maquina' in df_features.columns:
                le_equipment = LabelEncoder()
                df_features['tipo_maquina_encoded'] = le_equipment.fit_transform(df_features['tipo_maquina'].astype(str))
            
            # Encoding para localização
            if 'localizacao' in df_features.columns:
                le_location = LabelEncoder()
                df_features['localizacao_encoded'] = le_location.fit_transform(df_features['localizacao'].astype(str))
            
            # ==========================================
            # 5. FEATURES DE ALERTA BASEADAS EM THRESHOLD
            # ==========================================
            
            if 'vl_temperatura' in df_features.columns:
                df_features['temp_alert'] = (df_features['vl_temperatura'] > FEATURE_CONFIG['temperature_threshold']).astype(int)
            
            if 'vl_pressao' in df_features.columns:
                df_features['pressure_alert'] = (
                    (df_features['vl_pressao'] < FEATURE_CONFIG['pressure_min']) | 
                    (df_features['vl_pressao'] > FEATURE_CONFIG['pressure_max'])
                ).astype(int)
            
            if 'vl_humidade' in df_features.columns:
                df_features['humidity_alert'] = (df_features['vl_humidade'] > FEATURE_CONFIG['humidity_threshold']).astype(int)
            
            if 'vibration_magnitude' in df_features.columns:
                df_features['vibration_alert'] = (df_features['vibration_magnitude'] > FEATURE_CONFIG['vibration_threshold']).astype(int)
            
            # ==========================================
            # 6. TARGET VARIABLE
            # ==========================================
            
            # Converter flag_falha para target binário
            if 'flag_falha' in df_features.columns:
                df_features['target'] = (df_features['flag_falha'] == 'S').astype(int)
            
            self.logger.info(f"Feature engineering concluído: {df_features.shape[1]} features")
            return df_features
            
        except Exception as e:
            self.logger.error(f"Erro no feature engineering: {str(e)}")
            return df
    
    def select_features_for_ml(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
        """
        Selecionar features relevantes para ML
        
        Returns:
            Tuple com (DataFrame de features, lista de nomes das colunas)
        """
        try:
            # Features numéricas principais
            feature_columns = [
                'vl_temperatura', 'vl_pressao', 'vl_vibracao', 'vl_humidade',
                'vl_vibr_x', 'vl_vibr_y', 'vl_vibr_z',
                'vl_gyro_x', 'vl_gyro_y', 'vl_gyro_z'
            ]
            
            # Features derivadas se disponíveis
            derived_features = [
                'vibration_magnitude', 'gyro_magnitude',
                'tipo_maquina_encoded', 'localizacao_encoded',
                'temp_alert', 'pressure_alert', 'humidity_alert', 'vibration_alert'
            ]
            
            # Features temporais se disponíveis
            temporal_features = [
                'hour', 'day_of_week',
                'vl_temperatura_rolling_mean', 'vl_temperatura_rolling_std',
                'vl_pressao_rolling_mean', 'vl_pressao_rolling_std',
                'vl_humidade_rolling_mean', 'vl_humidade_rolling_std'
            ]
            
            # Construir lista final de features
            available_features = []
            for feature_list in [feature_columns, derived_features, temporal_features]:
                for feature in feature_list:
                    if feature in df.columns:
                        available_features.append(feature)
            
            # Remover features com muitos NaNs
            df_features = df[available_features].copy()
            
            # Remover colunas com mais de 50% de valores nulos
            null_percentage = df_features.isnull().sum() / len(df_features)
            valid_features = null_percentage[null_percentage < 0.5].index.tolist()
            
            df_final = df_features[valid_features].fillna(0)
            
            self.logger.info(f"Features selecionadas para ML: {len(valid_features)} features")
            self.feature_columns = valid_features
            
            return df_final, valid_features
            
        except Exception as e:
            self.logger.error(f"Erro na seleção de features: {str(e)}")
            return pd.DataFrame(), []
    
    def train_models(self, X: pd.DataFrame, y: pd.Series) -> Dict[str, Any]:
        """
        Treinar múltiplos modelos ML
        
        Args:
            X: Features
            y: Target variable
            
        Returns:
            Dicionário com modelos treinados e métricas
        """
        try:
            self.logger.info("Iniciando treinamento de modelos")
            
            # Split train/test
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, 
                test_size=ML_CONFIG['test_size'], 
                random_state=ML_CONFIG['random_state'],
                stratify=y
            )
            
            # Normalizar features
            self.scaler = RobustScaler()
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            # Salvar scaler
            with open(self.model_path / 'scaler.pkl', 'wb') as f:
                pickle.dump(self.scaler, f)
            
            # Definir modelos
            models_config = {
                'KNN': {
                    'model': KNeighborsClassifier(),
                    'params': {
                        'n_neighbors': [3, 5, 7, 9],
                        'weights': ['uniform', 'distance'],
                        'metric': ['euclidean', 'manhattan']
                    }
                },
                'RandomForest': {
                    'model': RandomForestClassifier(random_state=ML_CONFIG['random_state']),
                    'params': {
                        'n_estimators': [50, 100, 200],
                        'max_depth': [None, 10, 20],
                        'min_samples_split': [2, 5, 10]
                    }
                },
                'LogisticRegression': {
                    'model': LogisticRegression(random_state=ML_CONFIG['random_state']),
                    'params': {
                        'C': [0.1, 1.0, 10.0],
                        'solver': ['liblinear', 'lbfgs']
                    }
                }
            }
            
            results = {}
            
            # Treinar cada modelo
            for name, config in models_config.items():
                self.logger.info(f"Treinando {name}...")
                
                # Grid Search para hiperparâmetros
                grid_search = GridSearchCV(
                    config['model'], 
                    config['params'],
                    cv=ML_CONFIG['cv_folds'],
                    scoring='f1',
                    n_jobs=-1
                )
                
                grid_search.fit(X_train_scaled, y_train)
                
                # Melhor modelo
                best_model = grid_search.best_estimator_
                
                # Predições
                y_pred = best_model.predict(X_test_scaled)
                y_pred_proba = best_model.predict_proba(X_test_scaled)[:, 1] if hasattr(best_model, 'predict_proba') else None
                
                # Métricas
                metrics = MLMetrics(
                    accuracy=accuracy_score(y_test, y_pred),
                    precision=precision_score(y_test, y_pred, zero_division=0),
                    recall=recall_score(y_test, y_pred, zero_division=0),
                    f1_score=f1_score(y_test, y_pred, zero_division=0),
                    auc_roc=roc_auc_score(y_test, y_pred_proba) if y_pred_proba is not None else 0.0,
                    confusion_matrix=confusion_matrix(y_test, y_pred),
                    classification_report=classification_report(y_test, y_pred)
                )
                
                results[name] = {
                    'model': best_model,
                    'metrics': metrics,
                    'best_params': grid_search.best_params_,
                    'cv_score': grid_search.best_score_
                }
                
                # Salvar modelo
                model_file = self.model_path / f'{name.lower()}_model.pkl'
                with open(model_file, 'wb') as f:
                    pickle.dump(best_model, f)
                
                self.logger.info(f"{name} - F1: {metrics.f1_score:.4f}, Accuracy: {metrics.accuracy:.4f}")
            
            # Selecionar melhor modelo baseado em F1-score
            best_model_name = max(results, key=lambda x: results[x]['metrics'].f1_score)
            self.models = {best_model_name: results[best_model_name]['model']}
            self.current_metrics = results
            
            # Salvar dados de teste para posterior análise
            self.test_data = {
                'X_test': X_test,
                'y_test': y_test,
                'X_test_scaled': X_test_scaled
            }
            
            self.logger.info(f"Treinamento concluído. Melhor modelo: {best_model_name}")
            return results
            
        except Exception as e:
            self.logger.error(f"Erro no treinamento: {str(e)}")
            return {}
    
    def generate_visualizations(self, results: Dict) -> None:
        """Gerar visualizações dos resultados"""
        try:
            self.logger.info("Gerando visualizações")
            
            plt.style.use('seaborn-v0_8')
            
            # 1. Comparação de métricas
            fig, axes = plt.subplots(2, 2, figsize=(15, 12))
            fig.suptitle('Comparação de Modelos - Smart Maintenance ML', fontsize=16)
            
            # Preparar dados para gráficos
            model_names = list(results.keys())
            metrics_data = {
                'Accuracy': [results[name]['metrics'].accuracy for name in model_names],
                'Precision': [results[name]['metrics'].precision for name in model_names],
                'Recall': [results[name]['metrics'].recall for name in model_names],
                'F1-Score': [results[name]['metrics'].f1_score for name in model_names]
            }
            
            # Gráfico de barras para métricas
            x = np.arange(len(model_names))
            width = 0.2
            
            for i, (metric, values) in enumerate(metrics_data.items()):
                axes[0, 0].bar(x + i*width, values, width, label=metric)
            
            axes[0, 0].set_xlabel('Modelos')
            axes[0, 0].set_ylabel('Score')
            axes[0, 0].set_title('Métricas de Performance')
            axes[0, 0].set_xticks(x + width*1.5)
            axes[0, 0].set_xticklabels(model_names)
            axes[0, 0].legend()
            axes[0, 0].grid(True, alpha=0.3)
            
            # 2. Matriz de confusão do melhor modelo
            best_model_name = max(results, key=lambda x: results[x]['metrics'].f1_score)
            cm = results[best_model_name]['metrics'].confusion_matrix
            
            sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', ax=axes[0, 1])
            axes[0, 1].set_title(f'Matriz de Confusão - {best_model_name}')
            axes[0, 1].set_xlabel('Predito')
            axes[0, 1].set_ylabel('Real')
            
            # 3. Feature importance (se disponível)
            if best_model_name == 'RandomForest' and hasattr(results[best_model_name]['model'], 'feature_importances_'):
                importances = results[best_model_name]['model'].feature_importances_
                feature_names = self.feature_columns
                
                # Top 10 features mais importantes
                top_indices = np.argsort(importances)[-10:]
                top_importances = importances[top_indices]
                top_features = [feature_names[i] for i in top_indices]
                
                axes[1, 0].barh(range(len(top_features)), top_importances)
                axes[1, 0].set_yticks(range(len(top_features)))
                axes[1, 0].set_yticklabels(top_features)
                axes[1, 0].set_xlabel('Importância')
                axes[1, 0].set_title('Top 10 Features Mais Importantes')
                axes[1, 0].grid(True, alpha=0.3)
            
            # 4. Distribuição das predições
            if self.test_data and best_model_name in self.models:
                y_pred_proba = self.models[best_model_name].predict_proba(self.test_data['X_test_scaled'])
                
                axes[1, 1].hist(y_pred_proba[:, 1], bins=20, alpha=0.7, color='skyblue', edgecolor='black')
                axes[1, 1].axvline(0.5, color='red', linestyle='--', label='Threshold (0.5)')
                axes[1, 1].set_xlabel('Probabilidade de Falha')
                axes[1, 1].set_ylabel('Frequência')
                axes[1, 1].set_title('Distribuição das Probabilidades de Falha')
                axes[1, 1].legend()
                axes[1, 1].grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            # Salvar gráfico
            viz_path = self.results_path / f'ml_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
            plt.savefig(viz_path, dpi=300, bbox_inches='tight')
            self.logger.info(f"Visualizações salvas em: {viz_path}")
            
            # Mostrar gráfico
            plt.show()
            
        except Exception as e:
            self.logger.error(f"Erro ao gerar visualizações: {str(e)}")
    
    def predict_maintenance(self, 
                          equipment_id: str, 
                          sensor_data: Dict[str, float]) -> PredictionResult:
        """
        Predizer necessidade de manutenção para um equipamento
        
        Args:
            equipment_id: ID do equipamento
            sensor_data: Dados dos sensores
            
        Returns:
            Resultado da predição
        """
        try:
            if not self.models or not self.scaler:
                raise ValueError("Modelos não carregados. Execute treinamento primeiro.")
            
            # Preparar dados para predição
            feature_vector = self.prepare_prediction_features(sensor_data)
            
            # Normalizar
            feature_vector_scaled = self.scaler.transform([feature_vector])
            
            # Usar melhor modelo
            model_name = list(self.models.keys())[0]
            model = self.models[model_name]
            
            # Predição
            prediction = model.predict(feature_vector_scaled)[0]
            probability = model.predict_proba(feature_vector_scaled)[0][1] if hasattr(model, 'predict_proba') else prediction
            
            # Determinar nível de alerta
            if probability >= 0.8:
                alert_level = "CRITICAL"
            elif probability >= 0.6:
                alert_level = "HIGH"
            elif probability >= 0.4:
                alert_level = "MEDIUM"
            else:
                alert_level = "LOW"
            
            result = PredictionResult(
                equipment_id=equipment_id,
                timestamp=datetime.now(),
                fault_probability=float(probability),
                predicted_class=int(prediction),
                confidence=float(max(probability, 1-probability)),
                features_used=sensor_data,
                alert_level=alert_level
            )
            
            self.logger.info(f"Predição para {equipment_id}: {alert_level} ({probability:.3f})")
            return result
            
        except Exception as e:
            self.logger.error(f"Erro na predição: {str(e)}")
            return None
    
    def prepare_prediction_features(self, sensor_data: Dict[str, float]) -> List[float]:
        """Preparar features para predição baseado nos dados dos sensores"""
        
        # Mapear dados de sensores para features do modelo
        feature_mapping = {
            'vl_temperatura': sensor_data.get('temperature', 0),
            'vl_pressao': sensor_data.get('pressure', 0),
            'vl_vibracao': sensor_data.get('vibration', 0),
            'vl_humidade': sensor_data.get('humidity', 0),
            'vl_vibr_x': sensor_data.get('vibration_x', 0),
            'vl_vibr_y': sensor_data.get('vibration_y', 0),
            'vl_vibr_z': sensor_data.get('vibration_z', 0),
            'vl_gyro_x': sensor_data.get('gyro_x', 0),
            'vl_gyro_y': sensor_data.get('gyro_y', 0),
            'vl_gyro_z': sensor_data.get('gyro_z', 0)
        }
        
        # Calcular features derivadas
        vibration_magnitude = np.sqrt(
            feature_mapping['vl_vibr_x']**2 + 
            feature_mapping['vl_vibr_y']**2 + 
            feature_mapping['vl_vibr_z']**2
        )
        
        gyro_magnitude = np.sqrt(
            feature_mapping['vl_gyro_x']**2 + 
            feature_mapping['vl_gyro_y']**2 + 
            feature_mapping['vl_gyro_z']**2
        )
        
        # Features de alerta
        temp_alert = 1 if feature_mapping['vl_temperatura'] > FEATURE_CONFIG['temperature_threshold'] else 0
        pressure_alert = 1 if (feature_mapping['vl_pressao'] < FEATURE_CONFIG['pressure_min'] or 
                              feature_mapping['vl_pressao'] > FEATURE_CONFIG['pressure_max']) else 0
        humidity_alert = 1 if feature_mapping['vl_humidade'] > FEATURE_CONFIG['humidity_threshold'] else 0
        vibration_alert = 1 if vibration_magnitude > FEATURE_CONFIG['vibration_threshold'] else 0
        
        # Construir vetor de features na ordem correta
        feature_vector = []
        for feature_name in self.feature_columns:
            if feature_name in feature_mapping:
                feature_vector.append(feature_mapping[feature_name])
            elif feature_name == 'vibration_magnitude':
                feature_vector.append(vibration_magnitude)
            elif feature_name == 'gyro_magnitude':
                feature_vector.append(gyro_magnitude)
            elif feature_name == 'temp_alert':
                feature_vector.append(temp_alert)
            elif feature_name == 'pressure_alert':
                feature_vector.append(pressure_alert)
            elif feature_name == 'humidity_alert':
                feature_vector.append(humidity_alert)
            elif feature_name == 'vibration_alert':
                feature_vector.append(vibration_alert)
            else:
                feature_vector.append(0)  # Default para features não disponíveis
        
        return feature_vector
    
    def run_full_pipeline(self) -> bool:
        """Executar pipeline completo de ML"""
        try:
            self.logger.info("=== Iniciando Pipeline Completo de ML ===")
            
            # 1. Conectar ao banco
            if not self.connect_database():
                return False
            
            # 2. Extrair dados
            df_raw = self.extract_features_from_db(days_back=30, include_synthetic=True)
            if df_raw.empty:
                self.logger.error("Nenhum dado disponível para treinamento")
                return False
            
            # 3. Preparar features
            df_features = self.prepare_features(df_raw)
            
            # 4. Selecionar features para ML
            X, feature_names = self.select_features_for_ml(df_features)
            
            if X.empty or 'target' not in df_features.columns:
                self.logger.error("Features ou target não disponíveis")
                return False
            
            y = df_features['target']
            
            # 5. Treinar modelos
            results = self.train_models(X, y)
            
            if not results:
                self.logger.error("Falha no treinamento dos modelos")
                return False
            
            # 6. Gerar visualizações
            self.generate_visualizations(results)
            
            # 7. Salvar relatório
            self.save_training_report(results)
            
            self.logger.info("Pipeline de ML concluído com sucesso!")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro no pipeline de ML: {str(e)}")
            return False
    
    def save_training_report(self, results: Dict) -> None:
        """Salvar relatório de treinamento"""
        try:
            report_data = {
                'timestamp': datetime.now().isoformat(),
                'models_trained': len(results),
                'best_model': max(results, key=lambda x: results[x]['metrics'].f1_score),
                'feature_count': len(self.feature_columns),
                'features_used': self.feature_columns,
                'results': {}
            }
            
            for name, result in results.items():
                report_data['results'][name] = {
                    'accuracy': float(result['metrics'].accuracy),
                    'precision': float(result['metrics'].precision),
                    'recall': float(result['metrics'].recall),
                    'f1_score': float(result['metrics'].f1_score),
                    'auc_roc': float(result['metrics'].auc_roc),
                    'best_params': result['best_params'],
                    'cv_score': float(result['cv_score'])
                }
            
            # Salvar como JSON
            report_file = self.results_path / f'training_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            with open(report_file, 'w') as f:
                json.dump(report_data, f, indent=2)
            
            self.logger.info(f"Relatório salvo em: {report_file}")
            
        except Exception as e:
            self.logger.error(f"Erro ao salvar relatório: {str(e)}")

# ===========================================
# EXECUÇÃO PRINCIPAL
# ===========================================

if __name__ == "__main__":
    # Executar pipeline
    pipeline = SmartMaintenanceMLPipeline()
    success = pipeline.run_full_pipeline()
    
    if success:
        print("\n=== PIPELINE DE ML CONCLUÍDO ===")
        print("✓ Modelos treinados com sucesso")
        print("✓ Métricas calculadas")
        print("✓ Visualizações geradas")
        print("✓ Relatório salvo")
        
        # Exemplo de predição
        print("\n=== TESTE DE PREDIÇÃO ===")
        sample_sensor_data = {
            'temperature': 95.5,
            'pressure': 955.0,
            'vibration': 8.5,
            'humidity': 75.0,
            'vibration_x': 5.2,
            'vibration_y': 3.1,
            'vibration_z': 2.8,
            'gyro_x': 1.2,
            'gyro_y': -0.8,
            'gyro_z': 0.3
        }
        
        prediction = pipeline.predict_maintenance('PUMP_001', sample_sensor_data)
        if prediction:
            print(f"Equipamento: {prediction.equipment_id}")
            print(f"Probabilidade de falha: {prediction.fault_probability:.3f}")
            print(f"Nível de alerta: {prediction.alert_level}")
    else:
        print("\n❌ FALHA NO PIPELINE DE ML")
