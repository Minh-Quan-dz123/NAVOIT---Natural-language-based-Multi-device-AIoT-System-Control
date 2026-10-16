#pragma once
#include <Arduino.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <freertos/queue.h>

#define DEVICE_TASK_QUEUE_SIZE 10
#define DEVICE_NAME_MAX_LENGTH 128
#define DEVICE_TYPE_MAX_LENGTH 64

#define DEVICE_TASK_STACK_SIZE 4096
#define DEVICE_TASK_PRIORITY 1

// DeviceTask kiểm tra schedule mỗi 100 ms.
#define DEVICE_TASK_TICK_MS 100

// ============================================================
// Device Command
//
// Quy ước:
//   duration = 0
//       -> không sử dụng duration
//
//   scheduled_delay = 0
//       -> không sử dụng delay
//
//   scheduled_start_at = 0
//       -> không sử dụng start_at
//
//   scheduled_end_at = 0
//       -> không sử dụng end_at
//
// Các trường bằng 0 được xem là "ko có giá trị".
// ============================================================

// 1 các action
enum class DeviceAction
{
    ON, OFF, CANCEL_SCHEDULE
};

// 2. Các command
struct DeviceCommand
{
    DeviceAction action;

    // 2.1. Duration in seconds (= 0 means not used).
    uint32_t duration;
    uint32_t scheduled_delay;
    time_t scheduled_start_at;
    time_t scheduled_end_at;
};

// 3. các state của device
enum class DeviceStatus
{
    OFF, ON
};

// 4. DeviceTask
class DeviceTask
{
    public:
        DeviceTask(uint8_t gpio, const char *deviceType, const char *deviceName);
        ~DeviceTask(); // hàm hủy

        // 4.1. các phương thức điều khiển
        bool start(); // hàm bắt đầu sử dụng thiết bị này
        bool stop(); // tạm dừng ko dừng thiết bị này nữa
        bool sendCommand(const DeviceCommand &command);

        // 4.2. lấy thông tin
        uint8_t getGpio() const;
        const char *getDeviceType() const;
        const char *getDeviceName() const;
        DeviceStatus getStatus() const;
        bool isRunning() const;

        // 4.3. schedule information
        bool hasSchedule() const;
    
    private:
        // FreeRTOS task entry
        static void taskEntry(void *parameter);
        void taskLoop();

        // 4.4. hàm xử lý command
        void processCommand(const DeviceCommand &command);
        

        // 4.5. GPIO control mức thấp 
        void turnOn();
        void turnOff();
        void executeMotorControl(DeviceStatus status);//hàm sẽ thực thi theo status 
        void executeMotorControl(DeviceAction status); // 

        // 4.6. schedule
        void createSchedule(time_t t_now, time_t t_start, time_t t_end, DeviceStatus x1, DeviceStatus x2, DeviceStatus x3);
        void cancelSchedule();
        void checkSchedule();


        // 4.7. device information
        uint8_t _gpio;
        char _deviceType[DEVICE_TYPE_MAX_LENGTH];
        char _deviceName[DEVICE_NAME_MAX_LENGTH];
        DeviceStatus _status;

        // 4.8 FreeRTOS
        TaskHandle_t _taskHandle;
        QueueHandle_t _commandQueue;

        bool _running;// task đang run ko

        // 4.9 Schedule State
        DeviceAction _scheduledAction; // loại action

        time_t _Tnow; // millis
        time_t _Tstart; 
        time_t _Tend;
        DeviceStatus _statusScheduled[3];
        uint8_t ss; // biến phụ giúp xem đã qua Tstart chưa 
        // ss = 1, là đang _Tnow -> _Tstart 
        // ss = 2, là đang _Tnow -> _Tend   
        // ss = 3, là hết rồi,  ko có lịch 
};