#!/usr/bin/env python3
"""
Smart Maintenance SaaS - Dashboard Simplificado
===============================================

Dashboard básico para demonstração do sistema Smart Maintenance SaaS
Funciona apenas com as bibliotecas essenciais já instaladas.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import time
import json

# ===========================================
# CONFIGURAÇÃO DA PÁGINA
# ===========================================

st.set_page_config(
    page_title="Smart Maintenance Dashboard",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===========================================
# FUNÇÕES AUXILIARES
# ===========================================

@st.cache_data
def generate_sample_data():
    """Gerar dados de exemplo para demonstração"""
    
    # Simular dados dos últimos 30 dias
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    # Criar timeline
    timestamps = pd.date_range(start_date, end_date, freq='H')
    
    data = []
    for i, timestamp in enumerate(timestamps):
        # Simular 5 equipamentos
        for equipment_id in range(1, 6):
            # Simular temperatura com variação
            base_temp = 70 + equipment_id * 5
            temp_variation = np.sin(i * 0.1) * 10 + np.random.normal(0, 3)
            temperature = base_temp + temp_variation
            
            # Simular outros parâmetros
            pressure = np.random.normal(1013, 20)
            humidity = np.random.uniform(30, 80)
            vibration = np.random.exponential(2)
            
            # Simular falhas ocasionais
            fault_probability = 0.05
            if temperature > 95:
                fault_probability = 0.8
            
            is_fault = np.random.random() < fault_probability
            
            data.append({
                'timestamp': timestamp,
                'equipment_id': f'PUMP_{equipment_id:03d}',
                'temperature': temperature,
                'pressure': pressure,
                'humidity': humidity,
                'vibration': vibration,
                'fault': is_fault,
                'location': f'Factory_{chr(65 + equipment_id % 3)}',
                'type': 'Pump'
            })
    
    return pd.DataFrame(data)

def calculate_kpis(df):
    """Calcular KPIs principais"""
    
    # Filtrar dados das últimas 24 horas
    recent_data = df[df['timestamp'] >= (datetime.now() - timedelta(hours=24))]
    
    kpis = {
        'avg_temperature': recent_data['temperature'].mean(),
        'active_equipment': recent_data['equipment_id'].nunique(),
        'total_equipment': df['equipment_id'].nunique(),
        'alert_rate': (recent_data['fault'].sum() / len(recent_data)) * 100,
        'availability': 100 - (recent_data['fault'].sum() / len(recent_data)) * 100
    }
    
    return kpis

def generate_alerts(df):
    """Gerar alertas baseados em thresholds"""
    
    recent_data = df[df['timestamp'] >= (datetime.now() - timedelta(hours=1))]
    alerts = []
    
    for _, row in recent_data.iterrows():
        alert_type = None
        severity = None
        
        if row['temperature'] > 95:
            alert_type = "TEMPERATURE_HIGH"
            severity = "CRITICAL"
        elif row['temperature'] > 85:
            alert_type = "TEMPERATURE_HIGH" 
            severity = "WARNING"
        
        if row['pressure'] < 960 or row['pressure'] > 1040:
            alert_type = "PRESSURE_ABNORMAL"
            severity = "CRITICAL"
        
        if row['humidity'] > 80:
            alert_type = "HUMIDITY_HIGH"
            severity = "WARNING"
        
        if alert_type:
            alerts.append({
                'equipment_id': row['equipment_id'],
                'alert_type': alert_type,
                'severity': severity,
                'value': row['temperature'] if 'TEMPERATURE' in alert_type else row['pressure'],
                'timestamp': row['timestamp']
            })
    
    return alerts

# ===========================================
# INTERFACE PRINCIPAL
# ===========================================

def main():
    """Função principal do dashboard"""
    
    # Header
    st.markdown("""
    <div style='text-align: center; padding: 1rem; background: linear-gradient(90deg, #1f4e79, #2e86de); border-radius: 10px; margin-bottom: 2rem;'>
        <h1 style='color: white; margin: 0;'>🏭 Smart Maintenance SaaS</h1>
        <p style='color: #f1f2f6; margin: 0;'>Dashboard de Monitoramento em Tempo Real - DEMO</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.title("⚙️ Controles")
        
        # Auto-refresh
        auto_refresh = st.checkbox("Auto-refresh (30s)", value=False)
        
        if st.button("🔄 Atualizar Dados"):
            st.cache_data.clear()
            st.rerun()
        
        # Filtros
        st.subheader("Filtros")
        time_range = st.selectbox(
            "Período:",
            ["Última hora", "Últimas 6 horas", "Últimas 24 horas", "Últimos 7 dias"],
            index=2
        )
        
        # Status
        st.subheader("Status do Sistema")
        st.success("🟢 Dashboard: Ativo")
        st.info("🔵 Dados: Simulados")
        st.warning("🟡 Base Real: Não conectada")
    
    # Carregar dados
    df = generate_sample_data()
    kpis = calculate_kpis(df)
    alerts = generate_alerts(df)
    
    # KPIs
    st.subheader("📊 Indicadores Principais")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "🌡️ Temperatura Média",
            f"{kpis['avg_temperature']:.1f}°C",
            delta=f"+1.2°C",
            delta_color="inverse"
        )
    
    with col2:
        st.metric(
            "🏭 Equipamentos Ativos",
            f"{kpis['active_equipment']}/{kpis['total_equipment']}",
            delta=f"{(kpis['active_equipment']/kpis['total_equipment']*100):.0f}%"
        )
    
    with col3:
        st.metric(
            "⚠️ Taxa de Alertas",
            f"{kpis['alert_rate']:.1f}%",
            delta=f"-2.3%",
            delta_color="inverse"
        )
    
    with col4:
        st.metric(
            "✅ Disponibilidade",
            f"{kpis['availability']:.1f}%",
            delta=f"+0.5%"
        )
    
    # Gráficos
    st.subheader("📈 Monitoramento em Tempo Real")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Temperatura por Equipamento (Últimas 24h)**")
        
        # Filtrar últimas 24 horas
        recent_df = df[df['timestamp'] >= (datetime.now() - timedelta(hours=24))]
        
        fig_temp = go.Figure()
        
        for equipment in recent_df['equipment_id'].unique():
            eq_data = recent_df[recent_df['equipment_id'] == equipment]
            fig_temp.add_trace(go.Scatter(
                x=eq_data['timestamp'],
                y=eq_data['temperature'],
                mode='lines+markers',
                name=equipment,
                line=dict(width=2),
                marker=dict(size=4)
            ))
        
        # Linha de threshold crítico
        fig_temp.add_hline(
            y=95,
            line_dash="dash",
            line_color="red",
            annotation_text="Crítico (95°C)"
        )
        
        fig_temp.update_layout(
            height=400,
            xaxis_title="Tempo",
            yaxis_title="Temperatura (°C)",
            hovermode='x unified'
        )
        
        st.plotly_chart(fig_temp, use_container_width=True)
    
    with col2:
        st.write("**Distribuição de Status**")
        
        # Calcular status por temperatura
        temp_status = []
        for temp in recent_df['temperature']:
            if temp > 95:
                temp_status.append('CRITICAL')
            elif temp > 85:
                temp_status.append('WARNING')
            else:
                temp_status.append('NORMAL')
        
        status_counts = pd.Series(temp_status).value_counts()
        
        fig_pie = go.Figure(data=[go.Pie(
            labels=status_counts.index,
            values=status_counts.values,
            hole=.3,
            marker_colors=['#27ae60', '#f39c12', '#e74c3c']
        )])
        
        fig_pie.update_layout(
            height=400,
            annotations=[dict(text='Status', x=0.5, y=0.5, font_size=20, showarrow=False)]
        )
        
        st.plotly_chart(fig_pie, use_container_width=True)
    
    # Gráfico de pressão
    st.write("**Pressão e Vibração por Equipamento**")
    
    fig_multi = go.Figure()
    
    # Adicionar pressão
    for equipment in recent_df['equipment_id'].unique():
        eq_data = recent_df[recent_df['equipment_id'] == equipment]
        fig_multi.add_trace(go.Scatter(
            x=eq_data['timestamp'],
            y=eq_data['pressure'],
            mode='lines',
            name=f"{equipment} - Pressão",
            yaxis='y'
        ))
    
    # Adicionar vibração no eixo secundário
    for equipment in recent_df['equipment_id'].unique():
        eq_data = recent_df[recent_df['equipment_id'] == equipment]
        fig_multi.add_trace(go.Scatter(
            x=eq_data['timestamp'],
            y=eq_data['vibration'],
            mode='lines',
            name=f"{equipment} - Vibração",
            yaxis='y2',
            line=dict(dash='dash')
        ))
    
    fig_multi.update_layout(
        height=400,
        xaxis_title="Tempo",
        yaxis=dict(title="Pressão (hPa)", side='left'),
        yaxis2=dict(title="Vibração (m/s²)", side='right', overlaying='y'),
        hovermode='x unified'
    )
    
    st.plotly_chart(fig_multi, use_container_width=True)
    
    # Alertas
    st.subheader("🚨 Alertas Ativos")
    
    if alerts:
        alert_df = pd.DataFrame(alerts)
        
        # Contar alertas por severidade
        severity_counts = alert_df['severity'].value_counts()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            critical_count = severity_counts.get('CRITICAL', 0)
            st.metric("🔥 Críticos", critical_count)
        
        with col2:
            warning_count = severity_counts.get('WARNING', 0)
            st.metric("⚠️ Avisos", warning_count)
        
        with col3:
            st.metric("📧 Notificações", len(alerts))
        
        # Lista de alertas
        st.write("**Últimos Alertas:**")
        
        for alert in alerts[-10:]:  # Mostrar últimos 10
            severity_icon = "🔥" if alert['severity'] == 'CRITICAL' else "⚠️"
            st.write(f"{severity_icon} **{alert['equipment_id']}** - {alert['alert_type']} - Valor: {alert['value']:.1f}")
    
    else:
        st.success("✅ Nenhum alerta ativo no momento")
    
    # Tabela de equipamentos
    st.subheader("🏭 Status dos Equipamentos")
    
    # Criar resumo por equipamento
    equipment_summary = recent_df.groupby('equipment_id').agg({
        'temperature': ['mean', 'max'],
        'pressure': 'mean',
        'humidity': 'mean',
        'vibration': 'mean',
        'fault': 'sum',
        'timestamp': 'max'
    }).round(2)
    
    # Flatten columns
    equipment_summary.columns = ['Temp_Média', 'Temp_Máxima', 'Pressão_Média', 
                                'Umidade_Média', 'Vibração_Média', 'Total_Falhas', 'Última_Leitura']
    
    # Status
    equipment_summary['Status'] = equipment_summary.apply(
        lambda row: '🔥 CRÍTICO' if row['Temp_Máxima'] > 95 or row['Total_Falhas'] > 2
        else '⚠️ ATENÇÃO' if row['Temp_Máxima'] > 85 or row['Total_Falhas'] > 0
        else '✅ OK', axis=1
    )
    
    st.dataframe(
        equipment_summary,
        use_container_width=True,
        height=300
    )
    
    # Informações do sistema
    st.subheader("ℹ️ Informações do Sistema")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.info(f"""
        **Dados Simulados**
        - Registros: {len(df):,}
        - Período: 30 dias
        - Equipamentos: {df['equipment_id'].nunique()}
        - Última atualização: {datetime.now().strftime('%H:%M:%S')}
        """)
    
    with col2:
        st.info(f"""
        **Métricas ML (Simuladas)**
        - Modelo: Random Forest
        - Accuracy: 94.56%
        - F1-Score: 0.9234
        - Predições hoje: 1,247
        """)
    
    with col3:
        st.info(f"""
        **Performance**
        - Latência: < 2s
        - Throughput: 1,000 rec/min
        - Uptime: 99.2%
        - Alertas enviados: {len(alerts)}
        """)
    
    # Auto-refresh
    if auto_refresh:
        time.sleep(30)
        st.rerun()

# ===========================================
# EXECUÇÃO
# ===========================================

if __name__ == "__main__":
    main()
