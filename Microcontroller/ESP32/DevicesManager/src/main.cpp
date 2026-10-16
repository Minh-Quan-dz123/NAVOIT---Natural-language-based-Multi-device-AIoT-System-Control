#include <Arduino.h>
#include <time.h>

#include "WiFiManager.h"
#include "WiFiMonitor.h"
#include "HTTPServer.h"
#include "DeviceManager.h"
#include "MQTTManager.h"
#include "Timer.h"

// Hàm in thời gian hiện tại của hệ thống
void timeDebugTask(void *parameter)
{
    setenv("TZ", "ICT-7", 1);// đặt biến môi trường TZ thành múi giờ ICT (Indochina Time). Dấu -7 theo quy ước POSIX có nghĩa là UTC+7.
    tzset();  // êu cầu thư viện C cập nhật cấu hình múi giờ theo biến TZ vừa đặt.
    while (true)
    {
        if (Timer::isValid())
        {
            time_t now = Timer::getTime();

            struct tm timeInfo;
            localtime_r(&now, &timeInfo);

            Serial.printf(
                "[TIME] %04d-%02d-%02d %02d:%02d:%02d | Timestamp: %lld\n",
                timeInfo.tm_year + 1900,
                timeInfo.tm_mon + 1,
                timeInfo.tm_mday,
                timeInfo.tm_hour,
                timeInfo.tm_min,
                timeInfo.tm_sec,
                (long long)now
            );
        }
        else
        {
            Serial.println("[TIME] Waiting for MQTT time synchronization...");
        }

        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}


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

  // khởi tạo task in thời gian
  xTaskCreate(
        timeDebugTask,
        "TimeDebugTask",
        4096,
        nullptr,
        1,
        nullptr
    );

  delay(200);
  Serial.print("ESP32 MAC Address: ");
  Serial.println(WiFiManager::getMAC());

}

void loop() 
{
  vTaskDelay(pdMS_TO_TICKS(1000));
}

