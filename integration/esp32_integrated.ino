/*
 * ESP32 Integrated Sensor System - Smart Maintenance SaaS
 * 
 * Componentes:
 * - MPU6050: Temperatura, Acelerometro, Giroscopio  
 * - DHT22: Temperatura e Humidade (sensor adicional)
 * - Sensor simulado de pressão (via ADC)
 * 
 * Comunicação: WiFi + MQTT
 * Frequência: 1 leitura por segundo
 */

#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <Wire.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <DHT.h>
#include <vector>

// ===========================================
// CONFIGURAÇÕES DE REDE E MQTT
// ===========================================
const char* WIFI_SSID = "SEU_WIFI";
const char* WIFI_PASSWORD = "SUA_SENHA";
const char* MQTT_SERVER = "broker.emqx.io";  // Broker público para testes
const int MQTT_PORT = 1883;
const char* MQTT_TOPIC = "hermes/sensors/data";
const char* DEVICE_ID = "ESP32_HERMES_001";

// ===========================================
// CONFIGURAÇÕES DE HARDWARE
// ===========================================
#define DHT_PIN 2
#define DHT_TYPE DHT22
#define PRESSURE_ANALOG_PIN A0
#define LED_STATUS_PIN 2

// ===========================================
// OBJETOS E VARIÁVEIS GLOBAIS
// ===========================================
WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);
Adafruit_MPU6050 mpu;
DHT dht(DHT_PIN, DHT_TYPE);

// Controle de tempo
unsigned long lastSensorRead = 0;
unsigned long lastMqttPublish = 0;
const unsigned long SENSOR_INTERVAL = 1000;  // 1 segundo
const unsigned long MQTT_INTERVAL = 5000;    // 5 segundos (para não sobrecarregar)

// Dados simulados para demonstração
std::vector<float> mockTemperatures = {
  25.0, 32.2, 35.1, 37.3, 39.0, 40.4, 41.6, 42.7, 43.7, 44.6,
  45.4, 46.2, 46.9, 47.6, 48.2, 48.8, 49.4, 50.0, 50.5, 51.0,
  51.5, 52.0, 52.4, 52.9, 53.3, 53.7, 54.1, 54.5, 54.9, 55.3,
  75.5, 78.2, 82.1, 85.6, 89.3, 92.7, 95.1, 97.8, 99.5, 100.2  // Simula falha
};
unsigned int mockIndex = 0;

// Estrutura para dados dos sensores
struct SensorData {
  float temperature_mpu;
  float temperature_dht;
  float humidity;
  float pressure;
  float vibration_x;
  float vibration_y;  
  float vibration_z;
  float gyro_x;
  float gyro_y;
  float gyro_z;
  unsigned long timestamp;
  bool has_fault;
};

SensorData currentData;
std::vector<SensorData> dataBuffer;

// ===========================================
// SETUP INICIAL
// ===========================================
void setup() {
  Serial.begin(115200);
  pinMode(LED_STATUS_PIN, OUTPUT);
  
  Serial.println("\n=== ESP32 Smart Maintenance System ===");
  Serial.println("Inicializando sensores e conectividade...");
  
  // Inicializar sensores
  if (!initializeSensors()) {
    Serial.println("ERRO: Falha na inicialização dos sensores!");
    while(1) {
      digitalWrite(LED_STATUS_PIN, HIGH);
      delay(200);
      digitalWrite(LED_STATUS_PIN, LOW);
      delay(200);
    }
  }
  
  // Conectar WiFi
  connectWiFi();
  
  // Configurar MQTT
  mqttClient.setServer(MQTT_SERVER, MQTT_PORT);
  mqttClient.setCallback(mqttCallback);
  connectMQTT();
  
  Serial.println("Sistema inicializado com sucesso!");
  Serial.println("Formato de saída: Timestamp | Temp_MPU | Temp_DHT | Humid | Press | Vibr_XYZ | Status");
  
  digitalWrite(LED_STATUS_PIN, HIGH);  // LED ligado = sistema OK
}

// ===========================================
// LOOP PRINCIPAL
// ===========================================
void loop() {
  unsigned long now = millis();
  
  // Manter conexões ativas
  if (!mqttClient.connected()) {
    connectMQTT();
  }
  mqttClient.loop();
  
  // Leitura dos sensores (1Hz)
  if (now - lastSensorRead >= SENSOR_INTERVAL) {
    lastSensorRead = now;
    readAllSensors();
    displaySensorData();
    dataBuffer.push_back(currentData);
    
    // Manter buffer de até 100 amostras
    if (dataBuffer.size() > 100) {
      dataBuffer.erase(dataBuffer.begin());
    }
  }
  
  // Publicação MQTT (0.2Hz para não sobrecarregar)
  if (now - lastMqttPublish >= MQTT_INTERVAL) {
    lastMqttPublish = now;
    publishSensorData();
  }
  
  // Verificar alertas críticos
  checkCriticalAlerts();
}

// ===========================================
// FUNÇÕES DE INICIALIZAÇÃO
// ===========================================
bool initializeSensors() {
  bool success = true;
  
  // Inicializar MPU6050
  if (!mpu.begin()) {
    Serial.println("AVISO: MPU6050 não encontrado - usando dados simulados");
    success = false;  // Não falha totalmente, usa simulação
  } else {
    Serial.println("MPU6050 inicializado com sucesso");
    mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
    mpu.setGyroRange(MPU6050_RANGE_500_DEG);
    mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);
  }
  
  // Inicializar DHT22
  dht.begin();
  Serial.println("DHT22 inicializado");
  
  // Configurar ADC para sensor de pressão simulado
  analogReadResolution(12);  // 12-bit ADC
  Serial.println("Sensor de pressão (simulado) configurado");
  
  return true;  // Sempre retorna true para permitir simulação
}

void connectWiFi() {
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Conectando ao WiFi");
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println();
    Serial.println("WiFi conectado!");
    Serial.print("IP: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\nFalha na conexão WiFi - continuando sem conectividade");
  }
}

void connectMQTT() {
  if (WiFi.status() != WL_CONNECTED) return;
  
  while (!mqttClient.connected()) {
    Serial.print("Conectando ao MQTT...");
    
    if (mqttClient.connect(DEVICE_ID)) {
      Serial.println(" conectado!");
      mqttClient.subscribe("hermes/commands");
    } else {
      Serial.print(" falha, rc=");
      Serial.print(mqttClient.state());
      Serial.println(" tentando novamente em 5s");
      delay(5000);
    }
  }
}

// ===========================================
// LEITURA DE SENSORES
// ===========================================
void readAllSensors() {
  currentData.timestamp = millis();
  
  // Ler MPU6050 (temperatura, aceleração, giroscópio)
  bool mpuSuccess = readMPU6050();
  
  // Ler DHT22 (temperatura e humidade)
  readDHT22();
  
  // Ler pressão simulada
  readPressureSensor();
  
  // Detectar possíveis falhas baseado em thresholds
  detectFaults();
}

bool readMPU6050() {
  sensors_event_t accel, gyro, temp;
  
  if (mpu.getEvent(&accel, &gyro, &temp)) {
    currentData.temperature_mpu = temp.temperature;
    currentData.vibration_x = accel.acceleration.x;
    currentData.vibration_y = accel.acceleration.y;
    currentData.vibration_z = accel.acceleration.z;
    currentData.gyro_x = gyro.gyro.x;
    currentData.gyro_y = gyro.gyro.y;
    currentData.gyro_z = gyro.gyro.z;
    return true;
  } else {
    // Usar dados simulados se sensor não disponível
    if (mockIndex < mockTemperatures.size()) {
      currentData.temperature_mpu = mockTemperatures[mockIndex];
      mockIndex++;
    } else {
      mockIndex = 0;
      currentData.temperature_mpu = mockTemperatures[0];
    }
    
    // Simular vibrações
    currentData.vibration_x = random(-20, 20) / 10.0;
    currentData.vibration_y = random(-20, 20) / 10.0;
    currentData.vibration_z = random(80, 120) / 10.0;  // Componente Z mais estável
    
    return false;
  }
}

void readDHT22() {
  float h = dht.readHumidity();
  float t = dht.readTemperature();
  
  if (!isnan(h) && !isnan(t)) {
    currentData.humidity = h;
    currentData.temperature_dht = t;
  } else {
    // Valores simulados se sensor não disponível
    currentData.humidity = 45.0 + random(-10, 10);
    currentData.temperature_dht = currentData.temperature_mpu + random(-2, 3);
  }
}

void readPressureSensor() {
  // Simular sensor de pressão via ADC
  int adcValue = analogRead(PRESSURE_ANALOG_PIN);
  
  // Converter para pressão (simulated range: 950-1050 hPa)
  currentData.pressure = 950.0 + (adcValue / 4095.0) * 100.0;
  
  // Adicionar ruído e variação
  currentData.pressure += random(-5, 5) / 10.0;
}

void detectFaults() {
  bool fault = false;
  
  // Thresholds críticos
  if (currentData.temperature_mpu > 95.0) fault = true;
  if (currentData.humidity > 80.0) fault = true;  
  if (currentData.pressure < 960.0 || currentData.pressure > 1040.0) fault = true;
  if (abs(currentData.vibration_x) > 15.0) fault = true;
  if (abs(currentData.vibration_y) > 15.0) fault = true;
  
  currentData.has_fault = fault;
}

// ===========================================
// COMUNICAÇÃO E VISUALIZAÇÃO
// ===========================================
void displaySensorData() {
  Serial.print(currentData.timestamp);
  Serial.print(" | ");
  Serial.print(currentData.temperature_mpu, 2);
  Serial.print(" | ");
  Serial.print(currentData.temperature_dht, 2);
  Serial.print(" | ");
  Serial.print(currentData.humidity, 1);
  Serial.print(" | ");
  Serial.print(currentData.pressure, 2);
  Serial.print(" | ");
  Serial.print(currentData.vibration_x, 2);
  Serial.print(",");
  Serial.print(currentData.vibration_y, 2);
  Serial.print(",");
  Serial.print(currentData.vibration_z, 2);
  Serial.print(" | ");
  Serial.println(currentData.has_fault ? "ALERTA!" : "OK");
}

void publishSensorData() {
  if (!mqttClient.connected() || WiFi.status() != WL_CONNECTED) return;
  
  // Criar JSON payload
  StaticJsonDocument<512> doc;
  
  doc["device_id"] = DEVICE_ID;
  doc["timestamp"] = currentData.timestamp;
  doc["location"] = "Factory_A";
  doc["equipment_type"] = "Pump";
  
  JsonObject sensors = doc.createNestedObject("sensors");
  sensors["temperature"] = currentData.temperature_mpu;
  sensors["temperature_dht"] = currentData.temperature_dht;
  sensors["humidity"] = currentData.humidity;
  sensors["pressure"] = currentData.pressure;
  sensors["vibration_x"] = currentData.vibration_x;
  sensors["vibration_y"] = currentData.vibration_y;
  sensors["vibration_z"] = currentData.vibration_z;
  sensors["gyro_x"] = currentData.gyro_x;
  sensors["gyro_y"] = currentData.gyro_y;
  sensors["gyro_z"] = currentData.gyro_z;
  
  doc["fault_detected"] = currentData.has_fault;
  
  // Calcular estatísticas do buffer
  if (!dataBuffer.empty()) {
    doc["avg_temp_5min"] = calculateAverageTemp();
    doc["max_vibration_5min"] = calculateMaxVibration();
  }
  
  // Converter para string e publicar
  String jsonString;
  serializeJson(doc, jsonString);
  
  bool success = mqttClient.publish(MQTT_TOPIC, jsonString.c_str());
  
  if (success) {
    Serial.println("Dados enviados via MQTT: " + jsonString);
  } else {
    Serial.println("ERRO: Falha no envio MQTT");
  }
}

float calculateAverageTemp() {
  float sum = 0;
  for (const auto& data : dataBuffer) {
    sum += data.temperature_mpu;
  }
  return sum / dataBuffer.size();
}

float calculateMaxVibration() {
  float max_vibr = 0;
  for (const auto& data : dataBuffer) {
    float total_vibr = sqrt(data.vibration_x*data.vibration_x + 
                           data.vibration_y*data.vibration_y + 
                           data.vibration_z*data.vibration_z);
    if (total_vibr > max_vibr) {
      max_vibr = total_vibr;
    }
  }
  return max_vibr;
}

void checkCriticalAlerts() {
  if (currentData.has_fault) {
    // LED piscando para alertas
    static unsigned long lastBlink = 0;
    static bool ledState = false;
    
    if (millis() - lastBlink > 250) {
      ledState = !ledState;
      digitalWrite(LED_STATUS_PIN, ledState);
      lastBlink = millis();
    }
    
    // Log crítico a cada 30 segundos
    static unsigned long lastCriticalLog = 0;
    if (millis() - lastCriticalLog > 30000) {
      Serial.println("*** ALERTA CRÍTICO ATIVO ***");
      Serial.println("Temperatura: " + String(currentData.temperature_mpu) + "°C");
      Serial.println("Pressão: " + String(currentData.pressure) + " hPa");
      Serial.println("Vibração Total: " + String(calculateMaxVibration()));
      lastCriticalLog = millis();
    }
  } else {
    digitalWrite(LED_STATUS_PIN, HIGH);  // LED fixo quando OK
  }
}

// ===========================================
// CALLBACKS MQTT
// ===========================================
void mqttCallback(char* topic, byte* payload, unsigned int length) {
  String message;
  for (int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
  
  Serial.println("Comando MQTT recebido: " + message);
  
  // Implementar comandos básicos
  if (message == "reset_mock") {
    mockIndex = 0;
    Serial.println("Dados simulados reiniciados");
  } else if (message == "status") {
    Serial.println("Sistema operacional - " + String(dataBuffer.size()) + " amostras em buffer");
  }
}

// ===========================================
// FUNÇÕES DE EXPORTAÇÃO (CSV)
// ===========================================
void exportBufferToCSV() {
  Serial.println("\n=== EXPORT CSV BUFFER ===");
  Serial.println("timestamp,temp_mpu,temp_dht,humidity,pressure,vibr_x,vibr_y,vibr_z,fault");
  
  for (const auto& data : dataBuffer) {
    Serial.print(data.timestamp);
    Serial.print(",");
    Serial.print(data.temperature_mpu, 2);
    Serial.print(",");
    Serial.print(data.temperature_dht, 2);
    Serial.print(",");
    Serial.print(data.humidity, 1);
    Serial.print(",");
    Serial.print(data.pressure, 2);
    Serial.print(",");
    Serial.print(data.vibration_x, 2);
    Serial.print(",");
    Serial.print(data.vibration_y, 2);
    Serial.print(",");
    Serial.print(data.vibration_z, 2);
    Serial.print(",");
    Serial.println(data.has_fault ? 1 : 0);
  }
  
  Serial.println("=== FIM EXPORT CSV ===\n");
}
