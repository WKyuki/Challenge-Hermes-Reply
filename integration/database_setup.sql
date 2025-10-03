-- =====================================================
-- Smart Maintenance SaaS - Database Setup Scripts
-- Versão: 1.0 - Integração Completa
-- Data: 2024
-- =====================================================

-- =====================================================
-- 1. CRIAÇÃO DAS TABELAS (baseado na modelagem Sprint 3)
-- =====================================================

-- Limpar tabelas existentes (cuidado em produção!)
DROP TABLE T_MEDICAO CASCADE CONSTRAINTS;
DROP TABLE T_EQUIPAMENTO CASCADE CONSTRAINTS;  
DROP TABLE T_SENSOR CASCADE CONSTRAINTS;

-- Tabela de Equipamentos
CREATE TABLE T_EQUIPAMENTO (
    id_maquina VARCHAR2(10) NOT NULL,
    tipo_maquina VARCHAR2(16) NOT NULL,
    localizacao VARCHAR2(50),
    data_instalacao DATE DEFAULT SYSDATE,
    status_operacional CHAR(1) DEFAULT 'A' CHECK (status_operacional IN ('A', 'I', 'M')), -- A=Ativo, I=Inativo, M=Manutenção
    CONSTRAINT PK_T_EQUIPAMENTO PRIMARY KEY (id_maquina)
);

-- Tabela de Sensores  
CREATE TABLE T_SENSOR (
    id_sensor VARCHAR2(10) NOT NULL,
    tipo_sensor VARCHAR2(16) NOT NULL,
    unidade_medida VARCHAR2(10),
    faixa_min NUMBER(9,6),
    faixa_max NUMBER(9,6),
    precisao NUMBER(4,2),
    CONSTRAINT PK_T_SENSOR PRIMARY KEY (id_sensor)
);

-- Tabela de Medições (principal)
CREATE TABLE T_MEDICAO (
    id_medicao NUMBER(12) NOT NULL,
    id_sensor VARCHAR2(10) NOT NULL,
    id_maquina VARCHAR2(10) NOT NULL,
    dataHora_medicao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    vl_temperatura NUMBER(9,6),
    vl_pressao NUMBER(9,6),
    vl_vibracao NUMBER(9,6),
    vl_humidade NUMBER(9,6),
    vl_vibr_x NUMBER(9,6),
    vl_vibr_y NUMBER(9,6), 
    vl_vibr_z NUMBER(9,6),
    vl_gyro_x NUMBER(9,6),
    vl_gyro_y NUMBER(9,6),
    vl_gyro_z NUMBER(9,6),
    flag_falha CHAR(1) DEFAULT 'N' CHECK (flag_falha IN ('S', 'N')),
    fonte_dados VARCHAR2(20) DEFAULT 'ESP32', -- ESP32, MQTT, SIMULACAO
    CONSTRAINT PK_T_MEDICAO PRIMARY KEY (id_medicao)
);

-- =====================================================
-- 2. CHAVES ESTRANGEIRAS E RELACIONAMENTOS
-- =====================================================

ALTER TABLE T_MEDICAO 
    ADD CONSTRAINT FK_T_MEDICAO_EQUIPAMENTO 
    FOREIGN KEY (id_maquina) REFERENCES T_EQUIPAMENTO (id_maquina);

ALTER TABLE T_MEDICAO 
    ADD CONSTRAINT FK_T_MEDICAO_SENSOR 
    FOREIGN KEY (id_sensor) REFERENCES T_SENSOR (id_sensor);

-- =====================================================
-- 3. RESTRIÇÕES DE INTEGRIDADE E VALIDAÇÃO
-- =====================================================

-- Valores não-negativos para medições físicas
ALTER TABLE T_MEDICAO 
    ADD CONSTRAINT CK_T_MED_VL_PRESSAO CHECK (vl_pressao >= 0);

ALTER TABLE T_MEDICAO 
    ADD CONSTRAINT CK_T_MED_VL_HUMIDADE CHECK (vl_humidade >= 0 AND vl_humidade <= 100);

-- Faixa de temperatura razoável para equipamentos industriais
ALTER TABLE T_MEDICAO 
    ADD CONSTRAINT CK_T_MED_VL_TEMPERATURA CHECK (vl_temperatura >= -50 AND vl_temperatura <= 200);

-- =====================================================
-- 4. ÍNDICES PARA PERFORMANCE
-- =====================================================

-- Índice composto para consultas por equipamento e tempo
CREATE INDEX IDX_MEDICAO_EQUIP_TEMPO ON T_MEDICAO (id_maquina, dataHora_medicao);

-- Índice para consultas por flag de falha
CREATE INDEX IDX_MEDICAO_FALHA ON T_MEDICAO (flag_falha);

-- Índice para consultas recentes (últimas 24h, 7 dias, etc)
CREATE INDEX IDX_MEDICAO_TEMPO ON T_MEDICAO (dataHora_medicao);

-- =====================================================
-- 5. SEQUÊNCIA PARA IDs AUTOMÁTICOS
-- =====================================================

CREATE SEQUENCE SEQ_MEDICAO
    START WITH 1
    INCREMENT BY 1
    NOCACHE
    NOCYCLE;

-- =====================================================
-- 6. TRIGGER PARA AUTO-INCREMENT
-- =====================================================

CREATE OR REPLACE TRIGGER TRG_MEDICAO_ID
    BEFORE INSERT ON T_MEDICAO
    FOR EACH ROW
BEGIN
    IF :NEW.id_medicao IS NULL THEN
        :NEW.id_medicao := SEQ_MEDICAO.NEXTVAL;
    END IF;
END;
/

-- =====================================================
-- 7. VIEWS PARA CONSULTAS FREQUENTES
-- =====================================================

-- View para dados agregados por equipamento
CREATE OR REPLACE VIEW V_STATS_EQUIPAMENTO AS
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
CREATE OR REPLACE VIEW V_ALERTAS_ATIVOS AS
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
WHERE m.dataHora_medicao >= SYSTIMESTAMP - INTERVAL '24' HOUR
AND (m.vl_temperatura > 95 OR 
     m.vl_pressao < 960 OR m.vl_pressao > 1040 OR 
     m.vl_humidade > 80 OR 
     m.flag_falha = 'S')
ORDER BY m.dataHora_medicao DESC;

-- =====================================================
-- 8. DADOS DE EXEMPLO (SEED DATA)
-- =====================================================

-- Inserir equipamentos de exemplo
INSERT INTO T_EQUIPAMENTO (id_maquina, tipo_maquina, localizacao) VALUES
('PUMP_001', 'Pump', 'Factory_A');
INSERT INTO T_EQUIPAMENTO (id_maquina, tipo_maquina, localizacao) VALUES  
('TURB_001', 'Turbine', 'Factory_A');
INSERT INTO T_EQUIPAMENTO (id_maquina, tipo_maquina, localizacao) VALUES
('COMP_001', 'Compressor', 'Factory_B');
INSERT INTO T_EQUIPAMENTO (id_maquina, tipo_maquina, localizacao) VALUES
('PUMP_002', 'Pump', 'Factory_B');

-- Inserir sensores de exemplo
INSERT INTO T_SENSOR (id_sensor, tipo_sensor, unidade_medida, faixa_min, faixa_max, precisao) VALUES
('MPU_001', 'MPU6050', 'Multiple', -50, 200, 0.1);
INSERT INTO T_SENSOR (id_sensor, tipo_sensor, unidade_medida, faixa_min, faixa_max, precisao) VALUES
('DHT_001', 'DHT22', 'C/%', -40, 80, 0.5);
INSERT INTO T_SENSOR (id_sensor, tipo_sensor, unidade_medida, faixa_min, faixa_max, precisao) VALUES
('PRES_001', 'Pressure', 'hPa', 900, 1100, 1.0);
INSERT INTO T_SENSOR (id_sensor, tipo_sensor, unidade_medida, faixa_min, faixa_max, precisao) VALUES
('VIBR_001', 'Vibration', 'm/s2', -50, 50, 0.01);

COMMIT;

-- =====================================================
-- 9. PROCEDIMENTOS PARA CARGA DE DADOS
-- =====================================================

-- Procedimento para inserir medição completa
CREATE OR REPLACE PROCEDURE SP_INSERT_MEDICAO (
    p_id_sensor VARCHAR2,
    p_id_maquina VARCHAR2,
    p_temperatura NUMBER,
    p_pressao NUMBER,
    p_vibracao NUMBER,
    p_humidade NUMBER,
    p_vibr_x NUMBER DEFAULT NULL,
    p_vibr_y NUMBER DEFAULT NULL,
    p_vibr_z NUMBER DEFAULT NULL,
    p_gyro_x NUMBER DEFAULT NULL,
    p_gyro_y NUMBER DEFAULT NULL,
    p_gyro_z NUMBER DEFAULT NULL,
    p_flag_falha CHAR DEFAULT 'N',
    p_fonte VARCHAR2 DEFAULT 'ESP32'
) AS
BEGIN
    INSERT INTO T_MEDICAO (
        id_sensor, id_maquina, vl_temperatura, vl_pressao, 
        vl_vibracao, vl_humidade, vl_vibr_x, vl_vibr_y, vl_vibr_z,
        vl_gyro_x, vl_gyro_y, vl_gyro_z, flag_falha, fonte_dados
    ) VALUES (
        p_id_sensor, p_id_maquina, p_temperatura, p_pressao,
        p_vibracao, p_humidade, p_vibr_x, p_vibr_y, p_vibr_z,
        p_gyro_x, p_gyro_y, p_gyro_z, p_flag_falha, p_fonte
    );
    
    COMMIT;
EXCEPTION
    WHEN OTHERS THEN
        ROLLBACK;
        RAISE;
END SP_INSERT_MEDICAO;
/

-- =====================================================
-- 10. FUNÇÕES PARA ANÁLISE E ML
-- =====================================================

-- Função para calcular média móvel de temperatura
CREATE OR REPLACE FUNCTION FN_TEMP_MEDIA_MOVEL (
    p_id_maquina VARCHAR2,
    p_horas NUMBER DEFAULT 1
) RETURN NUMBER AS
    v_media NUMBER;
BEGIN
    SELECT AVG(vl_temperatura)
    INTO v_media
    FROM T_MEDICAO
    WHERE id_maquina = p_id_maquina
    AND dataHora_medicao >= SYSTIMESTAMP - INTERVAL p_horas HOUR;
    
    RETURN NVL(v_media, 0);
EXCEPTION
    WHEN NO_DATA_FOUND THEN
        RETURN 0;
END FN_TEMP_MEDIA_MOVEL;
/

-- =====================================================
-- 11. CONSULTAS DE EXEMPLO PARA VALIDAÇÃO
-- =====================================================

-- Verificar estrutura criada
SELECT table_name FROM user_tables WHERE table_name LIKE 'T_%';

-- Verificar constraints
SELECT constraint_name, constraint_type, table_name 
FROM user_constraints 
WHERE table_name IN ('T_EQUIPAMENTO', 'T_SENSOR', 'T_MEDICAO');

-- Verificar dados de exemplo
SELECT * FROM T_EQUIPAMENTO;
SELECT * FROM T_SENSOR;

-- Testar inserção via procedure
BEGIN
    SP_INSERT_MEDICAO(
        p_id_sensor => 'MPU_001',
        p_id_maquina => 'PUMP_001', 
        p_temperatura => 75.5,
        p_pressao => 1013.25,
        p_vibracao => 2.1,
        p_humidade => 45.2,
        p_vibr_x => 1.5,
        p_vibr_y => -0.8,
        p_vibr_z => 9.8
    );
END;
/

-- Verificar inserção
SELECT * FROM T_MEDICAO WHERE ROWNUM <= 5;

-- =====================================================
-- 12. COMENTÁRIOS E DOCUMENTAÇÃO
-- =====================================================

COMMENT ON TABLE T_EQUIPAMENTO IS 'Cadastro de equipamentos industriais monitorados';
COMMENT ON TABLE T_SENSOR IS 'Cadastro de sensores disponíveis no sistema';
COMMENT ON TABLE T_MEDICAO IS 'Medições coletadas pelos sensores - tabela principal';

COMMENT ON COLUMN T_MEDICAO.flag_falha IS 'S=Falha detectada, N=Normal';
COMMENT ON COLUMN T_MEDICAO.fonte_dados IS 'Origem dos dados: ESP32, MQTT, SIMULACAO';
COMMENT ON COLUMN T_EQUIPAMENTO.status_operacional IS 'A=Ativo, I=Inativo, M=Manutenção';

-- =====================================================
-- FIM DO SCRIPT
-- =====================================================

SELECT 'Database setup completed successfully!' as STATUS FROM DUAL;
