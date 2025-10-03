#!/usr/bin/env python3
"""
Smart Maintenance SaaS - SQLite Configuration
===========================================

Configuração para usar SQLite ao invés do Oracle Database.
Este arquivo contém as configurações e funções necessárias
para adaptar o projeto ao SQLite.

Autor: Challenge Hermes Reply Team
"""

import sqlite3
import logging
from pathlib import Path
from sqlalchemy import create_engine
from typing import Optional

# ===========================================
# CONFIGURAÇÕES SQLITE
# ===========================================

# SQLite Database Configuration
SQLITE_CONFIG = {
    'database_path': 'smart_maintenance.db',  # Caminho do arquivo SQLite
    'timeout': 20,  # Timeout em segundos
    'check_same_thread': False,  # Permitir uso em múltiplas threads
    'echo': False  # SQLAlchemy echo (logs de SQL)
}

# Configuração unificada (substitui DB_CONFIG dos outros arquivos)
DB_CONFIG = {
    'type': 'sqlite',
    'database_path': SQLITE_CONFIG['database_path'],
    'timeout': SQLITE_CONFIG['timeout'],
    'encoding': 'UTF-8'
}

# ===========================================
# FUNÇÕES DE CONFIGURAÇÃO
# ===========================================

def create_sqlite_database() -> bool:
    """
    Criar e configurar o banco SQLite com o schema necessário
    """
    try:
        db_path = Path(SQLITE_CONFIG['database_path'])
        
        # Conectar ao SQLite
        conn = sqlite3.connect(str(db_path))
        
        # Ler e executar o script SQL
        sql_script_path = Path(__file__).parent / 'database_setup_sqlite.sql'
        
        if sql_script_path.exists():
            with open(sql_script_path, 'r', encoding='utf-8') as f:
                sql_script = f.read()
                
            # Executar o script em partes (SQLite não suporta múltiplos statements por vez)
            statements = sql_script.split(';')
            
            for statement in statements:
                statement = statement.strip()
                if statement and not statement.startswith('--'):
                    try:
                        conn.execute(statement)
                    except sqlite3.Error as e:
                        if "already exists" not in str(e).lower():
                            logging.warning(f"SQL statement warning: {str(e)}")
            
            conn.commit()
            conn.close()
            
            logging.info(f"SQLite database criado com sucesso em {db_path.absolute()}")
            return True
        else:
            logging.error(f"Script SQL não encontrado: {sql_script_path}")
            return False
            
    except Exception as e:
        logging.error(f"Erro ao criar banco SQLite: {str(e)}")
        return False

def get_sqlite_engine():
    """
    Criar SQLAlchemy engine para SQLite
    """
    try:
        db_path = Path(SQLITE_CONFIG['database_path']).absolute()
        connection_string = f"sqlite:///{db_path}"
        
        engine = create_engine(
            connection_string,
            echo=SQLITE_CONFIG['echo'],
            connect_args={
                'timeout': SQLITE_CONFIG['timeout'],
                'check_same_thread': SQLITE_CONFIG['check_same_thread']
            }
        )
        
        return engine
    except Exception as e:
        logging.error(f"Erro ao criar SQLite engine: {str(e)}")
        return None

def get_sqlite_connection():
    """
    Obter conexão direta ao SQLite
    """
    try:
        db_path = Path(SQLITE_CONFIG['database_path']).absolute()
        conn = sqlite3.connect(
            str(db_path),
            timeout=SQLITE_CONFIG['timeout'],
            check_same_thread=SQLITE_CONFIG['check_same_thread']
        )
        
        # Configurar SQLite
        conn.execute("PRAGMA foreign_keys = ON")  # Habilitar foreign keys
        conn.execute("PRAGMA journal_mode = WAL")  # Melhor performance
        
        return conn
    except Exception as e:
        logging.error(f"Erro ao conectar SQLite: {str(e)}")
        return None

def init_sqlite_database() -> bool:
    """
    Inicializar completamente o banco SQLite
    """
    logging.info("Inicializando banco SQLite...")
    
    # Verificar se database já existe
    db_path = Path(SQLITE_CONFIG['database_path'])
    if not db_path.exists():
        # Criar database se não existir
        if not create_sqlite_database():
            return False
    else:
        logging.info(f"Database SQLite já existe: {db_path.absolute()}")
    
    # Testar conexão
    engine = get_sqlite_engine()
    if engine is None:
        return False
    
    try:
        # Testar consulta básica
        with engine.connect() as conn:
            from sqlalchemy import text
            result = conn.execute(text("SELECT COUNT(*) FROM T_EQUIPAMENTO")).fetchone()
            logging.info(f"SQLite inicializado. Equipamentos: {result[0] if result else 0}")
        
        return True
    except Exception as e:
        logging.error(f"Erro ao testar SQLite: {str(e)}")
        return False

# ===========================================
# FUNÇÕES DE MIGRAÇÃO (OPCIONAL)
# ===========================================

def convert_oracle_to_sqlite_query(oracle_query: str) -> str:
    """
    Converter consultas Oracle para SQLite (básico)
    """
    # Substituições básicas
    sqlite_query = oracle_query
    
    # Oracle → SQLite conversions
    conversions = {
        'SYSDATE': "datetime('now')",
        'SYSTIMESTAMP': "datetime('now')",
        'CURRENT_TIMESTAMP': "datetime('now')",
        'INTERVAL': 'datetime',
        'NVL(': 'IFNULL(',
        'ROWNUM': 'ROWID',
        'VARCHAR2': 'TEXT',
        'NUMBER': 'REAL',
        'CHAR(1)': 'TEXT'
    }
    
    for oracle_syntax, sqlite_syntax in conversions.items():
        sqlite_query = sqlite_query.replace(oracle_syntax, sqlite_syntax)
    
    return sqlite_query

# ===========================================
# TESTE E VALIDAÇÃO
# ===========================================

def test_sqlite_setup() -> bool:
    """
    Testar configuração SQLite
    """
    try:
        logging.info("Testando configuração SQLite...")
        
        # Inicializar
        if not init_sqlite_database():
            return False
        
        # Testar operações básicas
        engine = get_sqlite_engine()
        
        with engine.connect() as conn:
            from sqlalchemy import text
            
            # Teste SELECT
            result = conn.execute(text("SELECT COUNT(*) FROM T_EQUIPAMENTO")).fetchone()
            equipamentos = result[0] if result else 0
            
            # Teste INSERT
            conn.execute(text("""
                INSERT OR IGNORE INTO T_MEDICAO 
                (id_sensor, id_maquina, vl_temperatura, vl_pressao, vl_vibracao, fonte_dados) 
                VALUES ('MPU_001', 'PUMP_001', 75.0, 1013.0, 2.0, 'TESTE')
            """))
            
            conn.commit()
            
            # Teste com pandas (importante para ML pipeline)
            import pandas as pd
            df = pd.read_sql(text("SELECT * FROM T_MEDICAO LIMIT 5"), conn)
            
            logging.info(f"✅ SQLite funcionando. Equipamentos: {equipamentos}, Medições teste: {len(df)}")
            return True
            
    except Exception as e:
        logging.error(f"❌ Erro no teste SQLite: {str(e)}")
        return False

# ===========================================
# EXECUÇÃO DIRETA
# ===========================================

if __name__ == "__main__":
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Executar teste
    success = test_sqlite_setup()
    
    if success:
        print("🎉 SQLite configurado com sucesso!")
        print(f"📁 Database: {Path(SQLITE_CONFIG['database_path']).absolute()}")
        print("✅ Pronto para executar o sistema!")
    else:
        print("❌ Falha na configuração SQLite")
        print("Verifique os logs para mais detalhes")
