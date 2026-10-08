#include "DeviceManager.h"
#include <cstring>

namespace
{
    // 1. Configuration
    // Có thể đổi thành n theo thiết kế cuối cùng.

    DeviceTask *devices[DeviceManager::MAX_DEVICES] = {};
    uint8_t deviceCount = 0;
    bool initialized = false;

    // 2. hàm tìm index từ gpio
    int findDeviceIndex(uint8_t gpio)
    {
        for (uint8_t i = 0; i < DeviceManager::MAX_DEVICES; i++)
        {
            if (devices[i] != nullptr && (devices[i]->getGpio() == gpio)) return i;
        }
        return -1;
    }

    // 3. hàm tìm vị trí empty đầu tiên
    int findEmptySlot()
    {
        for (uint8_t i = 0; i < DeviceManager::MAX_DEVICES; i++)
        {
            if (devices[i] == nullptr) return i;
        }
        return -1;
    }
}


// 4. hàm chính
bool DeviceManager::begin()
{
    if(initialized) return false;
    for (uint8_t i = 0; i < DeviceManager::MAX_DEVICES; i++) devices[i] = nullptr;
    deviceCount = 0;
    initialized = true;

    return true;
}


// 5. Create Device
bool DeviceManager::createDevice(uint8_t gpio, const char *deviceType, const char *deviceName)
{
    // kiểm tra các thứ trước
    if(!initialized) return false;

    // Không cho phép 2 device dùng cùng GPIO.
    if (findDeviceIndex(gpio) >= 0) return false;

    // Kiểm tra số lượng device.
    if(deviceCount >= DeviceManager::MAX_DEVICES) return false;

    int slot = findEmptySlot();
    if(slot < 0) return false;

    // tạo
    DeviceTask *device = new DeviceTask(gpio, deviceType, deviceName);
    if(device == nullptr) return false;
    // xong thì start nó lên
    if(!device->start())
    {
        delete device;
        return false;
    }

    // tạo oke thì store nó lại
    devices[slot] = device;
    deviceCount++;
    return true;
}

// 6. hàm xóa device by gpio 
bool DeviceManager::deleteDevice(uint8_t gpio)
{
    if(!initialized) return false;
    
    int index = findDeviceIndex(gpio);
    if(index < 0) return false;

    delete devices[index];
    devices[index] = nullptr;
    if (deviceCount > 0) deviceCount--;
    return true;
}

// 7. hàm xóa device by gpio  + type + Name
// thường khi dùng cả type cả name thì nghĩa là ng ta có vẻ đang cần chắc chắn đúng device
bool DeviceManager::deleteDevice(uint8_t gpio, const char *deviceType, const char *deviceName)
{
    if(!initialized) return false;

    if (deviceType == nullptr || deviceName == nullptr) return false;
    
    int index = findDeviceIndex(gpio);
    if(index < 0) return false;

    DeviceTask *device = devices[index];
    // kiểm tra type và name
    if (strcmp(device->getDeviceType(),deviceType) != 0) return false;
    if (strcmp(device->getDeviceName(),deviceName) != 0) return false;

    // Delete DeviceTask
    delete device;
    devices[index] = nullptr;
    if(deviceCount > 0) deviceCount--;
    return true;
}

// 7. control
bool DeviceManager::controlDevice(uint8_t gpio, const DeviceCommand &command)
{
    if(!initialized) return false;
    DeviceTask *device = getDevice(gpio);

    if (device == nullptr) return false;
    return device->sendCommand(command);
}

// 8. Get device
DeviceTask *DeviceManager::getDevice(uint8_t gpio)
{
    if (!initialized) return nullptr;
    int index = findDeviceIndex(gpio);
    if (index < 0) return nullptr;
    return devices[index];
}

// 9. các hàm phụ
bool DeviceManager::hasDevice(uint8_t gpio)
{
    if (!initialized) return false;
    return findDeviceIndex(gpio) >= 0;
}

uint8_t DeviceManager::getDeviceCount()
{
    return deviceCount;
}

DeviceTask *DeviceManager::getDeviceByIndex(uint8_t index)
{
    if (!initialized) return nullptr;
    if (index >= DeviceManager::MAX_DEVICES) return nullptr;
    return devices[index];
}

void DeviceManager::end()
{
    if (!initialized) return;

    for (uint8_t i = 0; i < DeviceManager::MAX_DEVICES; i++)
    {
        if (devices[i] != nullptr)
        {
            delete devices[i];
            devices[i] = nullptr;
        }
    }

    deviceCount = 0;
    initialized = false;
}