-- =====================================================
-- Smart Maintenance SaaS - SQLite Setup Scripts
-- Versão: 1.0 - Adaptado para SQLite
-- Data: 2024
-- =====================================================

-- =====================================================
-- 1. CRIAÇÃO DAS TABELAS (baseado na modelagem Sprint 3)
-- =====================================================

-- Limpar tabelas existentes (cuidado em produção!)
DROP TABLE IF EXISTS T_MEDICAO;
DROP TABLE IF EXISTS T_EQUIPAMENTO;  
DROP TABLE IF EXISTS T_SENSOR;

-- Tabela de Equipamentos
CREATE TABLE T_EQUIPAMENTO (
    id_maquina TEXT NOT NULL,
    tipo_maquina TEXT NOT NULL,
    localizacao TEXT,
    data_instalacao TEXT DEFAULT (datetime('now')),
    status_operacional TEXT DEFAULT 'A' CHECK (status_operacional IN ('A', 'I', 'M')), -- A=Ativo, I=Inativo, M=Manutenção
    PRIMARY KEY (id_maquina)
);

-- Tabela de Sensores  
CREATE TABLE T_SENSOR (
    id_sensor TEXT NOT NULL,
    tipo_sensor TEXT NOT NULL,
    unidade_medida TEXT,
    faixa_min REAL,
    faixa_max REAL,
    precisao REAL,
    PRIMARY KEY (id_sensor)
);

-- Tabela de Medições (principal)
CREATE TABLE T_MEDICAO (
    id_medicao INTEGER PRIMARY KEY AUTOINCREMENT,
    id_sensor TEXT NOT NULL,
    id_maquina TEXT NOT NULL,
    dataHora_medicao TEXT DEFAULT (datetime('now')),
    vl_temperatura REAL,
    vl_pressao REAL,
    vl_vibracao REAL,
    vl_humidade REAL,
    vl_vibr_x REAL,
    vl_vibr_y REAL, 
    vl_vibr_z REAL,
    vl_gyro_x REAL,
    vl_gyro_y REAL,
    vl_gyro_z REAL,
    flag_falha TEXT DEFAULT 'N' CHECK (flag_falha IN ('S', 'N')),
    fonte_dados TEXT DEFAULT 'ESP32', -- ESP32, MQTT, SIMULACAO
    FOREIGN KEY (id_maquina) REFERENCES T_EQUIPAMENTO (id_maquina),
    FOREIGN KEY (id_sensor) REFERENCES T_SENSOR (id_sensor)
);

-- =====================================================
-- 2. ÍNDICES PARA PERFORMANCE
-- =====================================================

-- Índice composto para consultas por equipamento e tempo
CREATE INDEX IDX_MEDICAO_EQUIP_TEMPO ON T_MEDICAO (id_maquina, dataHora_medicao);

-- Índice para consultas por flag de falha
CREATE INDEX IDX_MEDICAO_FALHA ON T_MEDICAO (flag_falha);

-- Índice para consultas recentes (últimas 24h, 7 dias, etc)
CREATE INDEX IDX_MEDICAO_TEMPO ON T_MEDICAO (dataHora_medicao);

-- =====================================================
-- 3. VIEWS PARA CONSULTAS FREQUENTES
-- =====================================================

-- View para dados agregados por equipamento
CREATE VIEW V_STATS_EQUIPAMENTO AS
SELECT 
    e.id_maquina,
    e.tipo_maquina,
    e.localizacao,
    COUNT(m.id_medicao) as total_medicoes,
    AVG(m.vl_temperatura) as temp_media,
    MAX(m.vl_temperatura) as temp_maxima,
    MIN(m.vl_temperatura) as temp_minima,
    AVG(m.vl_pressao) as pressao_media,
    AVG(m.vl_humidade) as humidade_media,
    SUM(CASE WHEN m.flag_falha = 'S' THEN 1 ELSE 0 END) as total_falhas,
    MAX(m.dataHora_medicao) as ultima_medicao
FROM T_EQUIPAMENTO e
LEFT JOIN T_MEDICAO m ON e.id_maquina = m.id_maquina
GROUP BY e.id_maquina, e.tipo_maquina, e.localizacao;

-- View para alertas ativos (últimas 24 horas)
CREATE VIEW V_ALERTAS_ATIVOS AS
SELECT 
    e.id_maquina,
    e.tipo_maquina,
    e.localizacao,
    m.dataHora_medicao,
    m.vl_temperatura,
    m.vl_pressao,
    m.vl_humidade,
    CASE 
        WHEN m.vl_temperatura > 95 THEN 'TEMPERATURA_CRITICA'
        WHEN m.vl_pressao < 960 OR m.vl_pressao > 1040 THEN 'PRESSAO_ANORMAL'
        WHEN m.vl_humidade > 80 THEN 'HUMIDADE_ALTA'
        WHEN m.flag_falha = 'S' THEN 'FALHA_DETECTADA'
        ELSE 'NORMAL'
    END as tipo_alerta
FROM T_EQUIPAMENTO e
INNER JOIN T_MEDICAO m ON e.id_maquina = m.id_maquina
WHERE m.dataHora_medicao >= datetime('now', '-24 hours')
AND (m.vl_temperatura > 95 OR 
     m.vl_pressao < 960 OR m.vl_pressao > 1040 OR 
     m.vl_humidade > 80 OR 
     m.flag_falha = 'S')
ORDER BY m.dataHora_medicao DESC;

-- =====================================================
-- 4. DADOS DE EXEMPLO (SEED DATA)
-- =====================================================

-- Inserir equipamentos de exemplo
INSERT INTO T_EQUIPAMENTO (id_maquina, tipo_maquina, localizacao) VALUES
('PUMP_001', 'Pump', 'Factory_A'),
('TURB_001', 'Turbine', 'Factory_A'),
('COMP_001', 'Compressor', 'Factory_B'),
('PUMP_002', 'Pump', 'Factory_B'),
('MOTOR_001', 'Motor', 'Factory_A');

-- Inserir sensores de exemplo
INSERT INTO T_SENSOR (id_sensor, tipo_sensor, unidade_medida, faixa_min, faixa_max, precisao) VALUES
('MPU_001', 'MPU6050', 'Multiple', -50, 200, 0.1),
('DHT_001', 'DHT22', 'C/%', -40, 80, 0.5),
('PRES_001', 'Pressure', 'hPa', 900, 1100, 1.0),
('VIBR_001', 'Vibration', 'm/s2', -50, 50, 0.01),
('TEMP_001', 'DS18B20', 'C', -55, 125, 0.5);

-- =====================================================
-- 5. INSERÇÃO DE DADOS DE TESTE
-- =====================================================

-- Gerar algumas medições de exemplo
INSERT INTO T_MEDICAO (id_sensor, id_maquina, vl_temperatura, vl_pressao, vl_vibracao, vl_humidade, vl_vibr_x, vl_vibr_y, vl_vibr_z, flag_falha, fonte_dados) VALUES
('MPU_001', 'PUMP_001', 75.5, 1013.25, 2.1, 45.2, 1.5, -0.8, 9.8, 'N', 'ESP32'),
('DHT_001', 'PUMP_001', 76.2, 1012.8, 2.3, 46.1, 1.2, -0.5, 9.7, 'N', 'ESP32'),
('MPU_001', 'TURB_001', 82.1, 1015.2, 3.2, 52.4, 2.1, -1.2, 9.9, 'N', 'ESP32'),
('PRES_001', 'COMP_001', 78.9, 1010.5, 1.8, 48.7, 0.9, -0.3, 9.6, 'N', 'ESP32'),
('MPU_001', 'PUMP_002', 85.3, 1014.1, 2.8, 55.1, 1.8, -0.9, 9.8, 'N', 'ESP32');

-- Inserir algumas medições com falha para teste
INSERT INTO T_MEDICAO (id_sensor, id_maquina, vl_temperatura, vl_pressao, vl_vibracao, vl_humidade, vl_vibr_x, vl_vibr_y, vl_vibr_z, flag_falha, fonte_dados) VALUES
('MPU_001', 'PUMP_001', 98.5, 1050.0, 8.5, 85.2, 5.5, -3.8, 12.1, 'S', 'SIMULACAO'),
('DHT_001', 'TURB_001', 96.8, 950.0, 9.2, 88.1, 6.2, -4.2, 11.8, 'S', 'SIMULACAO');

-- =====================================================
-- 6. CONSULTAS DE VALIDAÇÃO
-- =====================================================

-- Verificar dados inseridos
SELECT 'Equipamentos cadastrados: ' || COUNT(*) as STATUS FROM T_EQUIPAMENTO;
SELECT 'Sensores cadastrados: ' || COUNT(*) as STATUS FROM T_SENSOR;
SELECT 'Medições inseridas: ' || COUNT(*) as STATUS FROM T_MEDICAO;

-- Verificar dados por equipamento
SELECT 
    id_maquina,
    COUNT(*) as total_medicoes,
    AVG(vl_temperatura) as temp_media,
    SUM(CASE WHEN flag_falha = 'S' THEN 1 ELSE 0 END) as total_falhas
FROM T_MEDICAO 
GROUP BY id_maquina;

-- Verificar alertas
SELECT COUNT(*) as alertas_ativos FROM V_ALERTAS_ATIVOS;

-- =====================================================
-- FIM DO SCRIPT
-- =====================================================

SELECT 'SQLite Database setup completed successfully!' as STATUS;
