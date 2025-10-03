#!/usr/bin/env python3
"""
Smart Maintenance SaaS - Execução com SQLite
==========================================

Script simplificado para executar o sistema usando SQLite
ao invés do Oracle Database.

Uso:
    python3 run_sqlite_system.py --mode dashboard
    python3 run_sqlite_system.py --mode demo

Autor: Challenge Hermes Reply Team
"""

import sys
import os
import argparse
import subprocess
import logging
import sqlite3
from pathlib import Path
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Importar configuração SQLite
from sqlite_config import init_sqlite_database, get_sqlite_engine

def setup_sqlite_environment():
    """Configurar ambiente SQLite"""
    print("🔧 Configurando ambiente SQLite...")
    
    # Inicializar banco
    success = init_sqlite_database()
    if not success:
        print("❌ Falha ao inicializar SQLite")
        return False
    
    print("✅ SQLite configurado com sucesso")
    return True

def run_dashboard_sqlite():
    """Executar apenas o dashboard com SQLite"""
    print("🚀 Iniciando Dashboard com SQLite...")
    
    # Verificar se dashboard_demo.py existe
    dashboard_script = Path(__file__).parent / "dashboard_demo.py"
    
    if not dashboard_script.exists():
        print("📝 Criando dashboard simplificado...")
        create_simple_dashboard()
        dashboard_script = Path(__file__).parent / "dashboard_simple.py"
    
    try:
        # Executar Streamlit
        cmd = [
            sys.executable, "-m", "streamlit", "run",
            str(dashboard_script),
            "--server.port", "8501",
            "--server.address", "0.0.0.0",
            "--server.headless", "true"
        ]
        
        print("Dashboard disponível em: http://localhost:8501")
        print("Pressione Ctrl+C para parar")
        
        subprocess.run(cmd)
        
    except KeyboardInterrupt:
        print("\n👋 Dashboard encerrado")
    except Exception as e:
        print(f"❌ Erro ao executar dashboard: {str(e)}")

def create_simple_dashboard():
    """Criar dashboard simplificado para SQLite"""
    dashboard_code = '''#!/usr/bin/env python3
"""
Dashboard Simplificado - SQLite
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sqlite3
from pathlib import Path

# Configuração da página
st.set_page_config(
    page_title="Smart Maintenance SaaS",
    page_icon="🏭",
    layout="wide"
)

@st.cache_data(ttl=30)
def load_data():
    """Carregar dados do SQLite"""
    try:
        db_path = Path("smart_maintenance.db")
        if not db_path.exists():
            st.error("❌ Banco SQLite não encontrado!")
            return None, None, None
            
        conn = sqlite3.connect(str(db_path))
        
        # Dados dos equipamentos
        equipamentos = pd.read_sql("""
            SELECT * FROM T_EQUIPAMENTO
        """, conn)
        
        # Dados das medições
        medicoes = pd.read_sql("""
            SELECT 
                m.*,
                e.tipo_maquina,
                e.localizacao
            FROM T_MEDICAO m
            JOIN T_EQUIPAMENTO e ON m.id_maquina = e.id_maquina
            ORDER BY m.dataHora_medicao DESC
            LIMIT 1000
        """, conn)
        
        # Estatísticas
        stats = pd.read_sql("""
            SELECT * FROM V_STATS_EQUIPAMENTO
        """, conn)
        
        conn.close()
        return equipamentos, medicoes, stats
        
    except Exception as e:
        st.error(f"Erro ao carregar dados: {str(e)}")
        return None, None, None

def main():
    # Título
    st.title("🏭 Smart Maintenance SaaS")
    st.markdown("### Sistema de Manutenção Preditiva Industrial")
    
    # Carregar dados
    equipamentos, medicoes, stats = load_data()
    
    if medicoes is None:
        st.stop()
    
    # Métricas principais
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Equipamentos",
            len(equipamentos) if equipamentos is not None else 0,
            delta=None
        )
    
    with col2:
        st.metric(
            "Total Medições",
            len(medicoes),
            delta=f"+{len(medicoes.tail(100))} (últimas 100)"
        )
    
    with col3:
        temp_media = medicoes['vl_temperatura'].mean() if 'vl_temperatura' in medicoes.columns else 0
        st.metric(
            "Temperatura Média",
            f"{temp_media:.1f}°C",
            delta=f"{'🔥' if temp_media > 85 else '✅'}"
        )
    
    with col4:
        falhas = len(medicoes[medicoes['flag_falha'] == 'S']) if 'flag_falha' in medicoes.columns else 0
        st.metric(
            "Alertas Ativos",
            falhas,
            delta=f"{'⚠️' if falhas > 0 else '✅'}"
        )
    
    # Gráficos
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Temperatura por Equipamento")
        if 'vl_temperatura' in medicoes.columns:
            fig = px.box(
                medicoes, 
                x='id_maquina', 
                y='vl_temperatura',
                title="Distribuição de Temperatura"
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("🔥 Alertas por Equipamento")
        if stats is not None and not stats.empty:
            fig = px.bar(
                stats,
                x='id_maquina',
                y='total_falhas',
                title="Total de Falhas por Equipamento"
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
    
    # Tabela de dados recentes
    st.subheader("📋 Medições Recentes")
    
    if not medicoes.empty:
        # Mostrar apenas colunas relevantes
        display_cols = [
            'id_maquina', 'id_sensor', 'dataHora_medicao',
            'vl_temperatura', 'vl_pressao', 'vl_humidade', 'flag_falha'
        ]
        
        available_cols = [col for col in display_cols if col in medicoes.columns]
        
        st.dataframe(
            medicoes[available_cols].head(20),
            use_container_width=True
        )
    
    # Informações do sistema
    with st.sidebar:
        st.header("ℹ️ Informações do Sistema")
        st.info(f"""
        **Database:** SQLite  
        **Último Update:** {datetime.now().strftime("%H:%M:%S")}  
        **Status:** ✅ Online
        """)
        
        if st.button("🔄 Recarregar Dados"):
            st.cache_data.clear()
            st.rerun()

if __name__ == "__main__":
    main()
'''
    
    # Escrever arquivo
    with open("dashboard_simple.py", "w", encoding="utf-8") as f:
        f.write(dashboard_code)
    
    print("✅ Dashboard simplificado criado: dashboard_simple.py")

def run_demo_mode():
    """Executar modo demo com dados simulados"""
    print("🎯 Executando modo DEMO...")
    
    # Gerar dados de exemplo
    generate_demo_data()
    
    # Executar dashboard
    run_dashboard_sqlite()

def generate_demo_data():
    """Gerar dados de demonstração"""
    print("📊 Gerando dados de demonstração...")
    
    try:
        conn = sqlite3.connect("smart_maintenance.db")
        
        # Gerar medições simuladas
        import random
        import json
        from datetime import datetime, timedelta
        
        equipamentos = ['PUMP_001', 'TURB_001', 'COMP_001', 'PUMP_002', 'MOTOR_001']
        sensores = ['MPU_001', 'DHT_001', 'PRES_001', 'VIBR_001']
        
        # Gerar 100 medições aleatórias
        for i in range(100):
            timestamp = datetime.now() - timedelta(minutes=random.randint(1, 1440))  # Últimas 24h
            equip = random.choice(equipamentos)
            sensor = random.choice(sensores)
            
            # Simular valores com variação
            temp = random.normalvariate(80, 15)
            pressao = random.normalvariate(1013, 30)
            vibracao = random.exponential(2)
            humidade = random.uniform(30, 80)
            
            # Simular falha baseada na temperatura
            falha = 'S' if temp > 95 or random.random() < 0.05 else 'N'
            
            conn.execute('''
                INSERT INTO T_MEDICAO 
                (id_sensor, id_maquina, dataHora_medicao, vl_temperatura, vl_pressao, vl_vibracao, vl_humidade, flag_falha, fonte_dados)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (sensor, equip, timestamp.isoformat(), temp, pressao, vibracao, humidade, falha, 'DEMO'))
        
        conn.commit()
        conn.close()
        
        print("✅ 100 medições de demonstração geradas")
        
    except Exception as e:
        print(f"❌ Erro ao gerar dados demo: {str(e)}")

def main():
    """Função principal"""
    parser = argparse.ArgumentParser(description="Smart Maintenance com SQLite")
    parser.add_argument(
        "--mode",
        choices=["dashboard", "demo"],
        default="dashboard",
        help="Modo de execução"
    )
    
    args = parser.parse_args()
    
    print("🏭 Smart Maintenance SaaS - SQLite Edition")
    print("=" * 50)
    
    # Configurar SQLite
    if not setup_sqlite_environment():
        return
    
    # Executar modo selecionado
    if args.mode == "dashboard":
        run_dashboard_sqlite()
    elif args.mode == "demo":
        run_demo_mode()

if __name__ == "__main__":
    main()
