#include "WiFiMonitor.h"
#include "WiFiManager.h"

#include <WiFi.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>

namespace
{
    TaskHandle_t monitorTaskHandle = nullptr;
    // RSSI thấp hơn giá trị này được xem là tín hiệu yếu.
    //
    // Ví dụ:
    // -50  : rất tốt
    // -60  : tốt
    // -70  : trung bình
    // -80  : yếu
    int32_t rssiThreshold = -72; // mặc định
    
    // khởi tạo các biến kiểm tra rssi mỗi 5 giây
    constexpr uint32_t MONITOR_INTERVAL_MS = 5000;
    constexpr uint16_t TASK_STACK_SIZE = 8192;
    constexpr UBaseType_t TASK_PRIORITY = 2;
    
    uint32_t lastRecoveryTime = 0;
    constexpr uint32_t RECOVERY_COOLDOWN_MS = 30000;
    void monitorTask(void *parameter);
    void recoverWiFi();

    // hàm monitor
    void monitorTask(void *parameter)
    {
        // Theo dõi RSSI WiFi hiện tại
        while(true)
        {
            // kiểm tra có đang connect hay ko
            bool connected = WiFiManager::isConnected();
            if(!connected)
            {
                // nếu ko thì gọi recoverWiFi để tìm kiếm wifi khác để kết nối
                Serial.println("[WiFiMonitor] WiFi disconnected");
                recoverWiFi();
            }
            
            // nếu vẫn đang kết nối thì check xem wifi này có quá yếu ko
            else
            {
                int32_t rssi = WiFiManager::getRSSI();
                Serial.print("[WiFiMonitor] RSSI: ");
                Serial.println(rssi);

                // RSSI quá yếu thì cx tìm kiếm wifi khác
                // ------------------------------------------------
                if (rssi < rssiThreshold)
                {
                    Serial.println("[WiFiMonitor] RSSI too weak");
                    recoverWiFi();
                }
            }
            vTaskDelay(pdMS_TO_TICKS(MONITOR_INTERVAL_MS));
        }
    }

    void recoverWiFi()
    {
        // cách mỗi 30 giây thì yêu cầu scan wifi 1 lần
        if(millis() - lastRecoveryTime < RECOVERY_COOLDOWN_MS)
        {
            return;
        }

        lastRecoveryTime = millis();
        Serial.println("[WiFiMonitor] Starting recovery scan");

        WiFiManager::requestScan(); // gửi yêu cầu và đợi khoảng 5 giây
        vTaskDelay(pdMS_TO_TICKS(5000));

        int bestIndex = -1;
        int32_t bestRSSI = -127;
        int savedCount = WiFiManager::getSavedCount();
        int scanCount = WiFiManager::getScanCount();

        // so sánh từng scannedWiFi xem đã từng lưu trong saved wifi ko, nếu có thì kết nối thử
        // cũng may sau khi scan xong thì các wifi đã được sắp xếp rồi
        for(int i = 0; i<scanCount; i++)
        {
            ScannedWiFi scanned = WiFiManager::getScanResult(i);
            for(int j = 0; j < savedCount; j++)
            {
                SavedWiFi saved = WiFiManager::getSavedWiFi(j);

                // so sánh BSSID trước, nếu BSSID ko có thì so sánh SSID
                bool matched = false;
                if (!saved.bssid.isEmpty() && !scanned.bssid.isEmpty())
                {
                    matched = saved.bssid.equalsIgnoreCase(scanned.bssid);
                }
                if(!matched)// nếu khác bssid hoặc ko có bssid để so sánh thì so sánh ssid
                {
                    matched = (saved.ssid == scanned.ssid);
                }
                // nếu khớp ssid thì lưu rssi mạnh hơn lại
                if(matched && (scanned.rssi > bestRSSI))
                {
                    bestRSSI = scanned.rssi;
                    bestIndex = j;
                }

            }
        }

        // ko tìm thấy wifi đã lưu
        if(bestIndex < 0)
        {
            Serial.println("[WiFiMonitor] No saved WiFi found");
            return;
        }

        // nhưng nếu tìm lấy wifi trùng với wifi đã lưu, và wifi trùng này là mạnh nhất
        SavedWiFi selected = WiFiManager::getSavedWiFi(bestIndex);
        Serial.println("[WiFiMonitor] Reconnecting:");
        Serial.print("SSID: ");
        Serial.println(selected.ssid);
        Serial.print("RSSI: ");
        Serial.println(bestRSSI);

        // Gửi yêu cầu CONNECT cho WiFi Manager.
        // --------------------------------------------------------
        WiFiManager::requestConnect(selected.ssid, selected.password, selected.bssid);
    }
}

void WiFiMonitor::begin()
{
    xTaskCreatePinnedToCore(
        monitorTask,
        "WiFiMonitorTask",
        TASK_STACK_SIZE,
        nullptr,
        TASK_PRIORITY,
        &monitorTaskHandle,
        1);

    Serial.println("[WiFiMonitor] Started");
}



//Hai hàm này dùng để đặt và lấy ngưỡng RSSI.
void WiFiMonitor::setRSSIThreshold(int32_t threshold)
{
    rssiThreshold = threshold;
}

int32_t WiFiMonitor::getRSSIThreshold()
{
    return rssiThreshold;
}