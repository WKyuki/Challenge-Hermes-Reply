#!/usr/bin/env python3
"""
Smart Maintenance SaaS - Gerador de Diagrama de Arquitetura
===========================================================

Script para gerar diagrama da arquitetura integrada usando Python.
Cria diagramas profissionais para documentação do projeto.

Uso:
    python create_architecture_diagram.py

Requer: matplotlib, networkx, plotly
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, ConnectionPatch
import numpy as np
from datetime import datetime
import json

# ===========================================
# CONFIGURAÇÕES DO DIAGRAMA
# ===========================================

DIAGRAM_CONFIG = {
    'width': 16,
    'height': 12,
    'dpi': 300,
    'colors': {
        'iot': '#3498db',           # Azul - ESP32/IoT
        'communication': '#e74c3c', # Vermelho - MQTT/HTTP
        'processing': '#f39c12',    # Laranja - ETL/ML
        'storage': '#27ae60',       # Verde - Database
        'interface': '#9b59b6',     # Roxo - Dashboard
        'arrow': '#34495e',         # Cinza escuro - Setas
        'text': '#2c3e50',         # Azul escuro - Texto
        'background': '#ecf0f1'     # Cinza claro - Fundo
    },
    'fonts': {
        'title': 16,
        'component': 12,
        'description': 10,
        'small': 8
    }
}

# ===========================================
# CLASSE PARA CRIAR DIAGRAMAS
# ===========================================

class SmartMaintenanceArchitectureDiagram:
    """Gerador de diagramas de arquitetura"""
    
    def __init__(self):
        self.fig, self.ax = plt.subplots(
            figsize=(DIAGRAM_CONFIG['width'], DIAGRAM_CONFIG['height']),
            dpi=DIAGRAM_CONFIG['dpi']
        )
        self.colors = DIAGRAM_CONFIG['colors']
        self.fonts = DIAGRAM_CONFIG['fonts']
        
        # Configurar plot
        self.ax.set_xlim(0, 10)
        self.ax.set_ylim(0, 10)
        self.ax.set_aspect('equal')
        self.ax.axis('off')
        
        # Fundo
        self.ax.add_patch(patches.Rectangle(
            (0, 0), 10, 10,
            facecolor=self.colors['background'],
            alpha=0.3
        ))
    
    def add_component_box(self, x, y, width, height, title, description, color, icon=""):
        """Adicionar caixa de componente"""
        
        # Caixa principal
        box = FancyBboxPatch(
            (x, y), width, height,
            boxstyle="round,pad=0.1",
            facecolor=color,
            edgecolor='white',
            linewidth=2,
            alpha=0.8
        )
        self.ax.add_patch(box)
        
        # Título
        self.ax.text(
            x + width/2, y + height - 0.3,
            f"{icon} {title}",
            ha='center', va='center',
            fontsize=self.fonts['component'],
            fontweight='bold',
            color='white'
        )
        
        # Descrição
        self.ax.text(
            x + width/2, y + height/2 - 0.2,
            description,
            ha='center', va='center',
            fontsize=self.fonts['description'],
            color='white',
            wrap=True
        )
    
    def add_arrow(self, x1, y1, x2, y2, label="", curved=False):
        """Adicionar seta entre componentes"""
        
        if curved:
            # Seta curva
            arrow = patches.FancyArrowPatch(
                (x1, y1), (x2, y2),
                connectionstyle="arc3,rad=0.3",
                arrowstyle='->,head_width=0.3,head_length=0.5',
                color=self.colors['arrow'],
                linewidth=2,
                alpha=0.8
            )
        else:
            # Seta reta
            arrow = patches.FancyArrowPatch(
                (x1, y1), (x2, y2),
                arrowstyle='->,head_width=0.3,head_length=0.5',
                color=self.colors['arrow'],
                linewidth=2,
                alpha=0.8
            )
        
        self.ax.add_patch(arrow)
        
        # Label da seta
        if label:
            mid_x, mid_y = (x1 + x2) / 2, (y1 + y2) / 2
            
            # Fundo branco para o label
            self.ax.text(
                mid_x, mid_y + 0.2,
                label,
                ha='center', va='center',
                fontsize=self.fonts['small'],
                bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8),
                color=self.colors['text']
            )
    
    def add_data_flow_info(self, x, y, data_format, frequency):
        """Adicionar informações de fluxo de dados"""
        info_text = f"Formato: {data_format}\nFrequência: {frequency}"
        
        self.ax.text(
            x, y,
            info_text,
            ha='center', va='center',
            fontsize=self.fonts['small'],
            bbox=dict(
                boxstyle="round,pad=0.4",
                facecolor='yellow',
                alpha=0.7,
                edgecolor=self.colors['text']
            ),
            color=self.colors['text']
        )
    
    def create_main_architecture_diagram(self):
        """Criar diagrama principal da arquitetura"""
        
        # Título principal
        self.ax.text(
            5, 9.5,
            "Smart Maintenance SaaS - Arquitetura Integrada",
            ha='center', va='center',
            fontsize=self.fonts['title'],
            fontweight='bold',
            color=self.colors['text']
        )
        
        # Subtítulo
        self.ax.text(
            5, 9.1,
            "Pipeline Completo: IoT → MQTT → Database → ML → Dashboard",
            ha='center', va='center',
            fontsize=self.fonts['description'],
            color=self.colors['text']
        )
        
        # ========================================
        # LAYER 1: IoT DEVICES (ESP32 + Sensores)
        # ========================================
        
        self.add_component_box(
            0.5, 7, 2, 1.5,
            "ESP32 + Sensores",
            "MPU6050 (Temp, Accel, Gyro)\nDHT22 (Temp, Humid)\nPressure Sensor\n@1Hz Sampling",
            self.colors['iot'],
            "🔧"
        )
        
        # ========================================
        # LAYER 2: COMMUNICATION (MQTT)
        # ========================================
        
        self.add_component_box(
            3.5, 7, 2, 1.5,
            "MQTT Broker",
            "Message Queue\nJSON Payload\nTopic: hermes/sensors\nQoS: 1",
            self.colors['communication'],
            "📡"
        )
        
        # Seta ESP32 → MQTT
        self.add_arrow(2.5, 7.75, 3.5, 7.75, "WiFi/JSON")
        self.add_data_flow_info(3, 8.2, "JSON", "1Hz")
        
        # ========================================
        # LAYER 3: DATA INGESTION
        # ========================================
        
        self.add_component_box(
            6.5, 7, 2.5, 1.5,
            "Data Ingestion Service",
            "Python MQTT Client\nData Validation\nBatch Processing\nBuffer Management",
            self.colors['processing'],
            "⚡"
        )
        
        # Seta MQTT → Ingestion
        self.add_arrow(5.5, 7.75, 6.5, 7.75, "Subscribe")
        self.add_data_flow_info(6, 8.2, "JSON", "Real-time")
        
        # ========================================
        # LAYER 4: DATABASE (ORACLE)
        # ========================================
        
        self.add_component_box(
            7.5, 4.5, 2, 1.8,
            "Oracle Database",
            "T_EQUIPAMENTO\nT_SENSOR\nT_MEDICAO\n3NF Normalized",
            self.colors['storage'],
            "🗄️"
        )
        
        # Seta Ingestion → Database
        self.add_arrow(7.75, 7, 8.5, 6.3, "SQL INSERT", curved=True)
        self.add_data_flow_info(8.8, 6.8, "SQL", "Batch")
        
        # ========================================
        # LAYER 5: ETL PIPELINE
        # ========================================
        
        self.add_component_box(
            4.5, 4.5, 2.5, 1.8,
            "ETL Pipeline",
            "Extract & Transform\nData Quality Checks\nFeature Engineering\nAggregations",
            self.colors['processing'],
            "🔄"
        )
        
        # Seta Database ↔ ETL (bidirectional)
        self.add_arrow(7.5, 5.4, 7, 5.4, "SELECT")
        self.add_arrow(7, 5.1, 7.5, 5.1, "LOAD")
        
        # ========================================
        # LAYER 6: ML PIPELINE
        # ========================================
        
        self.add_component_box(
            1.5, 4.5, 2.5, 1.8,
            "ML Pipeline",
            "KNN, Random Forest\nLogistic Regression\nModel Training\nPrediction API",
            self.colors['processing'],
            "🤖"
        )
        
        # Seta ETL → ML
        self.add_arrow(4.5, 5.4, 4, 5.4, "Features")
        
        # ========================================
        # LAYER 7: DASHBOARD & ALERTS
        # ========================================
        
        self.add_component_box(
            3, 1.5, 4, 2,
            "Dashboard & Alerts",
            "Streamlit Web App\nReal-time KPIs\nPlotly Charts\nAlert System\nEmail Notifications",
            self.colors['interface'],
            "📊"
        )
        
        # Setas para Dashboard
        self.add_arrow(2.5, 4.5, 4, 3.5, "ML Results", curved=True)
        self.add_arrow(5.75, 4.5, 5.5, 3.5, "ETL Data", curved=True)
        self.add_arrow(7.5, 4.5, 6.5, 3.5, "Raw Data", curved=True)
        
        # ========================================
        # INFORMAÇÕES ADICIONAIS
        # ========================================
        
        # Legenda de tecnologias
        tech_info = [
            "🔧 Hardware: ESP32, MPU6050, DHT22",
            "📡 Communication: MQTT (Eclipse Mosquitto)",
            "🗄️ Database: Oracle 11g (3NF)",
            "⚡ Processing: Python, Pandas, NumPy",
            "🤖 ML: Scikit-learn, KNN, Random Forest",
            "📊 Frontend: Streamlit, Plotly"
        ]
        
        for i, info in enumerate(tech_info):
            self.ax.text(
                0.2, 0.5 - i*0.2,
                info,
                ha='left', va='center',
                fontsize=self.fonts['small'],
                color=self.colors['text']
            )
        
        # Performance metrics
        perf_info = [
            "📈 Performance Metrics:",
            "• Throughput: 1,000 records/min",
            "• Latency: < 5 seconds end-to-end",
            "• ML Accuracy: 94.56%",
            "• System Uptime: 99.2%"
        ]
        
        for i, info in enumerate(perf_info):
            self.ax.text(
                0.2, 3.5 - i*0.2,
                info,
                ha='left', va='center',
                fontsize=self.fonts['small'],
                color=self.colors['text'],
                weight='bold' if i == 0 else 'normal'
            )
        
        # Data flow summary
        flow_summary = [
            "🔄 Data Flow Summary:",
            "1. ESP32 → MQTT (JSON, 1Hz)",
            "2. MQTT → Python Service (Real-time)", 
            "3. Service → Oracle DB (Batch)",
            "4. ETL → Feature Engineering (1min)",
            "5. ML → Predictions (On-demand)",
            "6. Dashboard → Visualization (<5s)"
        ]
        
        for i, info in enumerate(flow_summary):
            self.ax.text(
                0.2, 2.5 - i*0.15,
                info,
                ha='left', va='center',
                fontsize=self.fonts['small'],
                color=self.colors['text'],
                weight='bold' if i == 0 else 'normal'
            )
    
    def add_timestamp_and_credits(self):
        """Adicionar timestamp e créditos"""
        
        # Timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.ax.text(
            9.8, 0.2,
            f"Generated: {timestamp}",
            ha='right', va='bottom',
            fontsize=self.fonts['small'] - 1,
            color=self.colors['text'],
            alpha=0.7
        )
        
        # Credits
        self.ax.text(
            9.8, 0.05,
            "Challenge Hermes Reply - FIAP",
            ha='right', va='bottom',
            fontsize=self.fonts['small'],
            fontweight='bold',
            color=self.colors['text']
        )
    
    def save_diagram(self, filename="smart_maintenance_architecture.png"):
        """Salvar diagrama"""
        plt.tight_layout()
        plt.savefig(
            filename,
            dpi=DIAGRAM_CONFIG['dpi'],
            bbox_inches='tight',
            facecolor='white',
            edgecolor='none'
        )
        print(f"Diagrama salvo como: {filename}")

# ===========================================
# FUNÇÃO PARA CRIAR DIAGRAMA DETALHADO
# ===========================================

def create_detailed_component_diagram():
    """Criar diagrama detalhado dos componentes"""
    
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(
        2, 2, figsize=(16, 12), dpi=300
    )
    
    colors = DIAGRAM_CONFIG['colors']
    
    # ========================================
    # QUADRANTE 1: ESP32 & SENSORES
    # ========================================
    
    ax1.set_title("ESP32 & Sensor Integration", fontweight='bold', fontsize=14)
    ax1.set_xlim(0, 10)
    ax1.set_ylim(0, 10)
    ax1.axis('off')
    
    # ESP32 Core
    esp32_box = FancyBboxPatch(
        (2, 6), 6, 2,
        boxstyle="round,pad=0.2",
        facecolor=colors['iot'],
        edgecolor='white',
        linewidth=2,
        alpha=0.8
    )
    ax1.add_patch(esp32_box)
    ax1.text(5, 7, "ESP32 Controller\nWiFi + MQTT Client", 
             ha='center', va='center', fontsize=12, color='white', fontweight='bold')
    
    # Sensores
    sensors = [
        (1, 3, "MPU6050\nTemp+Gyro+Accel"),
        (4, 3, "DHT22\nTemp+Humidity"),
        (7, 3, "Pressure\nAnalog Sensor")
    ]
    
    for x, y, label in sensors:
        sensor_box = FancyBboxPatch(
            (x, y), 2, 1.5,
            boxstyle="round,pad=0.1",
            facecolor=colors['communication'],
            alpha=0.7
        )
        ax1.add_patch(sensor_box)
        ax1.text(x+1, y+0.75, label, ha='center', va='center', 
                fontsize=10, color='white', fontweight='bold')
        
        # Conexões
        ax1.arrow(x+1, y+1.5, 0, 1, head_width=0.2, head_length=0.2, 
                 fc=colors['arrow'], ec=colors['arrow'])
    
    # ========================================
    # QUADRANTE 2: BANCO DE DADOS
    # ========================================
    
    ax2.set_title("Database Schema (Oracle)", fontweight='bold', fontsize=14)
    ax2.set_xlim(0, 10)
    ax2.set_ylim(0, 10)
    ax2.axis('off')
    
    # Tabelas
    tables = [
        (1, 7, "T_EQUIPAMENTO\nPK: id_maquina\ntipo_maquina\nlocalizacao"),
        (5.5, 7, "T_SENSOR\nPK: id_sensor\ntipo_sensor\nunidade_medida"),
        (3, 3, "T_MEDICAO\nPK: id_medicao\nFK: id_maquina, id_sensor\nvl_temperatura\nvl_pressao\nvl_vibracao\nvl_humidade\ndataHora_medicao\nflag_falha")
    ]
    
    for x, y, label in tables:
        width = 3 if "T_MEDICAO" in label else 2.5
        height = 2.5 if "T_MEDICAO" in label else 2
        
        table_box = FancyBboxPatch(
            (x, y), width, height,
            boxstyle="round,pad=0.1",
            facecolor=colors['storage'],
            alpha=0.8
        )
        ax2.add_patch(table_box)
        ax2.text(x+width/2, y+height/2, label, ha='center', va='center', 
                fontsize=9, color='white', fontweight='bold')
    
    # Relacionamentos
    ax2.arrow(2.5, 7, 1, -1, head_width=0.15, head_length=0.15, 
             fc=colors['arrow'], ec=colors['arrow'], linestyle='--')
    ax2.arrow(5.5, 7, -1, -1, head_width=0.15, head_length=0.15, 
             fc=colors['arrow'], ec=colors['arrow'], linestyle='--')
    
    # ========================================
    # QUADRANTE 3: ML PIPELINE
    # ========================================
    
    ax3.set_title("ML Pipeline Components", fontweight='bold', fontsize=14)
    ax3.set_xlim(0, 10)
    ax3.set_ylim(0, 10)
    ax3.axis('off')
    
    # Pipeline steps
    ml_steps = [
        (1, 8, "Data\nExtraction", colors['processing']),
        (4, 8, "Feature\nEngineering", colors['processing']),
        (7, 8, "Model\nTraining", colors['processing']),
        (1, 5, "KNN\nClassifier", colors['iot']),
        (4, 5, "Random\nForest", colors['iot']),
        (7, 5, "Logistic\nRegression", colors['iot']),
        (4, 2, "Prediction\nAPI", colors['interface'])
    ]
    
    for x, y, label, color in ml_steps:
        step_box = FancyBboxPatch(
            (x, y), 2, 1.5,
            boxstyle="round,pad=0.1",
            facecolor=color,
            alpha=0.8
        )
        ax3.add_patch(step_box)
        ax3.text(x+1, y+0.75, label, ha='center', va='center', 
                fontsize=10, color='white', fontweight='bold')
    
    # Flow arrows
    ax3.arrow(2.5, 8.75, 1, 0, head_width=0.1, head_length=0.2, fc=colors['arrow'], ec=colors['arrow'])
    ax3.arrow(5.5, 8.75, 1, 0, head_width=0.1, head_length=0.2, fc=colors['arrow'], ec=colors['arrow'])
    
    # ========================================
    # QUADRANTE 4: DASHBOARD INTERFACE
    # ========================================
    
    ax4.set_title("Dashboard Components", fontweight='bold', fontsize=14)
    ax4.set_xlim(0, 10)
    ax4.set_ylim(0, 10)
    ax4.axis('off')
    
    # Dashboard elements
    dashboard_elements = [
        (1, 8, "KPIs\nCards", "Temperature\nPressure\nAlerts"),
        (5.5, 8, "Real-time\nCharts", "Time Series\nDistributions\nHeatmaps"),
        (1, 5, "Alert\nSystem", "Thresholds\nML Predictions\nNotifications"),
        (5.5, 5, "Equipment\nDetails", "Individual\nMachine Status\nHistory"),
        (3, 2, "Reports\n& Export", "PDF Reports\nCSV Export\nScheduled Reports")
    ]
    
    for x, y, title, description in dashboard_elements:
        element_box = FancyBboxPatch(
            (x, y), 3, 2,
            boxstyle="round,pad=0.1",
            facecolor=colors['interface'],
            alpha=0.8
        )
        ax4.add_patch(element_box)
        ax4.text(x+1.5, y+1.3, title, ha='center', va='center', 
                fontsize=11, color='white', fontweight='bold')
        ax4.text(x+1.5, y+0.7, description, ha='center', va='center', 
                fontsize=9, color='white')
    
    plt.tight_layout()
    plt.savefig("smart_maintenance_detailed_components.png", 
                dpi=300, bbox_inches='tight', facecolor='white')
    print("Diagrama detalhado salvo como: smart_maintenance_detailed_components.png")

# ===========================================
# EXECUÇÃO PRINCIPAL
# ===========================================

def main():
    """Função principal"""
    
    print("=== Smart Maintenance SaaS - Architecture Diagram Generator ===")
    print()
    
    # Diagrama principal
    print("Criando diagrama principal da arquitetura...")
    diagram = SmartMaintenanceArchitectureDiagram()
    diagram.create_main_architecture_diagram()
    diagram.add_timestamp_and_credits()
    diagram.save_diagram("smart_maintenance_architecture.png")
    
    print()
    
    # Diagrama detalhado
    print("Criando diagrama detalhado dos componentes...")
    create_detailed_component_diagram()
    
    print()
    print("✅ Diagramas criados com sucesso!")
    print("📁 Arquivos gerados:")
    print("   • smart_maintenance_architecture.png")
    print("   • smart_maintenance_detailed_components.png")
    print()
    print("ℹ️  Use estes diagramas na documentação do projeto")

if __name__ == "__main__":
    main()
