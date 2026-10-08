#pragma once
#include <Arduino.h>
#include <WiFi.h>

#define MAX_SAVED_WIFI 5
#define MAX_SCAN_WIFI 5

// 1. Trạng thái kết nối WiFi hiện tại
enum class WiFiConnectionState
{
    DISCONNECTED,
    CONNECTING,
    CONNECTED,
    FAILED
};

// 2. Các command để gửi vào WiFi Manager Task
enum class WiFiCommandType
{
    CONNECT,
    DISCONNECT,     // ngắt wifi đang kết nối
    CANCEL_CONNECT, // đang kết nối thì hủy
    SCAN
};

// 3. Command dùng cho Queue (gói dữ liệu được đưa vào Queue)
// ┌─────────────────────────────────────┐
// │ WiFiCommand                         │
// ├──────────────┬──────────────────────┤
// │ type         │ CONNECT              │
// │ ssid         │ HomeWiFi             │
// │ password     │ 12345678             │
// │ bssid        │ AA:BB:CC:DD:EE:FF    │
// └──────────────┴──────────────────────┘
struct WiFiCommand
{
    WiFiCommandType type;
    String ssid;
    String password;
    String bssid;
};

// 4. WiFi đã từng kết nối thành công
struct SavedWiFi 
{
    String ssid;
    String password;
    String bssid;
};

// 5. WiFi tìm đc khi scan
struct ScannedWiFi
{
    String ssid;
    int32_t rssi;   //độ mạnh tín hiệu WiFi (dBm)
    String bssid;   // địa chỉ max của wifi
};

// 6. API public để cho chương trình khác gọi 
namespace WiFiManager
{
    // 6.1. Nhóm điều khiển wifi
    void begin();
    bool requestConnect(const String &ssid, const String &password, const String &bssid ="");
    bool requestDisconnect(); // yêu cầu ngắt kết nối wifi hiện tại
    bool requestCancelConnect();
    bool requestScan();

    // 6.2. Nhón đọc trạng thái
    WiFiConnectionState getState();
    bool isConnected();     // dùng getState cũng đc nhưng sài cái này tiện hơn
    bool isConnecting();    // suy nghĩ tương tự

    // 6.3. Nhóm lấy thông tin wifi hiện tại
    int32_t getRSSI();
    String getSSID();
    String getIP();
    String getMAC();

    // 6.4. Nhóm lấy kết quả connect
    bool isConnectResultAvailable();
    bool getLastConnectResult();

    // 6.5 nhóm lấy kết quả scan
    int getScanCount();
    ScannedWiFi getScanResult(int index);

    // 6.6 nhóm lấy wifi đã lưu
    int getSavedCount();
    SavedWiFi getSavedWiFi(int index);
}