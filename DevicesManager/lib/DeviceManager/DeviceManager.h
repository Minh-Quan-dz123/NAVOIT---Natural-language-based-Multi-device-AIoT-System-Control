#pragma once

#include <Arduino.h>
#include "DeviceTask.h"


namespace DeviceManager
{

        bool begin();

        // 1. các hàm  management
        bool createDevice(uint8_t gpio, const char *deviceType, const char *deviceName);
        bool deleteDevice(uint8_t gpio, const char *deviceType, const char *deviceName);
        bool deleteDevice(uint8_t gpio);

        // 2. Device control
        bool controlDevice(uint8_t gpio, const DeviceCommand &command);

        // 3. get information
        DeviceTask *getDevice(uint8_t gpio); // lấy theo gpio
        bool hasDevice(uint8_t gpio);
        uint8_t getDeviceCount();
        DeviceTask *getDeviceByIndex(uint8_t index);
        constexpr uint8_t MAX_DEVICES = 6;

        // Shutdown
        void end();
        
};