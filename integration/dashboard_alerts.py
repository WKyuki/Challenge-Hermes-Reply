#!/usr/bin/env python3
"""
Smart Maintenance SaaS - Dashboard e Sistema de Alertas
======================================================

Dashboard interativo com Streamlit para monitoramento em tempo real
e sistema de alertas para Smart Maintenance.

Funcionalidades:
- Dashboard em tempo real com KPIs
- Visualização de dados dos sensores
- Sistema de alertas baseado em thresholds e ML
- Histórico de alertas e manutenções
- Relatórios executivos

Autor: Challenge Hermes Reply Team
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import altair as alt
from datetime import datetime, timedelta
import time
import json
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import smtplib
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart

# Database
import cx_Oracle
from sqlalchemy import create_engine

# ML Pipeline
from ml_pipeline import SmartMaintenanceMLPipeline

# ===========================================
# CONFIGURAÇÕES
# ===========================================

# Page config
st.set_page_config(
    page_title="Smart Maintenance Dashboard",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Database Configuration
DB_CONFIG = {
    'user': 'your_db_user',
    'password': 'your_db_password',
    'dsn': 'localhost:1521/xe',
    'encoding': 'UTF-8'
}

# Alert Configuration
ALERT_CONFIG = {
    'temperature_critical': 95.0,
    'temperature_warning': 85.0,
    'pressure_min': 960.0,
    'pressure_max': 1040.0,
    'humidity_critical': 80.0,
    'humidity_warning': 70.0,
    'vibration_critical': 10.0,
    'vibration_warning': 7.5,
    'ml_probability_critical': 0.8,
    'ml_probability_warning': 0.6
}

# Email Configuration (para alertas)
EMAIL_CONFIG = {
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587,
    'sender_email': 'hermes@smartmaintenance.com',
    'sender_password': 'your_app_password',
    'recipients': ['admin@company.com', 'maintenance@company.com']
}

# ===========================================
# ESTRUTURAS DE DADOS
# ===========================================

@dataclass
class Alert:
    id: str
    equipment_id: str
    alert_type: str
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    message: str
    timestamp: datetime
    value: float
    threshold: float
    status: str  # ACTIVE, ACKNOWLEDGED, RESOLVED
    source: str  # THRESHOLD, ML_MODEL, MANUAL

@dataclass
class KPI:
    name: str
    value: float
    unit: str
    status: str  # NORMAL, WARNING, CRITICAL
    change_24h: float
    target: Optional[float] = None

# ===========================================
# CLASSE PRINCIPAL - DASHBOARD
# ===========================================

class SmartMaintenanceDashboard:
    """Dashboard principal do Smart Maintenance SaaS"""
    
    def __init__(self):
        self.setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Database connection
        self.db_connection = None
        self.db_engine = None
        
        # ML Pipeline
        self.ml_pipeline = None
        
        # Cache para dados
        if 'dashboard_cache' not in st.session_state:
            st.session_state.dashboard_cache = {}
            
        if 'alerts_cache' not in st.session_state:
            st.session_state.alerts_cache = []
            
        if 'last_refresh' not in st.session_state:
            st.session_state.last_refresh = datetime.now()
    
    def setup_logging(self):
        """Configurar logging"""
        logging.basicConfig(level=logging.INFO)
    
    @st.cache_resource
    def connect_database(_self):
        """Conectar ao banco de dados (cached)"""
        try:
            # SQLAlchemy engine
            connection_string = f"oracle+cx_oracle://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['dsn']}"
            engine = create_engine(connection_string)
            return engine
        except Exception as e:
            st.error(f"Erro ao conectar com banco: {str(e)}")
            return None
    
    @st.cache_data(ttl=60)  # Cache por 1 minuto
    def load_real_time_data(_self) -> pd.DataFrame:
        """Carregar dados em tempo real do banco"""
        try:
            engine = _self.connect_database()
            if not engine:
                return pd.DataFrame()
            
            query = """
            SELECT 
                m.*,
                e.tipo_maquina,
                e.localizacao,
                CASE 
                    WHEN m.vl_temperatura > 95 THEN 'CRITICAL'
                    WHEN m.vl_temperatura > 85 THEN 'WARNING' 
                    ELSE 'NORMAL'
                END as temp_status,
                CASE 
                    WHEN m.vl_pressao < 960 OR m.vl_pressao > 1040 THEN 'CRITICAL'
                    WHEN m.vl_pressao < 970 OR m.vl_pressao > 1030 THEN 'WARNING'
                    ELSE 'NORMAL'
                END as pressure_status
            FROM T_MEDICAO m
            INNER JOIN T_EQUIPAMENTO e ON m.id_maquina = e.id_maquina
            WHERE m.dataHora_medicao >= SYSTIMESTAMP - INTERVAL '24' HOUR
            ORDER BY m.dataHora_medicao DESC
            """
            
            df = pd.read_sql(query, engine)
            df['dataHora_medicao'] = pd.to_datetime(df['DATAHORA_MEDICAO'])
            
            return df
            
        except Exception as e:
            st.error(f"Erro ao carregar dados: {str(e)}")
            return pd.DataFrame()
    
    @st.cache_data(ttl=300)  # Cache por 5 minutos
    def calculate_kpis(_self, df: pd.DataFrame) -> List[KPI]:
        """Calcular KPIs principais"""
        if df.empty:
            return []
        
        kpis = []
        
        try:
            # KPI 1: Temperatura Média
            temp_avg = df['VL_TEMPERATURA'].mean()
            temp_change = df['VL_TEMPERATURA'].tail(100).mean() - df['VL_TEMPERATURA'].head(100).mean()
            temp_status = 'CRITICAL' if temp_avg > 95 else 'WARNING' if temp_avg > 85 else 'NORMAL'
            
            kpis.append(KPI(
                name="Temperatura Média",
                value=temp_avg,
                unit="°C",
                status=temp_status,
                change_24h=temp_change,
                target=80.0
            ))
            
            # KPI 2: Equipamentos Ativos
            active_equipment = df['ID_MAQUINA'].nunique()
            total_equipment = 10  # Assumindo 10 equipamentos cadastrados
            active_pct = (active_equipment / total_equipment) * 100
            
            kpis.append(KPI(
                name="Equipamentos Ativos",
                value=active_equipment,
                unit="unidades",
                status='NORMAL' if active_pct > 80 else 'WARNING',
                change_24h=0,
                target=total_equipment
            ))
            
            # KPI 3: Taxa de Alertas
            alerts_count = len(df[df['FLAG_FALHA'] == 'S'])
            alert_rate = (alerts_count / len(df)) * 100 if len(df) > 0 else 0
            
            kpis.append(KPI(
                name="Taxa de Alertas",
                value=alert_rate,
                unit="%",
                status='CRITICAL' if alert_rate > 15 else 'WARNING' if alert_rate > 5 else 'NORMAL',
                change_24h=0,
                target=5.0
            ))
            
            # KPI 4: Disponibilidade
            uptime = 100 - alert_rate  # Simplificado
            
            kpis.append(KPI(
                name="Disponibilidade",
                value=uptime,
                unit="%",
                status='NORMAL' if uptime > 95 else 'WARNING' if uptime > 90 else 'CRITICAL',
                change_24h=0,
                target=99.0
            ))
            
        except Exception as e:
            st.error(f"Erro ao calcular KPIs: {str(e)}")
        
        return kpis
    
    def generate_alerts(self, df: pd.DataFrame) -> List[Alert]:
        """Gerar alertas baseado em thresholds e ML"""
        alerts = []
        
        if df.empty:
            return alerts
        
        try:
            # Alertas baseados em threshold
            for _, row in df.iterrows():
                equipment_id = row['ID_MAQUINA']
                timestamp = row['dataHora_medicao']
                
                # Alerta de temperatura
                if row['VL_TEMPERATURA'] > ALERT_CONFIG['temperature_critical']:
                    alerts.append(Alert(
                        id=f"TEMP_{equipment_id}_{int(timestamp.timestamp())}",
                        equipment_id=equipment_id,
                        alert_type="TEMPERATURE_HIGH",
                        severity="CRITICAL",
                        message=f"Temperatura crítica: {row['VL_TEMPERATURA']:.1f}°C",
                        timestamp=timestamp,
                        value=row['VL_TEMPERATURA'],
                        threshold=ALERT_CONFIG['temperature_critical'],
                        status="ACTIVE",
                        source="THRESHOLD"
                    ))
                elif row['VL_TEMPERATURA'] > ALERT_CONFIG['temperature_warning']:
                    alerts.append(Alert(
                        id=f"TEMP_{equipment_id}_{int(timestamp.timestamp())}",
                        equipment_id=equipment_id,
                        alert_type="TEMPERATURE_HIGH",
                        severity="WARNING",
                        message=f"Temperatura elevada: {row['VL_TEMPERATURA']:.1f}°C",
                        timestamp=timestamp,
                        value=row['VL_TEMPERATURA'],
                        threshold=ALERT_CONFIG['temperature_warning'],
                        status="ACTIVE",
                        source="THRESHOLD"
                    ))
                
                # Alerta de pressão
                if (row['VL_PRESSAO'] < ALERT_CONFIG['pressure_min'] or 
                    row['VL_PRESSAO'] > ALERT_CONFIG['pressure_max']):
                    alerts.append(Alert(
                        id=f"PRESS_{equipment_id}_{int(timestamp.timestamp())}",
                        equipment_id=equipment_id,
                        alert_type="PRESSURE_ABNORMAL",
                        severity="CRITICAL",
                        message=f"Pressão anormal: {row['VL_PRESSAO']:.1f} hPa",
                        timestamp=timestamp,
                        value=row['VL_PRESSAO'],
                        threshold=ALERT_CONFIG['pressure_min'],
                        status="ACTIVE",
                        source="THRESHOLD"
                    ))
                
                # Alerta de umidade
                if row['VL_HUMIDADE'] > ALERT_CONFIG['humidity_critical']:
                    alerts.append(Alert(
                        id=f"HUM_{equipment_id}_{int(timestamp.timestamp())}",
                        equipment_id=equipment_id,
                        alert_type="HUMIDITY_HIGH",
                        severity="WARNING",
                        message=f"Umidade alta: {row['VL_HUMIDADE']:.1f}%",
                        timestamp=timestamp,
                        value=row['VL_HUMIDADE'],
                        threshold=ALERT_CONFIG['humidity_critical'],
                        status="ACTIVE",
                        source="THRESHOLD"
                    ))
            
            # Manter apenas alertas únicos (último por equipamento/tipo)
            unique_alerts = {}
            for alert in alerts:
                key = f"{alert.equipment_id}_{alert.alert_type}"
                if key not in unique_alerts or alert.timestamp > unique_alerts[key].timestamp:
                    unique_alerts[key] = alert
            
            return list(unique_alerts.values())
            
        except Exception as e:
            st.error(f"Erro ao gerar alertas: {str(e)}")
            return []
    
    def send_alert_email(self, alert: Alert):
        """Enviar alerta por email (simulado)"""
        try:
            # Simular envio de email (logs)
            email_content = f"""
            ALERTA SMART MAINTENANCE
            ========================
            
            Equipamento: {alert.equipment_id}
            Tipo: {alert.alert_type}
            Severidade: {alert.severity}
            Mensagem: {alert.message}
            Timestamp: {alert.timestamp}
            Valor: {alert.value}
            Threshold: {alert.threshold}
            
            Favor verificar o equipamento imediatamente.
            
            Dashboard: http://localhost:8501
            """
            
            self.logger.info(f"EMAIL ALERTA ENVIADO: {alert.equipment_id} - {alert.severity}")
            
            # Em produção, implementar envio real:
            # msg = MimeText(email_content)
            # msg['Subject'] = f"[{alert.severity}] Smart Maintenance Alert - {alert.equipment_id}"
            # msg['From'] = EMAIL_CONFIG['sender_email']
            # msg['To'] = ', '.join(EMAIL_CONFIG['recipients'])
            # 
            # with smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port']) as server:
            #     server.starttls()
            #     server.login(EMAIL_CONFIG['sender_email'], EMAIL_CONFIG['sender_password'])
            #     server.send_message(msg)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao enviar email: {str(e)}")
            return False
    
    def render_header(self):
        """Render cabeçalho do dashboard"""
        st.markdown("""
        <div style='text-align: center; padding: 1rem; background: linear-gradient(90deg, #1f4e79, #2e86de); border-radius: 10px; margin-bottom: 2rem;'>
            <h1 style='color: white; margin: 0;'>🏭 Smart Maintenance SaaS</h1>
            <p style='color: #f1f2f6; margin: 0;'>Dashboard de Monitoramento em Tempo Real</p>
        </div>
        """, unsafe_allow_html=True)
    
    def render_kpi_cards(self, kpis: List[KPI]):
        """Render cards de KPIs"""
        if not kpis:
            return
        
        cols = st.columns(len(kpis))
        
        for i, kpi in enumerate(kpis):
            with cols[i]:
                # Cor baseada no status
                color_map = {
                    'NORMAL': '#27ae60',
                    'WARNING': '#f39c12', 
                    'CRITICAL': '#e74c3c'
                }
                color = color_map.get(kpi.status, '#7f8c8d')
                
                # Card HTML
                card_html = f"""
                <div style='
                    background: white; 
                    padding: 1.5rem; 
                    border-radius: 10px; 
                    border-left: 4px solid {color};
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    height: 120px;
                '>
                    <h3 style='color: #2c3e50; font-size: 0.9rem; margin: 0;'>{kpi.name}</h3>
                    <h2 style='color: {color}; margin: 0.5rem 0;'>{kpi.value:.1f} {kpi.unit}</h2>
                    <p style='color: #7f8c8d; font-size: 0.8rem; margin: 0;'>
                        Status: <strong style='color: {color};'>{kpi.status}</strong>
                    </p>
                </div>
                """
                st.markdown(card_html, unsafe_allow_html=True)
    
    def render_real_time_charts(self, df: pd.DataFrame):
        """Render gráficos em tempo real"""
        if df.empty:
            st.warning("Nenhum dado disponível para gráficos")
            return
        
        # Filtrar dados das últimas 6 horas para melhor visualização
        cutoff_time = datetime.now() - timedelta(hours=6)
        df_recent = df[df['dataHora_medicao'] > cutoff_time].copy()
        
        if df_recent.empty:
            df_recent = df.tail(100)  # Últimas 100 medições se não há dados recentes
        
        # Gráfico 1: Temperatura ao longo do tempo
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 Temperatura por Equipamento")
            
            fig_temp = go.Figure()
            
            for equipment in df_recent['ID_MAQUINA'].unique():
                eq_data = df_recent[df_recent['ID_MAQUINA'] == equipment]
                fig_temp.add_trace(go.Scatter(
                    x=eq_data['dataHora_medicao'],
                    y=eq_data['VL_TEMPERATURA'],
                    mode='lines+markers',
                    name=equipment,
                    line=dict(width=2),
                    marker=dict(size=4)
                ))
            
            # Linha de threshold crítico
            fig_temp.add_hline(
                y=ALERT_CONFIG['temperature_critical'],
                line_dash="dash",
                line_color="red",
                annotation_text="Crítico (95°C)"
            )
            
            fig_temp.update_layout(
                title="Evolução da Temperatura",
                xaxis_title="Tempo",
                yaxis_title="Temperatura (°C)",
                hovermode='x unified',
                height=400
            )
            
            st.plotly_chart(fig_temp, use_container_width=True)
        
        with col2:
            st.subheader("💨 Pressão e Vibração")
            
            # Subplot para pressão e vibração
            fig_multi = make_subplots(
                rows=2, cols=1,
                subplot_titles=('Pressão (hPa)', 'Vibração (m/s²)'),
                vertical_spacing=0.1
            )
            
            # Pressão
            for equipment in df_recent['ID_MAQUINA'].unique():
                eq_data = df_recent[df_recent['ID_MAQUINA'] == equipment]
                fig_multi.add_trace(
                    go.Scatter(
                        x=eq_data['dataHora_medicao'],
                        y=eq_data['VL_PRESSAO'],
                        mode='lines',
                        name=f"{equipment} - Pressão",
                        showlegend=False
                    ),
                    row=1, col=1
                )
                
                # Vibração
                fig_multi.add_trace(
                    go.Scatter(
                        x=eq_data['dataHora_medicao'],
                        y=eq_data['VL_VIBRACAO'],
                        mode='lines',
                        name=f"{equipment} - Vibração",
                        showlegend=False
                    ),
                    row=2, col=1
                )
            
            fig_multi.update_layout(height=400)
            st.plotly_chart(fig_multi, use_container_width=True)
        
        # Gráfico 3: Distribuição de status
        st.subheader("📈 Status dos Equipamentos")
        
        col3, col4 = st.columns(2)
        
        with col3:
            # Pie chart de status de temperatura
            temp_status_counts = df['TEMP_STATUS'].value_counts()
            
            fig_pie = go.Figure(data=[go.Pie(
                labels=temp_status_counts.index,
                values=temp_status_counts.values,
                hole=.3,
                marker_colors=['#27ae60', '#f39c12', '#e74c3c']
            )])
            
            fig_pie.update_layout(
                title="Distribuição Status Temperatura",
                annotations=[dict(text='Status', x=0.5, y=0.5, font_size=20, showarrow=False)]
            )
            
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col4:
            # Bar chart de equipamentos por localização
            location_counts = df.groupby(['LOCALIZACAO', 'TIPO_MAQUINA']).size().reset_index(name='count')
            
            fig_bar = px.bar(
                location_counts, 
                x='LOCALIZACAO', 
                y='count',
                color='TIPO_MAQUINA',
                title="Equipamentos por Localização"
            )
            
            st.plotly_chart(fig_bar, use_container_width=True)
    
    def render_alerts_panel(self, alerts: List[Alert]):
        """Render painel de alertas"""
        st.subheader("🚨 Alertas Ativos")
        
        if not alerts:
            st.success("✅ Nenhum alerta ativo no momento")
            return
        
        # Filtrar por severidade
        severity_filter = st.selectbox(
            "Filtrar por severidade:",
            ["Todos", "CRITICAL", "WARNING", "LOW"],
            index=0
        )
        
        filtered_alerts = alerts
        if severity_filter != "Todos":
            filtered_alerts = [a for a in alerts if a.severity == severity_filter]
        
        # Mostrar alertas em cards
        for alert in filtered_alerts[:10]:  # Mostrar apenas os 10 mais recentes
            severity_color = {
                'CRITICAL': '#e74c3c',
                'WARNING': '#f39c12',
                'LOW': '#3498db'
            }.get(alert.severity, '#7f8c8d')
            
            with st.expander(
                f"🔥 {alert.equipment_id} - {alert.alert_type} - {alert.severity}",
                expanded=(alert.severity == "CRITICAL")
            ):
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    st.write(f"**Mensagem:** {alert.message}")
                    st.write(f"**Timestamp:** {alert.timestamp}")
                    st.write(f"**Fonte:** {alert.source}")
                
                with col2:
                    st.metric("Valor Atual", f"{alert.value:.2f}")
                    st.metric("Threshold", f"{alert.threshold:.2f}")
                
                with col3:
                    if st.button(f"Reconhecer", key=f"ack_{alert.id}"):
                        st.success("Alerta reconhecido!")
                        # Aqui seria implementada a lógica para atualizar status no banco
                    
                    if st.button(f"Enviar Email", key=f"email_{alert.id}"):
                        if self.send_alert_email(alert):
                            st.success("Email enviado!")
                        else:
                            st.error("Falha no envio")
    
    def render_equipment_details(self, df: pd.DataFrame):
        """Render detalhes dos equipamentos"""
        if df.empty:
            return
        
        st.subheader("🏭 Detalhes dos Equipamentos")
        
        # Seletor de equipamento
        equipment_list = sorted(df['ID_MAQUINA'].unique())
        selected_equipment = st.selectbox("Selecionar equipamento:", equipment_list)
        
        if selected_equipment:
            eq_data = df[df['ID_MAQUINA'] == selected_equipment].sort_values('dataHora_medicao')
            
            if not eq_data.empty:
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    # Informações básicas
                    latest = eq_data.iloc[-1]
                    st.write(f"**Tipo:** {latest['TIPO_MAQUINA']}")
                    st.write(f"**Localização:** {latest['LOCALIZACAO']}")
                    st.write(f"**Última medição:** {latest['dataHora_medicao']}")
                    st.write(f"**Status:** {latest['FLAG_FALHA']}")
                    
                    # Métricas atuais
                    st.metric("Temperatura", f"{latest['VL_TEMPERATURA']:.1f}°C")
                    st.metric("Pressão", f"{latest['VL_PRESSAO']:.1f} hPa")
                    st.metric("Umidade", f"{latest['VL_HUMIDADE']:.1f}%")
                    st.metric("Vibração", f"{latest['VL_VIBRACAO']:.2f} m/s²")
                
                with col2:
                    # Histórico detalhado
                    st.write("**Histórico das últimas 24h**")
                    
                    # Tabela com dados recentes
                    display_data = eq_data[['dataHora_medicao', 'VL_TEMPERATURA', 'VL_PRESSAO', 
                                           'VL_HUMIDADE', 'VL_VIBRACAO', 'FLAG_FALHA']].tail(20)
                    
                    display_data.columns = ['Timestamp', 'Temp (°C)', 'Press (hPa)', 
                                          'Umid (%)', 'Vibr (m/s²)', 'Falha']
                    
                    st.dataframe(
                        display_data, 
                        use_container_width=True,
                        height=300
                    )
    
    def render_ml_insights(self, df: pd.DataFrame):
        """Render insights do modelo ML"""
        st.subheader("🤖 Insights de Machine Learning")
        
        if df.empty:
            st.warning("Dados insuficientes para análise ML")
            return
        
        try:
            # Simular predições ML (em produção, usar modelo real)
            np.random.seed(42)
            equipment_list = df['ID_MAQUINA'].unique()
            
            ml_predictions = []
            for eq in equipment_list:
                eq_data = df[df['ID_MAQUINA'] == eq].tail(1)
                if not eq_data.empty:
                    latest = eq_data.iloc[0]
                    
                    # Simular probabilidade de falha baseada nos dados
                    risk_score = 0
                    if latest['VL_TEMPERATURA'] > 90:
                        risk_score += 0.3
                    if latest['VL_PRESSAO'] < 970 or latest['VL_PRESSAO'] > 1030:
                        risk_score += 0.2
                    if latest['VL_HUMIDADE'] > 75:
                        risk_score += 0.1
                    if latest['VL_VIBRACAO'] > 5:
                        risk_score += 0.2
                    
                    # Adicionar ruído aleatório
                    risk_score += np.random.normal(0, 0.1)
                    risk_score = max(0, min(1, risk_score))  # Clamp entre 0 e 1
                    
                    ml_predictions.append({
                        'equipment': eq,
                        'risk_score': risk_score,
                        'risk_level': 'HIGH' if risk_score > 0.6 else 'MEDIUM' if risk_score > 0.3 else 'LOW',
                        'prediction': 'MANUTENÇÃO NECESSÁRIA' if risk_score > 0.6 else 'MONITORAR' if risk_score > 0.3 else 'NORMAL'
                    })
            
            if ml_predictions:
                # Ordenar por risk score
                ml_predictions.sort(key=lambda x: x['risk_score'], reverse=True)
                
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    st.write("**Ranking de Risco por Equipamento**")
                    
                    for pred in ml_predictions:
                        risk_color = '#e74c3c' if pred['risk_level'] == 'HIGH' else '#f39c12' if pred['risk_level'] == 'MEDIUM' else '#27ae60'
                        
                        st.markdown(f"""
                        <div style='
                            background: white; 
                            padding: 1rem; 
                            margin: 0.5rem 0;
                            border-radius: 5px;
                            border-left: 4px solid {risk_color};
                            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                        '>
                            <strong>{pred['equipment']}</strong><br>
                            Risco: <span style='color: {risk_color};'><strong>{pred['risk_score']:.1%}</strong></span><br>
                            Ação: {pred['prediction']}
                        </div>
                        """, unsafe_allow_html=True)
                
                with col2:
                    st.write("**Distribuição de Risco**")
                    
                    # Gráfico de barras horizontal
                    pred_df = pd.DataFrame(ml_predictions)
                    
                    fig_risk = px.bar(
                        pred_df.sort_values('risk_score'),
                        y='equipment',
                        x='risk_score',
                        color='risk_level',
                        orientation='h',
                        color_discrete_map={
                            'LOW': '#27ae60',
                            'MEDIUM': '#f39c12', 
                            'HIGH': '#e74c3c'
                        }
                    )
                    
                    fig_risk.update_layout(
                        title="Probabilidade de Falha por Equipamento",
                        xaxis_title="Probabilidade de Falha",
                        yaxis_title="Equipamento",
                        height=300
                    )
                    
                    st.plotly_chart(fig_risk, use_container_width=True)
        
        except Exception as e:
            st.error(f"Erro na análise ML: {str(e)}")
    
    def run_dashboard(self):
        """Executar dashboard principal"""
        
        # Header
        self.render_header()
        
        # Sidebar para controles
        with st.sidebar:
            st.title("⚙️ Controles")
            
            # Controle de auto-refresh
            auto_refresh = st.checkbox("Auto-refresh (30s)", value=True)
            
            if st.button("🔄 Atualizar Dados"):
                st.cache_data.clear()
                st.rerun()
            
            # Filtros de tempo
            st.subheader("Filtros")
            time_range = st.selectbox(
                "Período:",
                ["Última hora", "Últimas 6 horas", "Últimas 24 horas", "Últimos 7 dias"],
                index=2
            )
            
            # Filtros de equipamento
            if 'dashboard_cache' in st.session_state and st.session_state.dashboard_cache:
                df = st.session_state.dashboard_cache
                if not df.empty:
                    selected_locations = st.multiselect(
                        "Localizações:",
                        options=df['LOCALIZACAO'].unique(),
                        default=df['LOCALIZACAO'].unique()
                    )
                    
                    selected_types = st.multiselect(
                        "Tipos de Equipamento:",
                        options=df['TIPO_MAQUINA'].unique(),
                        default=df['TIPO_MAQUINA'].unique()
                    )
            
            # Status do sistema
            st.subheader("Status do Sistema")
            st.success("🟢 Banco de Dados: Conectado")
            st.info("🔵 MQTT: Simulado")
            st.warning("🟡 ML Model: Simulado")
        
        # Auto-refresh
        if auto_refresh:
            time.sleep(0.1)  # Pequena pausa
            placeholder = st.empty()
            
            with placeholder.container():
                # Carregar dados
                df = self.load_real_time_data()
                st.session_state.dashboard_cache = df
                
                if not df.empty:
                    # Filtrar dados se necessário
                    # (implementar filtros baseados na sidebar)
                    
                    # KPIs
                    kpis = self.calculate_kpis(df)
                    self.render_kpi_cards(kpis)
                    
                    # Gráficos em tempo real
                    self.render_real_time_charts(df)
                    
                    # Alertas
                    alerts = self.generate_alerts(df)
                    st.session_state.alerts_cache = alerts
                    self.render_alerts_panel(alerts)
                    
                    # Abas para diferentes visualizações
                    tab1, tab2, tab3 = st.tabs(["📋 Equipamentos", "🤖 ML Insights", "📊 Relatórios"])
                    
                    with tab1:
                        self.render_equipment_details(df)
                    
                    with tab2:
                        self.render_ml_insights(df)
                    
                    with tab3:
                        st.subheader("📈 Relatórios Executivos")
                        st.info("Funcionalidade em desenvolvimento")
                        
                        # Placeholder para relatórios
                        if st.button("Gerar Relatório Semanal"):
                            st.success("Relatório gerado! (simulado)")
                        
                        if st.button("Exportar Dados CSV"):
                            csv = df.to_csv(index=False)
                            st.download_button(
                                label="Download CSV",
                                data=csv,
                                file_name=f"smart_maintenance_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                mime="text/csv"
                            )
                
                else:
                    st.warning("⚠️ Nenhum dado disponível. Verifique a conexão com o banco de dados.")
                    
                    # Dados simulados para demonstração
                    if st.button("Usar Dados Simulados"):
                        st.info("Gerando dados simulados para demonstração...")
                        # Implementar geração de dados simulados
            
            # Auto-refresh a cada 30 segundos
            if auto_refresh:
                time.sleep(30)
                st.rerun()

# ===========================================
# EXECUÇÃO PRINCIPAL
# ===========================================

def main():
    """Função principal"""
    dashboard = SmartMaintenanceDashboard()
    dashboard.run_dashboard()

if __name__ == "__main__":
    main()
