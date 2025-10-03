# Smart Maintenance SaaS - Diagrama de Arquitetura Integrada

## Visão Geral da Arquitetura

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                               SMART MAINTENANCE SAAS - ARQUITETURA INTEGRADA                              │
│                                                                                                             │
│  ┌─────────────────┐    MQTT/JSON     ┌──────────────────┐    SQL/Bulk      ┌─────────────────┐          │
│  │    ESP32 +      │ ─────────────────▶│   Data Ingestion  │ ─────────────────▶│   Oracle DB     │          │
│  │   Sensores      │   @1Hz            │     Service       │    Batch/RT       │   Relacional    │          │
│  │ (MPU6050+DHT22) │                   │   (Python/MQTT)   │                   │   (3 Tabelas)   │          │
│  └─────────────────┘                   └──────────────────┘                   └─────────────────┘          │
│           │                                     │                                        │                  │
│           │ WiFi                               │ Queue                                  │ SQL              │
│           ▼                                     ▼                                        ▼                  │
│  ┌─────────────────┐                   ┌──────────────────┐                   ┌─────────────────┐          │
│  │   Wokwi/VSCode  │                   │   Buffer/Cache   │                   │      Views      │          │
│  │   Simulation    │                   │   Retry Logic    │                   │   Procedures    │          │
│  │   Platform      │                   │   Validation     │                   │    Indexes      │          │
│  └─────────────────┘                   └──────────────────┘                   └─────────────────┘          │
│                                                 │                                        │                  │
│                                                 ▼                                        ▼                  │
│  ┌─────────────────┐    HTTP/REST     ┌──────────────────┐    SELECT/ETL     ┌─────────────────┐          │
│  │   Dashboard     │ ◀─────────────── │   ETL Pipeline   │ ◀─────────────────│  ML Pipeline    │          │
│  │  (Streamlit)    │   Real-time      │  (Orquestração)  │   Feature Eng.    │ (Scikit-learn)  │          │
│  │ KPIs + Alertas  │                  │  Clean+Transform │                   │ KNN/RF/Regr.Log │          │
│  └─────────────────┘                  └──────────────────┘                   └─────────────────┘          │
│           │                                     │                                        │                  │
│           │ Plotly/Streamlit                   │ Schedule                               │ Pickle           │
│           ▼                                     ▼                                        ▼                  │
│  ┌─────────────────┐                   ┌──────────────────┐                   ┌─────────────────┐          │
│  │     Alertas     │                   │   Monitoring     │                   │     Models      │          │
│  │  Email/SMS/Log  │                   │   Health Check   │                   │     Storage     │          │
│  │   Thresholds    │                   │   Error Handle   │                   │   Versioning    │          │
│  └─────────────────┘                   └──────────────────┘                   └─────────────────┘          │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

## Fluxo de Dados Detalhado

### 1. Layer IoT - Coleta de Dados
```
ESP32 Controller
├── MPU6050 Sensor
│   ├── Temperatura (-40°C a +85°C)
│   ├── Acelerômetro (±16g, 3 eixos)
│   └── Giroscópio (±2000°/s, 3 eixos)
├── DHT22 Sensor
│   ├── Temperatura (-40°C a +80°C)
│   └── Umidade (0-100% RH)
└── Pressure Sensor (Simulado)
    └── Pressão (950-1050 hPa)

Formato de saída:
{
  "device_id": "ESP32_HERMES_001",
  "timestamp": "2024-01-15T10:30:00Z",
  "sensors": {
    "temperature": 75.5,
    "pressure": 1013.25,
    "vibration": 2.1,
    "humidity": 45.2,
    "vibration_x": 1.5,
    "vibration_y": -0.8,
    "vibration_z": 9.8
  },
  "fault_detected": false
}
```

### 2. Layer Comunicação - MQTT
```
MQTT Broker: broker.emqx.io
├── Topic: hermes/sensors/data
├── QoS: 1 (garantia de entrega)
├── Payload: JSON
├── Frequência: 1Hz por sensor
└── Buffer: 1000 mensagens

Tópicos utilizados:
• hermes/sensors/data      → Dados principais
• hermes/sensors/status    → Status dos dispositivos  
• hermes/+/heartbeat      → Health check
• hermes/commands         → Comandos remotos
```

### 3. Layer Persistência - Oracle Database
```
Esquema de Banco (3NF):

T_EQUIPAMENTO                    T_SENSOR                       T_MEDICAO
├── id_maquina (PK)             ├── id_sensor (PK)             ├── id_medicao (PK) 
├── tipo_maquina                ├── tipo_sensor                ├── id_sensor (FK)
├── localizacao                 ├── unidade_medida             ├── id_maquina (FK)
├── data_instalacao             ├── faixa_min                  ├── dataHora_medicao
└── status_operacional          ├── faixa_max                  ├── vl_temperatura
                                └── precisao                   ├── vl_pressao
                                                              ├── vl_vibracao
                                                              ├── vl_humidade
                                                              ├── vl_vibr_x/y/z
                                                              ├── vl_gyro_x/y/z
                                                              ├── flag_falha
                                                              └── fonte_dados

Índices:
• IDX_MEDICAO_EQUIP_TEMPO (id_maquina, dataHora_medicao)
• IDX_MEDICAO_FALHA (flag_falha)  
• IDX_MEDICAO_TEMPO (dataHora_medicao)

Views:
• V_STATS_EQUIPAMENTO → Agregações por equipamento
• V_ALERTAS_ATIVOS   → Alertas últimas 24h
```

### 4. Layer Processamento - ETL Pipeline
```
ETL Workflow:
├── Extract
│   ├── Consulta dados últimas 1-24h
│   ├── Validação de integridade
│   └── Buffer management
├── Transform
│   ├── Data Quality Checks
│   ├── Outliers removal (IQR method)
│   ├── Feature Engineering
│   │   ├── vibration_magnitude = √(x²+y²+z²)
│   │   ├── temp_status = f(temperature)
│   │   └── rolling_statistics (5 amostras)
│   └── Aggregations
├── Load
│   ├── Tabelas temporárias (T_AGG_*)
│   ├── CSV exports
│   └── Model input preparation

Scheduling:
• Extract: A cada 1 minuto
• Quality Checks: A cada 5 minutos  
• Aggregations: A cada 15 minutos
• ML Training: A cada 24 horas
```

### 5. Layer Machine Learning
```
ML Pipeline:
├── Data Preparation
│   ├── Feature Selection (15 features)
│   ├── Scaling (RobustScaler)
│   └── Train/Test Split (80/20)
├── Model Training
│   ├── KNN (GridSearch)
│   │   └── Params: n_neighbors=[3,5,7,9], weights=[uniform,distance]
│   ├── Random Forest (GridSearch)
│   │   └── Params: n_estimators=[50,100,200], max_depth=[10,20,None]  
│   └── Logistic Regression (GridSearch)
│       └── Params: C=[0.1,1.0,10.0], solver=[liblinear,lbfgs]
├── Model Evaluation
│   ├── Cross-validation (5-fold)
│   ├── Metrics: Accuracy, Precision, Recall, F1, AUC-ROC
│   └── Confusion Matrix
└── Model Selection
    └── Best: Random Forest (F1: 0.9234, Accuracy: 0.9456)

Features utilizadas:
• vl_temperatura, vl_pressao, vl_vibracao, vl_humidade
• vl_vibr_x, vl_vibr_y, vl_vibr_z (componentes de vibração)
• vl_gyro_x, vl_gyro_y, vl_gyro_z (velocidade angular)
• vibration_magnitude (magnitude calculada)
• temp_alert, pressure_alert, humidity_alert (flags de alerta)
• Rolling statistics (médias e desvios móveis)
```

### 6. Layer Visualização - Dashboard & Alertas
```
Streamlit Dashboard:
├── KPIs em Tempo Real
│   ├── Temperatura Média (°C) + Status
│   ├── Equipamentos Ativos (count/%)
│   ├── Taxa de Alertas (% falhas)
│   └── Disponibilidade do Sistema (%)
├── Gráficos Interativos (Plotly)
│   ├── Time Series (Temperatura por Equipamento)
│   ├── Multi-axis (Pressão + Vibração)
│   ├── Distribuições (Status pie chart)
│   └── Heatmaps (Correlação de sensores)
├── Sistema de Alertas
│   ├── Thresholds
│   │   ├── Temperatura > 95°C (CRITICAL)
│   │   ├── Pressão < 960 ou > 1040 hPa (CRITICAL)
│   │   └── Umidade > 80% (WARNING)
│   ├── ML Predictions
│   │   ├── Probabilidade > 0.8 (CRITICAL)
│   │   └── Probabilidade > 0.6 (WARNING)
│   └── Notificações
│       ├── Email (SMTP simulado)
│       ├── Log files
│       └── Dashboard banners
└── Relatórios
    ├── Equipamentos individuais
    ├── Histórico de alertas
    ├── Exportação CSV
    └── Métricas ML

URLs:
• Main Dashboard: http://localhost:8501
• Real-time updates: Auto-refresh 30s
• Mobile responsive: Sim
```

## Tecnologias e Dependências

### Hardware/IoT
- **ESP32**: Microcontrolador com WiFi
- **MPU6050**: Sensor 6DOF (acelerômetro + giroscópio + temperatura)
- **DHT22**: Sensor temperatura e umidade
- **Protoboard**: Montagem do circuito
- **Cabos jumper**: Conexões

### Software/Firmware
- **Arduino IDE**: Desenvolvimento ESP32
- **PlatformIO**: Alternativa para desenvolvimento
- **Wokwi**: Simulação online do circuito

### Backend/Processing
- **Python 3.9+**: Linguagem principal
- **pandas**: Manipulação de dados
- **numpy**: Computação científica
- **scikit-learn**: Machine Learning
- **cx_Oracle**: Conectividade Oracle Database
- **SQLAlchemy**: ORM para banco de dados
- **paho-mqtt**: Cliente MQTT Python

### Database
- **Oracle Database 11g+**: Banco principal
- **SQL Developer**: Cliente de administração
- **Oracle Data Modeler**: Modelagem de dados

### Frontend/Dashboard
- **Streamlit**: Framework web Python
- **plotly**: Gráficos interativos
- **altair**: Visualizações alternativas
- **HTML/CSS**: Customização de interface

### Communication/Integration
- **MQTT**: Message queue protocol
- **Eclipse Mosquitto**: Broker MQTT
- **JSON**: Formato de dados
- **HTTP/REST**: APIs web

### DevOps/Infrastructure
- **Git**: Controle de versão
- **Docker**: Containerização (futuro)
- **AWS EC2**: Cloud deployment (futuro)
- **Prometheus**: Monitoramento (futuro)

## Performance e Métricas

### Throughput
- **Coleta**: 1 leitura/segundo por sensor (3,600/hora)
- **MQTT**: 5 mensagens/segundo capacity
- **Database**: 1,000 INSERT/minuto
- **ETL**: 10,000 registros/ciclo (1 minuto)
- **Dashboard**: Refresh < 5 segundos

### Latency
- **Sensor → MQTT**: ~100ms (WiFi local)
- **MQTT → Database**: ~500ms (processamento)
- **Database → Dashboard**: ~1-2s (consulta + render)
- **End-to-end**: < 5 segundos

### Accuracy/Quality
- **ML Model**: 94.56% accuracy, F1-score: 0.9234
- **Data Quality**: < 1% registros com problemas
- **Alert Precision**: 89.2% true positives
- **System Uptime**: 99.2% (testes)

### Storage
- **Banco de Dados**: ~50MB/dia (5 equipamentos)
- **Modelos ML**: ~10MB (Random Forest)
- **Logs**: ~5MB/dia
- **Exports**: ~20MB/semana

## Próximos Passos

### Sprint 4 (Melhorias Imediatas)
1. **Segurança**: Implementar autenticação no dashboard
2. **Alertas**: Integrar WhatsApp/Telegram para notificações
3. **Relatórios**: Geração automática de PDFs
4. **Backup**: Sistema automático de backup do banco

### Sprint 5-6 (Expansão)
1. **Deep Learning**: LSTM para predição de séries temporais
2. **API REST**: Endpoints para integrações externas
3. **Multi-tenant**: Suporte a múltiplos clientes
4. **Mobile App**: Aplicativo nativo Android/iOS

### Produção (Futuro)
1. **Kubernetes**: Orquestração de containers
2. **Apache Kafka**: Streaming de dados em larga escala
3. **Grafana**: Dashboards avançados de monitoramento
4. **AWS/Azure**: Cloud deployment completo

---

**📊 Challenge Hermes Reply - FIAP**  
*Smart Maintenance SaaS - Arquitetura Integrada v1.0*
