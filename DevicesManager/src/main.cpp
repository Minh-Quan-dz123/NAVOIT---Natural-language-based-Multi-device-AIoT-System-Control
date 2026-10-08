#include <Arduino.h>

#include "WiFiManager.h"
#include "WiFiMonitor.h"
#include "HTTPServer.h"
#include "DeviceManager.h"
#include "MQTTManager.h"

void setup() 
{
  Serial.begin(115200);
  // Khởi tạo WiFi Manager Task
  WiFiManager::begin();

  // Khởi tạo WiFi Monitor Task
  WiFiMonitor::begin();

  // Khởi tạo HTTP Server Task
  HTTPServer::begin();

  // khởi tạo Device
  DeviceManager::begin();

  // khởi tạo MQTT Manager
  MQTTManager::begin();

}

void loop() 
{
  vTaskDelay(pdMS_TO_TICKS(1000));
}

