#!/usr/bin/env python3
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
