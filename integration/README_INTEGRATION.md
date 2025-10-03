# Pipeline Integrado - Smart Maintenance SaaS

## 4.1 Arquitetura Integrada

```
┌─────────────────┐    MQTT/HTTP     ┌──────────────────┐    SQL Queries    ┌─────────────────┐
│    ESP32 +      │ ─────────────────▶│   Data Ingestion  │ ─────────────────▶│   Oracle DB     │
│   Sensores      │   JSON/CSV        │     Service       │    INSERT/BULK     │   (3 Tabelas)   │
│  (MPU6050+)     │   @1Hz            │   (Python/MQTT)   │                   │                 │
└─────────────────┘                   └──────────────────┘                   └─────────────────┘
                                               │                                        │
                                               ▼                                        ▼
┌─────────────────┐    REST API      ┌──────────────────┐    SELECT/JOIN    ┌─────────────────┐
│   Dashboard     │ ◀─────────────── │   ML Pipeline    │ ◀─────────────────│  ETL Process    │
│  (Streamlit)    │   KPIs/Alertas   │  (Scikit-learn)  │   Feature Prep     │  (Data Prep)    │
│   + Alertas     │                  │  Treino/Predict  │                   │                 │
└─────────────────┘                  └──────────────────┘                   └─────────────────┘

Fluxos de Dados:
- ESP32 → MQTT Broker → Python Service → Oracle DB (1Hz, JSON)
- DB → ETL → ML Training → Model Storage (Batch, diário)
- DB → ML Inference → Dashboard → Alertas (Real-time, < 5min)
```

## Componentes e Tecnologias

- **IoT**: ESP32 + MPU6050 + DHT22
- **Comunicação**: MQTT (Eclipse Mosquitto)
- **Banco**: Oracle Database (3NF)  
- **ML**: Scikit-learn (KNN + Random Forest)
- **Dashboard**: Streamlit + Plotly
- **Orquestração**: Python Scripts

## Formatos de Dados

### MQTT Payload (JSON)
```json
{
  "device_id": "ESP32_001",
  "timestamp": "2024-01-15T10:30:00Z",
  "sensors": {
    "temperature": 75.5,
    "pressure": 1013.25,
    "vibration": 2.1,
    "humidity": 45.2
  },
  "location": "Factory_A",
  "equipment_type": "Pump"
}
```

### Database Schema
```sql
T_EQUIPAMENTO: (id_maquina, tipo_maquina)
T_SENSOR: (id_sensor, tipo_sensor)
T_MEDICAO: (sensor_id, equipamento_id, dataHora_medicao, vl_temperatura, vl_pressao, vl_vibracao, vl_humidade)
```
