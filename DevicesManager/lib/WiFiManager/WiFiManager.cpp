#include <Preferences.h>        // Dùng để lưu dữ liệu vào bộ nhớ flash của ESP32
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <freertos/queue.h>
#include <freertos/semphr.h>    // Dùng cho Semaphore và Mutex.

#include "WiFiManager.h"
namespace
{
    // 1. FressRTOS objects
    TaskHandle_t wifiManagerTaskHandle = nullptr;
    QueueHandle_t wifiCommandQueue = nullptr;
    SemaphoreHandle_t wifiDataMutex = nullptr;

    // 2. WiFi data
    WiFiConnectionState connectionState = WiFiConnectionState::DISCONNECTED;

    SavedWiFi savedWiFi[MAX_SAVED_WIFI];
    int savedWiFiCount = 0;

    ScannedWiFi scanResults[MAX_SCAN_WIFI];
    int scanResultCount = 0;

    bool connectResultAvailable = false;// biến này cho biết đã có kết quả kết nối wifi chưa
    bool lastConnectResult = false;     // biến này lưu kết quả của lần connect gần nhất
    volatile bool cancelRequested = false;  // biến này cho biết user có yêu cầu hủy kết nối ko, Được requestCancelConnect() và connectWiFi() truy cập

    Preferences preferences;

    // 3. AP configuration
    const char *AP_SSID = "ESP32_Config";
    const char *AP_PASSWORD = "12345678";

    // 4. Task Configuration
    // constexpr là giá trị hằng số tại thời điểm biên dịch
    constexpr uint32_t CONNECT_TIMEOUT_MS = 10000;
    constexpr uint16_t TASK_STACK_SIZE = 16384;
    constexpr UBaseType_t TASK_PRIORITY = 3; // UBaseType_t là kiểu số nguyên ko dấu cho FreeRTOS tự định nghĩa

    // 5. khai báo trc
    void wifiManagerTask(void *parameter);
    void initializeAP();    //khởi tạo ESP32 ở chế độ Access Point (AP).
    void loadSavedWiFi();   //dùng để đọc các WiFi đã lưu từ bộ nhớ Preferences của ESP32 vào RAM.
    void saveSavedWiFi();    //Ngược lại với loadSavedWiFi().
    void addSavedWiFi(const String &ssid, const String &password, const String &bssid);
    bool connectWiFi(const String &ssid, const String &password, const String &bssid);
    void disconnectWiFi();
    void scanWiFi();
    //void sortScanResults();
    String normalizeBSSID(const String &bssid); //Dùng để chuẩn hóa BSSID.


    // 7. AP - Access Point
    void initializeAP()
    {
        // ESP32 tạo AP để người dùng kết nối
        bool result = WiFi.softAP(AP_SSID, AP_PASSWORD);
        if(result)
        {
            Serial.println("[WiFiManager] 7. AP started");

            Serial.print("[WiFiManager] 7. AP SSID: ");
            Serial.println(AP_SSID);

            Serial.print("[WiFiManager] 7. AP IP: ");
            Serial.println(WiFi.softAPIP());
        }
        else Serial.println("[WiFiManager] 7. Failed to start AP");
    }

    // 8. LOAD SAVED WIFI
    void loadSavedWiFi()
    {
        // 8.1. khởi tạo preferences và đọc giá trị

        // 8.1.1. mở vùng lưu trữ có tên là "wifi", true => chỉ đọc
        preferences.begin("wifi", true);

        // 8.1.2. lấy count
        savedWiFiCount = preferences.getInt("count",0); // 0 tức là giá trị mặc định nếu ko tìm thấy count
        if(savedWiFiCount > MAX_SAVED_WIFI)
        {
            savedWiFiCount = MAX_SAVED_WIFI;
        }
        
        // 8.2. load list savedWiFi từ flash => ram
        // lưu bọn này với key-value, ví dụ [wifi0_ssid, ...]
        for(int i = 0; i<savedWiFiCount; i++)
        {
            String prefix = "wifi" + String(i);

            savedWiFi[i].ssid = preferences.getString((prefix+"_ssid").c_str(), "");
            savedWiFi[i].password = preferences.getString((prefix+"_pass").c_str(), "");
            savedWiFi[i].bssid = preferences.getString((prefix+"_bssid").c_str(), "");
        }

        // 8.3 lấy xong thì đóng lại
        preferences.end();
        Serial.printf("[WiFiManager] 8. Loaded %d savedWiFi\n",savedWiFiCount);
    }

    // 9. Save wifi to flash memory
    void saveSavedWiFi()
    {
        // 9.1. lưu count
        preferences.begin("wifi", false); // false = đọc/ghi
        preferences.putInt("count", savedWiFiCount);

        // 9.2. lưu list wifi
        for(int i = 0 ; i<MAX_SAVED_WIFI; i++)
        {
            String prefix = "wifi" + String(i);

            preferences.putString((prefix + "_ssid").c_str(), savedWiFi[i].ssid);
            preferences.putString((prefix + "_pass").c_str(), savedWiFi[i].password);
            preferences.putString((prefix + "_bssid").c_str(), savedWiFi[i].bssid);
        }
        preferences.end();
        Serial.printf("[WiFiManager] 9. Saved %d savedWiFi\n",savedWiFiCount);
    }

    // 10. thêm 1 wifi vào list wifi đã lưu, và đưa lên wifi đó lên đầu danh sách tối đa 5 wifi
    void addSavedWiFi(const String &ssid, const String &password, const String &bssid)
    {
        // 10.1. nếu ko có tên wifi thì ko lưu
        if(ssid.isEmpty()) return;
        String normalizedBSSID = normalizeBSSID(bssid); // aa:bb:cc:dd:ee:ff => AA:BB:CC:DD:EE:FF

        // 10.2. Nếu wifi đã tồn tại thì đưa nó lên đầu danh sách
        int existingIndex = -1;
        for(int i = 0; i < savedWiFiCount; i++)
        {
            if(savedWiFi[i].ssid == ssid)
            {
                existingIndex = i;
                break;
            }
        }

        // 10.3. nếu tồn tại ở index ví dụ = 3 => đưa lên đầu
        // ví dụ [0,1,2,3,4] => [3,0,1,2,4]
        if(existingIndex >= 0)
        {
            for(int i = existingIndex; i>0; i--) savedWiFi[i] = savedWiFi[i-1];
            savedWiFi[0] = {ssid, password, normalizedBSSID};
            saveSavedWiFi(); 

            Serial.println("[WiFiManager] 10.3. WiFi saved");
            return;
        }

        // 10.4. nếu wifi này chưa tồn tại thì xử lý như sau
        // nếu list chưa full 5 wifi , ví dụ [0,1,2]
        // thì dồn về cuối [new, 0,1,2]
        // nếu đã full [0,1,2,3,4] => [new,0,1,2,3]
        // 10.4.1. nếu list chưa full 5 wifi
        if(savedWiFiCount < MAX_SAVED_WIFI)
        {
            for(int i = savedWiFiCount; i>0; i--) savedWiFi[i] = savedWiFi[i-1];
            savedWiFi[0] = {ssid, password, normalizedBSSID};
            savedWiFiCount++;
        }
        // 10.4.2. nếu đã đủ 5 wifi
        else
        {
            for(int i = MAX_SAVED_WIFI-1; i>0;i--) savedWiFi[i] = savedWiFi[i-1];
            savedWiFi[0] = {ssid, password, normalizedBSSID};
        }
        saveSavedWiFi();
        Serial.println("[WiFiManager] 10.4. WiFi saved");
    }

    // 11. kết nối tới 1 wifi
    bool connectWiFi(const String &ssid, const String &password, const String &bssid)
    {
        Serial.println();
        Serial.println("[WiFiManager] 11. Starting connection");
        Serial.print("SSID: ");
        Serial.println(ssid);
        
        //11.1. đánh dấu trạng thái connecting
        connectionState = WiFiConnectionState::CONNECTING;
        connectResultAvailable = false; 
        cancelRequested = false;

        // 11.2. ngắt wifi hiện tại trước khi kết nối wifi mới
        WiFi.disconnect(false);
        vTaskDelay(pdMS_TO_TICKS(200));// đợi chút để nó tắt

        // 11.3. nếu có bssid thì dùng bssid, nếu ko thì dùng ssid + password
        if(!bssid.isEmpty())
        {
            // bssid = "AA:BB:CC:DD:EE:FF"
            uint8_t mac[6];
            if(sscanf(bssid.c_str(),
                    "%hhx:%hhx:%hhx:%hhx:%hhx:%hhx",
                    &mac[0],
                    &mac[1],
                    &mac[2],
                    &mac[3],
                    &mac[4],
                    &mac[5]) == 6)
            {
                WiFi.begin(ssid.c_str(), password.c_str(), 0, mac, true);
            }
            else WiFi.begin(ssid.c_str(), password.c_str());
        }
        else WiFi.begin(ssid.c_str(), password.c_str());

        // 11.4 chờ tối đa 10 giây
        uint32_t startTime = millis();
        while(millis() - startTime < CONNECT_TIMEOUT_MS)
        {
            // nếu trong lúc đợi mà user bấm cancel
            if(cancelRequested)
            {
                Serial.println("[WiFiManager] 11.4. Connection cancelled by user");
                WiFi.disconnect(false);
                connectionState = WiFiConnectionState::DISCONNECTED;
                connectResultAvailable = true;
                lastConnectResult = false;
                cancelRequested = false;
                return false;
            }
            // nếu ko bị bấm cancel và kết nối thành công
            if (WiFi.status() == WL_CONNECTED)
            {
                Serial.println("[WiFiManager] 11.4. Connected");

                Serial.print("SSID: ");
                Serial.println(WiFi.SSID());

                Serial.print("IP: ");
                Serial.println(WiFi.localIP());

                Serial.print("RSSI: ");
                Serial.println(WiFi.RSSI());

                addSavedWiFi(ssid, password, WiFi.BSSIDstr());
                connectionState = WiFiConnectionState::CONNECTED;
                connectResultAvailable = true;
                lastConnectResult = true;

                return true;
            }
            vTaskDelay(pdMS_TO_TICKS(100));
        }

        //11.5. sau 10 giây ko kết nối được => timeout
        Serial.println("[WiFiManager] Connection timeout");
        WiFi.disconnect(false);
        connectionState =WiFiConnectionState::FAILED;
        connectResultAvailable = true;
        lastConnectResult = false;

        return false;
    }

    // 12. ngắt kết nối
    void disconnectWiFi()
    {
        WiFi.disconnect(false);
        connectionState = WiFiConnectionState::DISCONNECTED;
        connectResultAvailable = false;
        Serial.println("[WiFiManager] 12. Disconnected");
    }

    //13. scan wifi
    void scanWiFi()
    {
        Serial.println("[WiFiManager] 13. Scanning WiFi...");
        int count = WiFi.scanNetworks(false, false);
        // tham số 1: có quét đồng bộ hay ko (false = quét đồng bộ)
        // tham số 2: có tìm các wifi ẩn ssid ko
        // 13.1. nếu ko scan được wifi nào
        if(count <= 0)
        {
            scanResultCount = 0;
            Serial.println("[WiFiManager] 13. No WiFi found");
            WiFi.scanDelete();
            return;
        }

        // 13.2. nếu có, chỉ lấy tối đa 5 mạng có rssi mạnh nhất
        int total = min(count, 20);
        struct TempWiFi // khai báo tạm 1 struct để sài để sort
        {
            String ssid;
            int32_t rssi;
            String bssid;
        };
        TempWiFi temp[20];
        for(int i = 0; i < total; i++)
        {
            temp[i].ssid = WiFi.SSID(i);
            temp[i].rssi = WiFi.RSSI(i);
            temp[i].bssid = WiFi.BSSIDstr(i);
            
            // print
            Serial.println("[WiFiManager] 13.2. Scanned WiFi");
            Serial.println("===== WiFi " + String(i) + " =====");
            Serial.println("SSID: " + temp[i].ssid);
            Serial.println("RSSI: " + String(temp[i].rssi) + " dBm");
            Serial.println("BSSID: " + temp[i].bssid);
        }
        // sort theo rssi -40 mạnh hơn -70
        for (int i = 0; i < total - 1; i++)
        {
            for (int j = i + 1; j < total; j++)
            {
                if (temp[j].rssi >
                    temp[i].rssi)
                {
                    TempWiFi tmp = temp[i];

                    temp[i] = temp[j];

                    temp[j] = tmp;
                }
            }
        }

        // 13.3. sort xong chọn
        scanResultCount = min(total, MAX_SCAN_WIFI);
        for(int i = 0 ; i<scanResultCount; i++)
        {
            scanResults[i].ssid =temp[i].ssid;
            scanResults[i].rssi = temp[i].rssi;
            scanResults[i].bssid = temp[i].bssid;

            Serial.println("[WiFiManager] 13.3. Sorted Scanned WiFi");
            Serial.println("===== WiFi " + String(i) + " =====");
            Serial.println("SSID: " +  scanResults[i].ssid);
            Serial.println("RSSI: " +  String(scanResults[i].rssi) + " dBm");
            Serial.println("BSSID: " + scanResults[i].bssid);
        }
        WiFi.scanDelete();
        Serial.printf( "[WiFiManager] Found %d WiFi\n", scanResultCount);

    }

    // 14. Task chính
    void wifiManagerTask(void *parameter)
    {
        WiFiCommand command;
        while(true)
        {
            // chờ command từ HTTP Server hoặc monitor
            // wifiCommandQueue: Queue cần lấy dữ liệu.
            // &command: nơi nhận dữ liệu lấy ra từ Queue.
            // portMAX_DELAY: chờ vô hạn nếu Queue đang rỗng.
            // xQueueReceive(...): lấy 1 phần tử khỏi Queue.
            // == pdTRUE: kiểm tra lấy thành công.
            if(xQueueReceive(wifiCommandQueue, &command, portMAX_DELAY) == pdTRUE)
            {
                switch (command.type)
                {
                    case WiFiCommandType::CONNECT:
                        connectWiFi(command.ssid, command.password, command.bssid);
                        break;
                    case WiFiCommandType::DISCONNECT:
                        disconnectWiFi();
                        break;
                    case WiFiCommandType::CANCEL_CONNECT: // ko cần thiết nhưng kệ cứ để vậy
                        cancelRequested = true;
                        break;
                    case WiFiCommandType::SCAN:
                        scanWiFi();
                        break;
                }
            }
        }
    }

    // 32 NORMALIZE BSSID
    String normalizeBSSID(const String &bssid)
    {
        String result = bssid;
        result.toUpperCase();
        return result;
    }


}

// ------------ I. các hàm ở mức thấp ---------------
// 6. begin
void WiFiManager::begin()
{   
    // 6.1. khởi tạo 1 queue chứa tối đa 10 phần tử, 1 phần tử có độ lớn = sizeof(WiFiCommand)
    wifiCommandQueue = xQueueCreate(10, sizeof(WiFiCommand));

    // 6.2. tạo 1 mutex
    wifiDataMutex = xSemaphoreCreateMutex();

    // => kiểm tra đã tạo được chưa
    if(wifiCommandQueue == nullptr || wifiDataMutex == nullptr)
    {
        Serial.println("[WiFiManager] ERROR: 6.1 or 6.2 FreeRTOS object creation failed");
        return;
    }

    // 6.3. đặt esp32 ở chế độ AP + STA
    WiFi.mode(WIFI_AP_STA);

    // 6.4. Tắt reconnect tự động của Arduino WiFi, việc reconnect cho WiFiManagerTask quản lý
    WiFi.setAutoReconnect(false);
    initializeAP();
    loadSavedWiFi();

    //6.5. tạo task và ép task đó chạy trên 1 cpu core cụ thể
    xTaskCreatePinnedToCore(
        wifiManagerTask,          // 1. Hàm mà task sẽ chạy
        "WiFiManagerTask",        // 2. Tên của task
        TASK_STACK_SIZE,          // 3. Kích thước stack của task
        nullptr,                  // 4. Tham số truyền vào task
        TASK_PRIORITY,            // 5. Độ ưu tiên của task
        &wifiManagerTaskHandle,   // 6. Nơi lưu TaskHandle_t của task
        1                         // 7. Core mà task được ghim vào
    );

    Serial.println("[WiFiManager] 6. Started");
}



//---------- II. các hàm để các tầng trên gọi xuống để gửi lệnh ---------

// 15. queue api - hàm để các tầng trên yêu cầu kết nối wifi
bool WiFiManager::requestConnect(const String &ssid, const String &password, const String &bssid)
{
    if(wifiCommandQueue == nullptr) return false;
    WiFiCommand command;
    command.type = WiFiCommandType::CONNECT;
    command.ssid = ssid;
    command.password = password;
    command.bssid = bssid;

    return xQueueSend(wifiCommandQueue, &command, pdMS_TO_TICKS(100)) == pdTRUE;
}

// 16. hàm yêu cầu hủy kết nối
bool WiFiManager::requestDisconnect()
{
    WiFiCommand command;
    command.type = WiFiCommandType::DISCONNECT;

    return xQueueSend(wifiCommandQueue, &command, pdMS_TO_TICKS(100)) == pdTRUE;
}

// 17. hàm yêu cầu hủy cái kết nối đang thực hiện kết nối
bool WiFiManager::requestCancelConnect()
{
    if (connectionState != WiFiConnectionState::CONNECTING)  return false;
    cancelRequested = true;

    return true;
}

// 18. hàm yêu cầu scan
bool WiFiManager::requestScan()
{
    WiFiCommand command;

    command.type = WiFiCommandType::SCAN;

    return xQueueSend(wifiCommandQueue, &command, pdMS_TO_TICKS(100)) == pdTRUE;
}

// ----------- III. các hàm getters để tầng trên lấy trạng thái ------------------
// 19. state
WiFiConnectionState WiFiManager::getState()
{
    return connectionState;
}

// 20. isConnected
bool WiFiManager::isConnected()
{
    return WiFi.status() == WL_CONNECTED;
}

// 21. lấy rssi
int32_t WiFiManager::getRSSI()
{
    if (!isConnected()) return -127;
    return WiFi.RSSI();
}

// 22. ssid
String WiFiManager::getSSID()
{
    return WiFi.SSID();
}

// 23.  lấy ip
String WiFiManager::getIP()
{
    if (!isConnected()) return "";
    return WiFi.localIP().toString();
}

// 24. lấy MAC
String WiFiManager::getMAC()
{
    return WiFi.macAddress();
}

// 25. kiểm tra có đang kết nối ko
bool WiFiManager::isConnecting()
{
    return connectionState == WiFiConnectionState::CONNECTING;
}

// 26. kiểm tra có sẵn kết quả kết nối chưa
bool WiFiManager::isConnectResultAvailable()
{
    return connectResultAvailable;
}

// 27. lấy kết quả kết nối mới nhất
bool WiFiManager::getLastConnectResult()
{
    return lastConnectResult;
}

// 28 lấy scan count
int WiFiManager::getScanCount()
{
    return scanResultCount;
}

// 29 lấy wifi đã scan được ở index i
ScannedWiFi WiFiManager::getScanResult(int index)
{
    if (index < 0 ||index >= scanResultCount) return {};
    return scanResults[index];
}

// 30. lấy số lượng các wifi đã save
int WiFiManager::getSavedCount()
{
    return savedWiFiCount;
}

// 31. lấy wifi đã save ở index
SavedWiFi WiFiManager::getSavedWiFi(int index)
{
    if (index < 0 || index >= savedWiFiCount) return {};
    return savedWiFi[index];
}

