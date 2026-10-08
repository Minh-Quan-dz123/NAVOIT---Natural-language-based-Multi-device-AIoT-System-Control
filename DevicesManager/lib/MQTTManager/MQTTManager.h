#pragma once
#include <Arduino.h>

namespace MQTTManager
{
    // Khởi tạo MQTT Manager Task
    bool begin();

    // Dừng MQTT Manager Task
    void end();

    // Kiểm tra MQTT đã kết nối chưa
    bool isConnected();

    // Thông tin MQTT
    const char *getClientId();
}