#include "MQTTManager.h"

#include <Arduino.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <WiFiClientSecure.h>

#include "WiFiManager.h"
#include "DeviceManager.h"
#include "Timer.h"
#include "Utils.h"
// NHIỆM VỤ:
// - Kết nối ESP32 với MQTT Broker
// - Subscribe các MQTT topic -> Nhận JSON command từ Server -> Phân tích command -> Gửi command xuống DeviceManager
// - Publish topic -> Gửi response từ ESP32 về Server
//
// Mọi việc kết nối/ngắt/scan WiFi do WiFiManager đảm nhiệm.
// MQTTManager chỉ sử dụng:
//     WiFiManager::isConnected()
//     WiFiManager::getMAC()

namespace
{
    // 1. cấu hình

    // 1.1. MQTT CONNECTION
    constexpr const char *MQTT_BROKER = "03fbc12347f1474da0ae09d7f1a9c894.s1.eu.hivemq.cloud";
    constexpr uint16_t MQTT_PORT = 8883;
    constexpr const char *MQTT_USERNAME = "hivemq.webclient.1791559584748";
    constexpr const char *MQTT_PASSWORD = "vjckvnZlSmyqiVHu9UB4B8WZyAc%hPcZ";

    // 1.2. MQTT TASK CONFIGURATION
    constexpr uint32_t MQTT_TASK_STACK_SIZE = 8192;
    constexpr UBaseType_t MQTT_TASK_PRIORITY = 2;

    // 1.3. OTHERS
    //Kiểm tra MQTT định kỳ
    constexpr uint32_t MQTT_TASK_TICK_MS = 100;

    // Khoảng thời gian giữa các lần reconnect MQTT
    constexpr uint32_t MQTT_RECONNECT_INTERVAL_MS = 5000;

    // 1.4. khởi tạo 1 số giá trị trong topic
    // iot/{microcontrollertype}/{version}/{esp32_id}/{direction}/{type}
    // {microcontrollertype}	esp32/esp8266	
    // {version}	v1/v2/v3/v3_1	
    // {esp32_id}	là địa chỉ MAC của nó	ID duy nhất của ESP32  
    // {direction}	FROM_SV/FROM_ESP32/FROM_ESP8266	server-to-device hoặc device-to-server
    // {type}	command/ configuration	Loại message
    //
    constexpr const char *MQTT_API_VERSION = "v1";
    constexpr const char *MQTT_MICROCONTROLLER_TYPE = "esp32";


    // 2. Khai báo các buffer topic
    char _commandSubscribeTopic[128]; 
    char _configurationSubscribeTopic[128];
    //iot/esp32/v1/jkqwbcwfjd/FROM_SV/COMMAND
    //iot/esp32/v1/jkqwbcwfjd/FROM_SV/CONFIGURATION

    char _commandPublishTopic[128];
    char _configurationPublishTopic[128];
    //iot/esp32/v1/jkqwbcwfjd/ROM_ESP32/COMMAND
    //iot/esp32/v1/jkqwbcwfjd/ROM_ESP32/CONFIGURATION

    // 5. MQTT OBJECT
    WiFiClientSecure _wifiClient; // TCP client dùng để kết nối tới MQTT Broker.
    PubSubClient _mqttClient(_wifiClient); // MQTT client sử dụng WiFiClient ở trên.

    TaskHandle_t _taskHandle = nullptr;

    bool _running = false;

    unsigned long _lastReconnectAttempt = 0; // Thời điểm cuối cùng MQTT thử reconnect.

    // 6. MQTT client id 
    char _clientId[32]; // ví dụ ESP32_AABBCCDDEEFF

    void buildClientId()
    {
        // Ý tưởng: Lấy MAC của ESP32 thông qua WiFiManager
        // => AA:BB:CC:11:22:33
        // => chuyển thành ESP32_AABBCC112233
        String mac = WiFiManager::getMAC();
        mac.replace(":", "");// Xóa dấu ':' trong MAC.
        snprintf( _clientId, sizeof(_clientId), "ESP32_%s",mac.c_str());
    }

    // 7. tạo MQTT topic
    // iot/{microcontrollertype}/{version}/{esp32_id}/{direction}/{type}
    void buildTopics()
    {
        String mac = WiFiManager::getMAC();
        mac.replace(":", "");

        snprintf(
            _commandSubscribeTopic,
            sizeof(_commandSubscribeTopic),
            "iot/%s/%s/%s/FROM_SV/command",
            MQTT_MICROCONTROLLER_TYPE,
            MQTT_API_VERSION,
            mac.c_str()
        );

        snprintf(
            _configurationSubscribeTopic,
            sizeof(_configurationSubscribeTopic),
            "iot/%s/%s/%s/FROM_SV/configuration",
            MQTT_MICROCONTROLLER_TYPE,
            MQTT_API_VERSION,
            mac.c_str()
        );

        snprintf(
            _commandPublishTopic,
            sizeof(_commandPublishTopic),
            "iot/%s/%s/%s/FROM_ESP32/command",
            MQTT_MICROCONTROLLER_TYPE,
            MQTT_API_VERSION,
            mac.c_str()
        );

        snprintf(
            _configurationPublishTopic,
            sizeof(_configurationPublishTopic),
            "iot/%s/%s/%s/FROM_ESP32/configuration",
            MQTT_MICROCONTROLLER_TYPE,
            MQTT_API_VERSION,
            mac.c_str()
        );
    }
    //=====================================
    // Các hàm gửi, nhận
    //=====================================
    // 8. Publish JSON
    // Chuyển JsonDocument thành chuỗi JSON => rồi publish lên MQTT topic.
    bool publishJson(const char *topic, JsonDocument &doc)
    {
        if (!_mqttClient.connected())
        {
            Serial.println("[ERROR] MQTT is NOT connected");
            Serial.printf("[INFO] MQTT state: %d\n", _mqttClient.state());
            return false;
        }
        char buffer[2048];

        // Chuyển JsonDocument → chuỗi JSON.
        size_t length = serializeJson(doc, buffer, sizeof(buffer));

        if (length == 0 || length >= sizeof(buffer))
        {
            Serial.println("[ERROR] JSON serialization failed or buffer too small");
            return false;
        }

        Serial.printf("[TOPIC] %s\n", topic);
        Serial.printf("[PAYLOAD] %s\n", buffer);

        unsigned int requiredSize = 5+2 + strlen(topic) + length;

        Serial.printf("[DEBUG] Topic length: %u\n", strlen(topic));
        Serial.printf("[DEBUG] Payload length: %u\n", length);
        Serial.printf("[DEBUG] Estimated packet size: %u\n", requiredSize);
        Serial.printf("[DEBUG] Buffer size: %u\n", _mqttClient.getBufferSize());

        bool result = _mqttClient.publish(topic, buffer, length);

        Serial.printf("[RESULT] Publish: %s\n", result ? "SUCCESS" : "FAILED");

        if (!result)
        {
            Serial.printf("[ERROR] MQTT state: %d\n", _mqttClient.state());
            Serial.printf("[ERROR] Payload length: %u\n", length);
            Serial.printf("[ERROR] MQTT buffer size: %u\n", _mqttClient.getBufferSize());
            Serial.printf("[ERROR] MQTT connected: %d\n", _mqttClient.connected());
        }
        Serial.println("==================================");
        return result;
    }

    // 9. TẠO PHẦN THÔNG TIN CHUNG CỦA RESPONSE
    // Các response đều có một số thông tin giống nhau: command, command_id, microcontroller_id
    // Hàm này giúp không phải viết lại 3 trường trên
    void fillCommonResponse(JsonObject response, const char *command, const char *commandId, const char *status, const char *message)
    {
        response["command"] = command;
        response["command_id"] = commandId;
        response["microcontroller_id"] = WiFiManager::getMAC();
        response["status"] = status;
        response["message"] = message;
    }

    //===================================================
    // các hàm publish để response
    //===================================================
    // 10. CREATE_DEVICE_RESPONSE
    // Báo cho Server rằng CREATE_DEVICE đã xử lý thành công.
    void sendCreateDeviceResponse(const char *commandId, uint8_t gpio, const char *send_time, const char *status, const char *message)
    {
        JsonDocument doc;
        JsonObject response = doc.to<JsonObject>();

        fillCommonResponse(response, "CREATE_DEVICE_RESPONSE", commandId, status, message);

        response["gpio"] = gpio;
        response["send_time"] = send_time;

        publishJson(_commandPublishTopic, doc);
    }

    // 11. DELETE_DEVICE_RESPONSE
    // Báo cho Server rằng DELETE_DEVICE đã xử lý thành công.
    void sendDeleteDeviceResponse(const char *commandId, uint8_t gpio, const char *send_time, const char *status, const char *message)
    {
        JsonDocument doc;
        JsonObject response = doc.to<JsonObject>();
        fillCommonResponse(response, "DELETE_DEVICE_RESPONSE", commandId, status, message);

        response["gpio"] = gpio;
        response["send_time"] = send_time;

        publishJson(_commandPublishTopic, doc);
    }

    // 12. DEVICE_CONTROL_RESPONSE
    // Báo cho Server rằng lệnh điều khiển Device đã được DeviceManager xử lý thành công.
    void sendDeviceControlResponse(const char *commandId, uint8_t gpio, const char *send_time, const char *status, const char *message)
    {
        JsonDocument doc;
        JsonObject response = doc.to<JsonObject>();

        fillCommonResponse(response, "DEVICE_CONTROL_RESPONSE", commandId, status, message);

        response["gpio"] = gpio;
        response["send_time"] = send_time;

        publishJson(_commandPublishTopic,doc);
    }

    // 13. REFRESH_DEVICE_RESPONSE
    // Lấy toàn bộ Device đang được DeviceManager quản lý
    // {
    // "type": "REFRESH_DEVICE_RESPONSE",
    // "command_id": "CMD_001",

    // "gpios": [32, 33, 34, 35, 36],
    // "device_types": ["light", "fan", "light", "dht11", "fan"],
    // "device_names": ["Đèn học", "Quạt", "Đèn phòng", "Cảm biến nhiệt độ", "Quạt trần"],
    // "device_status": ["on", "off", "on", "off", "on"],

    // "device_count": 5,
    // "send_time": 1727850000
    // }
    void sendRefreshDeviceResponse(const char *commandId, const char *send_time, const char *status, const char *message)
    {
        JsonDocument doc;
        JsonObject response = doc.to<JsonObject>();

        fillCommonResponse(response,"REFRESH_DEVICE_RESPONSE",commandId, status, message);

        JsonArray gpios = response["gpios"].to<JsonArray>();
        JsonArray types = response["device_types"].to<JsonArray>();
        JsonArray names = response["device_names"].to<JsonArray>();
        JsonArray statuses = response["device_status"].to<JsonArray>();

        uint8_t count = DeviceManager::getDeviceCount();

        response["device_count"] = count;
        for (uint8_t i = 0; i < DeviceManager::MAX_DEVICES; i++)
        {
            DeviceTask *device =DeviceManager::getDeviceByIndex(i);

            if (device == nullptr) continue;

            gpios.add(device->getGpio());
            types.add(device->getDeviceType());
            names.add(device->getDeviceName());

            if (device->getStatus() == DeviceStatus::ON) statuses.add("on");
            else statuses.add("off");
        }

        response["send_time"] = send_time;

        publishJson(_commandPublishTopic, doc);
    }

    // 13.5 Thêm hàm response thời gian
    void sendRefreshTimeResponse(const char *commandId, time_t currentTime, const char *status, const char *message)
    {
        JsonDocument doc;
        JsonObject response = doc.to<JsonObject>();

        fillCommonResponse(response, "REFRESH_TIME_ACK", commandId, status, message);

        response["current_time"] = static_cast<int64_t>(currentTime);

        publishJson(_configurationPublishTopic, doc);
    }

    // =======================================
    // các hàm pubich của set up time
    // Sau khi ESP32 kết nối MQTT thành công, yêu cầu Server gửi thời gian hiện tại.
    // =======================================
    // 14. GỬI YÊU CẦU LẤY THỜI GIAN
    void sendRefreshTimeRequest()
    {
        JsonDocument doc;
        JsonObject request = doc.to<JsonObject>();
        request["command"] = "REFRESH_TIME_REQUEST";
        request["command_id"] = "00011";
        request["microcontroller_id"] = WiFiManager::getMAC();
        publishJson(_configurationPublishTopic, doc);
    }

    // 15. XỬ LÝ REFRESH TIME RESPONSE
    // Nhận thời gian Server gửi xuống ESP32.
    // Hiện tại mới kiểm tra current_time.
    void processRefreshTimeResponse(JsonObject root)
    {
        const char *commandId = root["command_id"] | "";
        time_t currentTime;

        if (!Utils::getTimestampFromJson(root["current_time"], currentTime))
        {
            sendRefreshTimeResponse(commandId,0,"error","Missing or invalid current_time");
            return;
        }
        Timer::setTime(currentTime);
        sendRefreshTimeResponse(commandId,currentTime,"success","Time synchronized successfully");
    }

    // 17. hàm XỬ LÝ CREATE DEVICE
    // Nhận CREATE_DEVICE_REQUEST từ Server.
    // MQTTManager không trực tiếp tạo Device.
    // Nó lấy dữ liệu từ JSON rồi gọi:
    // DeviceManager::createDevice()
    void processCreateDevice(JsonObject root)
    {
        // Kiểm tra command_id.
        if (!root["command_id"].is<const char *>()) return;

        // Kiểm tra GPIO.
        uint8_t gpio;
        if (!Utils::getGpioFromJson(root["gpio"], gpio)) return;

        // Kiểm tra device_type.
        if (!root["device_type"].is<const char *>()) return;

        // Kiểm tra device_name.
        if (!root["device_name"].is<const char *>()) return;

        // Kiểm tra send_time.
        if (!root["send_time"].is<const char *>()) return;


        // Lấy dữ liệu từ JSON.
        const char *commandId = root["command_id"];
        const char *deviceType = root["device_type"];
        const char *deviceName = root["device_name"];
        const char *sendTime = root["send_time"];
        //uint8_t gpio = root["gpio"]; ở trên r
        
        // 17.1. Kiểm tra GPIO đã được đăng ký chưa.
        if (DeviceManager::hasDevice(gpio))
        {
            sendCreateDeviceResponse(commandId, gpio, sendTime,"error","GPIO is already configured");
            return;
        }

        // 17.2. Kiểm tra số lượng thiết bị tối đa.
        if ((DeviceManager::getDeviceCount()) >= (DeviceManager::MAX_DEVICES))
        {
            sendCreateDeviceResponse(commandId, gpio, sendTime,"error","Maximum number of devices reached");
            return;
        }

        // Yêu cầu DeviceManager tạo Device.
        bool result = DeviceManager::createDevice(gpio, deviceType, deviceName);

        // Nếu tạo thành công → gửi response.
        if (result)
        {
            sendCreateDeviceResponse(commandId, gpio, sendTime,"success", "Device created successfully");
        }
        else
        {
            sendCreateDeviceResponse(commandId, gpio, sendTime,"error", "Failed to create device");
        }
    }

    // 17. XỬ LÝ DELETE DEVICE
    // NHIỆM VỤ:
    // Nhận DELETE_DEVICE_REQUEST.
    // Sau đó gọi:
    // DeviceManager::deleteDevice()
    void processDeleteDevice(JsonObject root)
    {
        if (!root["command_id"].is<const char *>()) return;

        uint8_t gpio;
        if (!Utils::getGpioFromJson(root["gpio"], gpio)) return;

        // if (!root["device_type"].is<const char *>()) return;
        // if (!root["device_name"].is<const char *>()) return;
        if (!root["send_time"].is<const char *>()) return;

        // Lấy dữ liệu từ JSON.
        const char *commandId = root["command_id"];
        const char *deviceType = root["device_type"];
        const char *deviceName = root["device_name"];
        const char *sendTime = root["send_time"];
        //uint8_t gpio = root["gpio"]; ở trên r

        // Yêu cầu DeviceManager xóa Device.
        bool result = DeviceManager::deleteDevice(gpio);

        // Xóa thành công → gửi response.
        if (result)
        {
            sendDeleteDeviceResponse(commandId, gpio, sendTime,"success", "Device deleted successfully");
        }
        else
        {
            sendDeleteDeviceResponse(commandId, gpio, sendTime,"error", "Failed to delete device");
        }
    }

    // 18. XỬ LÝ REFRESH DEVICE
    // NHIỆM VỤ:
    // Server yêu cầu ESP32 gửi lại danh sách Device hiện tại.
    void processRefreshDevice(JsonObject root)
    {
        if (!root["command_id"].is<const char *>())
        {
            Serial.println("[ERROR] Missing or invalid command_id");
            return;
        }

        const char *commandId = root["command_id"];
        if (!root["send_time"].is<const char *>())
        {
            sendRefreshDeviceResponse(commandId,"","error","Missing or invalid send_time");
            return;
        }

        const char *sendTime = root["send_time"];
        sendRefreshDeviceResponse(commandId,sendTime,"success","Device list refreshed successfully");
    }


    // 19. XỬ LÝ DEVICE CONTROL
    // NHIỆM VỤ:
    // Nhận lệnh điều khiển Device từ Server.
    // Ví dụ: action = "on"
    // sẽ chuyển thành:
    // DeviceAction::ON
    // Sau đó tạo DeviceCommand và gửi cho:
    // DeviceManager::controlDevice()
    // ========================================================

    void processDeviceControl(JsonObject root)
    {
        // Kiểm tra dữ liệu bắt buộc
        if (!root["command_id"].is<const char *>()) return;

        uint8_t gpio;
        if (!Utils::getGpioFromJson(root["gpio"], gpio)) return;

        if (!root["detail"].is<JsonObject>()) return;
        if (!root["send_time"].is<const char *>()) return;


        // Lấy dữ liệu chính
        const char *commandId = root["command_id"];
        JsonObject detail = root["detail"];
        const char *sendTime = root["send_time"];

        // Lấy action
        if (!detail["action"] .is<const char *>()) return;

        const char *action = detail["action"];

        // Chuyển String action thành DeviceAction
        DeviceAction deviceAction;

        if (strcasecmp(action, "on") == 0) deviceAction = DeviceAction::ON;
        else if (strcasecmp(action, "off") == 0) deviceAction = DeviceAction::OFF;
        else if (strcasecmp(action, "cancel_schedule") == 0) deviceAction = DeviceAction::CANCEL_SCHEDULE;
        else return; // Action không hợp lệ.

        // Tạo DeviceCommand
        DeviceCommand command{};

        // Action chính.
        command.action = deviceAction;

        // Mặc định không có schedule.
        command.duration = 0;
        command.scheduled_delay = 0;
        command.scheduled_start_at = 0;
        command.scheduled_end_at = 0;

        // duration
        if (!detail["duration"].isNull())
        {
            if (!Utils::getSecondsFromJson(detail["duration"], command.duration)) return;
        }

        if (!detail["scheduled_delay"].isNull())
        {
            if (!Utils::getSecondsFromJson(detail["scheduled_delay"], command.scheduled_delay)) return;
        }

        // scheduled_start_at : 1791021600
        if (!detail["scheduled_start_at"].isNull())
        {
            if (!Utils::getTimestampFromJson(detail["scheduled_start_at"],command.scheduled_start_at)) return;
        }

        if (!detail["scheduled_end_at"].isNull())
        {
            if (!Utils::getTimestampFromJson(detail["scheduled_end_at"], command.scheduled_end_at)) return;
        }

        // Kiểm tra Timer đã được đồng bộ thời gian chưa.
        // Các lệnh có duration hoặc schedule cần thời gian hợp lệ.
        if (
            command.duration > 0 ||
            command.scheduled_delay > 0 ||
            command.scheduled_start_at > 0 ||
            command.scheduled_end_at > 0
        )
        {
            if (!Timer::isValid())
            {
                sendDeviceControlResponse(commandId, gpio,sendTime,"error",
                    "Cannot execute time-based command: system time has not been synchronized. Please synchronize time before using duration or scheduling parameters."
                );

                return;
            }
        }

        // Kiểm tra GPIO có đang được DeviceManager quản lý không.
        if (!DeviceManager::hasDevice(gpio))
        {
            sendDeviceControlResponse(commandId,gpio,sendTime,"error","GPIO is not configured on this ESP32");
            return;
        }

        // Gửi command sang DeviceManager
        bool result = DeviceManager::controlDevice(gpio, command);

        // DeviceManager xử lý thành công
        if (result)
        {
            sendDeviceControlResponse(commandId, gpio, sendTime,"success", "Device controlled successfully");
        }
        else
        {
            sendDeviceControlResponse(commandId, gpio, sendTime, "error", "Failed to control device");
        }

  
    }

    // ========================================================
    // 20. MQTT CALLBACK
    // ========================================================
    // Đây là nơi MQTTManager nhận message từ MQTT Broker.
    // Luồng:
    // MQTT Broker
    //      ↓
    // mqttCallback()
    //      ↓
    // Parse JSON
    //      ↓
    // Kiểm tra topic
    //      ↓
    // Kiểm tra command
    //      ↓
    // processXXX()
    // ========================================================

    void mqttCallback(char *topic, byte *payload, unsigned int length)
    {
        Serial.println("\n========== MQTT MESSAGE RECEIVED ==========");
        Serial.printf("[TOPIC] %s\n", topic);
        Serial.printf("[LENGTH] %u bytes\n", length);

        char buffer[2048];

        if (length >= sizeof(buffer))
        {
            Serial.println("[ERROR] Payload too large");
            return;
        }
        memcpy(buffer,payload,length);

        // Thêm '\0' để buffer trở thành C-string.
        buffer[length] = '\0';

        Serial.printf("[PAYLOAD] %s\n", buffer);

        // 20.2. Parse JSON
        JsonDocument doc;
        DeserializationError error = deserializeJson(doc, buffer);
        if (error)
        {
            Serial.printf("[ERROR] JSON parse failed: %s\n", error.c_str());
            return;
        }

        JsonObject root = doc.as<JsonObject>();

        // 20.25 tiền kiểm tra microcontroller_id
        Serial.println("[CHECK] Checking microcontroller_id...");
        if (!root["microcontroller_id"].is<const char *>())
        {
            Serial.println("[ERROR] Missing or invalid microcontroller_id");
            return;
        }

        const char *microcontrollerId = root["microcontroller_id"];
        String esp32Mac = WiFiManager::getMAC();

        Serial.printf("[CHECK] Server MAC: [%s]\n", microcontrollerId);
        Serial.printf("[CHECK] ESP32 MAC:  [%s]\n", esp32Mac.c_str());

        bool sameMac = Utils::isSameMac(microcontrollerId,esp32Mac.c_str());

        Serial.printf("[CHECK] MAC comparison: %s\n",sameMac ? "MATCH" : "NOT MATCH");

        if (!sameMac)
        {
            Serial.println("[ERROR] microcontroller_id does not match ESP32 MAC");
            Serial.println("[ERROR] Message ignored");
            return;
        }

        Serial.println("[CHECK] MAC matched");

        // 20.3. Kiểm tra topic
        Serial.println("[CHECK] Checking command topic...");

        if (!Utils::isSameMac(microcontrollerId, esp32Mac.c_str())) return;

        // 20.3. COMMAND TOPIC
        if (strcmp(topic, _commandSubscribeTopic) == 0)
        {
            // Phải có command.
            if (!root["command"].is<const char *>()) return;
            const char *command = root["command"];

            // 20.3.1. CREATE_DEVICE_REQUEST
            if (strcmp(command, "CREATE_DEVICE_REQUEST") == 0) processCreateDevice(root);

            // 20.3.2. DELETE_DEVICE_REQUEST
            else if (strcmp(command, "DELETE_DEVICE_REQUEST") == 0) processDeleteDevice(root);

            // 20.3.3. REFRESH_DEVICE_REQUEST            
            else if (strcmp(command,"REFRESH_DEVICE_REQUEST") == 0) processRefreshDevice(root);

            // 20.3.4. DEVICE_CONTROL_REQUEST
            else if (strcmp(command, "DEVICE_CONTROL_REQUEST") == 0) processDeviceControl(root);
        }

        // 20.4. CONFIGURATION TOPIC
        else if (strcmp(topic, _configurationSubscribeTopic) == 0)
        {
            if (!root["command"].is<const char *>())
            {
                return;
            }

            const char *command = root["command"];

            // 20.4.1. REFRESH_TIME_RESPONSE
            if (strcmp(command, "REFRESH_TIME_RESPONSE") == 0)
            {
                processRefreshTimeResponse(root);
            }
        }
    }

    // 21. KẾT NỐI MQTT BROKER
    // NHIỆM VỤ:
    //
    // 1. Kiểm tra WiFi đã connected chưa.
    // 2. Kết nối MQTT Broker.
    // 3. Subscribe command topic.
    // 4. Subscribe configuration topic.
    // 5. Yêu cầu Server gửi thời gian.

    bool connectMQTT()
    {
        // 21.1. MQTT chỉ có thể kết nối khi WiFi đã connected.
        if (!WiFiManager::isConnected()) return false;

        _wifiClient.setInsecure();
        // sau đó tạo Client ID.
        buildClientId();

        Serial.println("\n========== MQTT CONNECT ==========");
        Serial.printf("[MQTT] Client ID: %s\n", _clientId);
        Serial.printf("[MQTT] Subscribe command topic: %s\n", _commandSubscribeTopic);
        Serial.printf("[MQTT] Subscribe configuration topic: %s\n", _configurationSubscribeTopic);
        
        bool connected;

        // 21.2. Kết nối có username/password
        if (MQTT_USERNAME != nullptr && MQTT_PASSWORD != nullptr)
        {
            connected = _mqttClient.connect(_clientId, MQTT_USERNAME, MQTT_PASSWORD);
        }

        // Kết nối không cần username/password
        else connected = _mqttClient.connect(_clientId);

        // Kết nối thất bại.
        if (!connected)
        {
            Serial.printf("[MQTT] Ket noi that bai. State: %d\n", _mqttClient.state());
            Serial.println("==================================");
            return false;
        }

        Serial.println("[MQTT] Ket noi broker thanh cong.");
        // 21.2. Subscribe command và Subscribe configuration
        bool commandSubscribed =_mqttClient.subscribe(_commandSubscribeTopic);
        bool configurationSubscribed =_mqttClient.subscribe(_configurationSubscribeTopic);

        Serial.printf("[MQTT] Subscribe command: %s\n", commandSubscribed ? "SUCCESS" : "FAILED");
        Serial.printf("[MQTT] Subscribe configuration: %s\n", configurationSubscribed ? "SUCCESS" : "FAILED");

        // Nếu subscribe thất bại → disconnect.
        if (!commandSubscribed || !configurationSubscribed)
        {
            Serial.println("[MQTT] Subscribe that bai. Ngat ket noi.");
            _mqttClient.disconnect();
            Serial.println("==================================");
            return false;
        }


        // 21.3. MQTT kết nối thành công.
        Serial.println("[MQTT] Da subscribe thanh cong cac topic:");
        Serial.printf("  - %s\n", _commandSubscribeTopic);
        Serial.printf("  - %s\n", _configurationSubscribeTopic);

        // Yêu cầu Server gửi thời gian hiện tại.
        Serial.println("[MQTT] Gui REFRESH_TIME_REQUEST...");
        sendRefreshTimeRequest();

        Serial.println("==================================");
        return true;
    }

    // 23. MQTT TASK LOOP
    // NHIỆM VỤ:
    // Đây là vòng lặp chính của MQTT Task.
    // Mỗi vòng:
    //
    // 1. Kiểm tra WiFi.
    // 2. Nếu WiFi mất → ngắt MQTT.
    // 3. Nếu MQTT mất → thử reconnect.
    // 4. Nếu MQTT connected → xử lý MQTT packet.

    void taskLoop()
    {
        while (_running)
        {
            // TRƯỜNG HỢP 1:
            // WiFi chưa connected
            if (!WiFiManager::isConnected())
            {
                // WiFi mất thì MQTT cũng không thể hoạt động.
                if (_mqttClient.connected())
                {
                    _mqttClient.disconnect();
                }

                // Chờ một chút rồi kiểm tra lại.
                vTaskDelay(pdMS_TO_TICKS(MQTT_TASK_TICK_MS));
                continue;
            }


            // TRƯỜNG HỢP 2:
            // WiFi connected nhưng MQTT chưa connected
            if (!_mqttClient.connected())
            {
                Serial.println("[STATUS MQTT] taskLoop(): MQTT disconnected");
                unsigned long now = millis();

                // Chưa đủ 5 giây thì chưa reconnect.
                if (now - _lastReconnectAttempt >= MQTT_RECONNECT_INTERVAL_MS)
                {
                    _lastReconnectAttempt = now;
                    Serial.println("[MQTT] taskLoop(): Attempting to connect to HiveMQ...");

                    if (!connectMQTT())
                    {
                        Serial.printf("[MQTT] Connection failed. State: %d\n", _mqttClient.state());
                    }
                }
            }

            // TRƯỜNG HỢP 3:
            // MQTT đang connected
            else
            {
                unsigned long now = millis();

                if (now - _lastReconnectAttempt >= MQTT_RECONNECT_INTERVAL_MS)
                {
                    _lastReconnectAttempt = now;
                    Serial.println("[STATUS] MQTT connected to HiveMQ");
                }

                _mqttClient.loop();
            }

            // MQTT Task nghỉ 100 ms.
            vTaskDelay(pdMS_TO_TICKS(MQTT_TASK_TICK_MS));
        }
        // Khi _running = false,
        // Task tự kết thúc.
        vTaskDelete(nullptr);
    }

    // 23. FREE RTOS TASK ENTRY
    // NHIỆM VỤ:
    // Đây là hàm mà FreeRTOS gọi khi MQTT Task bắt đầu.
    // Nó chỉ có nhiệm vụ gọi taskLoop().
    void taskEntry(void *parameter)
    {
        // Không sử dụng parameter.
        (void)parameter;

        // Chạy vòng lặp chính của MQTT Task.
        taskLoop();
    }
}

// 24. MQTTManager PUBLIC API
namespace MQTTManager
{
    // begin()    
    // NHIỆM VỤ:
    // Khởi tạo MQTTManager và tạo MQTT FreeRTOS Task.
    bool begin()
    {
        // MQTTManager đã chạy rồi.
        if (_running) return false;

        // Tạo Client ID.
        buildClientId();

        // Tạo các MQTT topic.
        buildTopics();

        // Cấu hình MQTT Broker.
        _mqttClient.setServer(MQTT_BROKER, MQTT_PORT);

        // Tăng buffer để chứa MQTT packet gồm header, topic và payload.
        if (!_mqttClient.setBufferSize(2048))
        {
            Serial.println("[MQTT ERROR] Cannot allocate MQTT buffer");
            return false;
        }

        Serial.printf("[MQTT] Buffer size: %u bytes\n", _mqttClient.getBufferSize());

        // Đăng ký callback.
        // Khi MQTT nhận message: → mqttCallback()
        _mqttClient.setCallback(mqttCallback);

        // Cho phép MQTT Task chạy.
        _running = true;


        // Tạo FreeRTOS Task.
        BaseType_t result =
            xTaskCreate(
                taskEntry,
                "MQTTManager",
                MQTT_TASK_STACK_SIZE,
                nullptr,
                MQTT_TASK_PRIORITY,
                &_taskHandle
            );


        // Tạo Task thất bại.
        if (result != pdPASS)
        {
            _running = false;
            _taskHandle = nullptr;
            return false;
        }

        return true;
    }

    // end()
    // Dừng MQTTManager.
    void end()
    {
        // MQTTManager chưa chạy.
        if (!_running) return;
        _running = false; // Báo cho taskLoop() dừng.

        // Ngắt MQTT nếu đang connected.
        if (_mqttClient.connected()) _mqttClient.disconnect();

        // Xóa FreeRTOS Task.
        if (_taskHandle != nullptr)
        {
            vTaskDelete(_taskHandle);
            _taskHandle = nullptr;
        }
    }

    // Kiểm tra MQTT hiện tại có connected không.
    bool isConnected()
    {
        return _mqttClient.connected();
    }

    // getClientId()
    // NHIỆM VỤ:
    // Trả về MQTT Client ID của ESP32.
    const char *getClientId()
    {
        return _clientId;
    }

    void printSubscribedTopics()
    {
        Serial.println("\n========== MQTT SUBSCRIBED TOPICS ==========");
        Serial.printf("[MQTT] Command topic: %s\n", _commandSubscribeTopic);
        Serial.printf("[MQTT] Configuration topic: %s\n", _configurationSubscribeTopic);
        Serial.println("============================================\n");
    }

}


