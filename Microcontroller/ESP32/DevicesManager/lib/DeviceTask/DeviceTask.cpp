#include "DeviceTask.h"
#include <cstring>
#include "Timer.h"


DeviceTask::DeviceTask(uint8_t gpio, const char *deviceType, const char *deviceName):
    _gpio(gpio),
    _status(DeviceStatus::OFF),
    _taskHandle(nullptr),
    _commandQueue(nullptr),
    _running(false),
    _scheduledAction(DeviceAction::OFF),
    _Tnow(Timer::getTime()),
    _Tstart(0),
    _Tend(0),
    ss(3)
{
    // 1. khởi tạo các thuộc tính
    strncpy(_deviceType, deviceType, DEVICE_TYPE_MAX_LENGTH-1);
    _deviceType[DEVICE_TYPE_MAX_LENGTH-1] = '\0';

    strncpy(_deviceName, deviceName, DEVICE_NAME_MAX_LENGTH-1);
    _deviceName[DEVICE_NAME_MAX_LENGTH-1] = '\0';

}

// 2. destructor
DeviceTask::~DeviceTask()
{
    stop();
    if(_commandQueue != nullptr)
    {
        vQueueDelete(_commandQueue);
        _commandQueue = nullptr;
    }
}

// 3. hàm start
bool DeviceTask::start()
{
    if(_running) return false;

    // 3.1. cấu hình gpio
    pinMode(_gpio, OUTPUT);
    digitalWrite(_gpio, LOW);
    
    _status = DeviceStatus::OFF;

    // 3.2. tạo queue
    if(_commandQueue == nullptr) _commandQueue = xQueueCreate(DEVICE_TASK_QUEUE_SIZE, sizeof(DeviceCommand));

    if(_commandQueue == nullptr) return false;

    // 3.3. tạo task
    BaseType_t result = xTaskCreate(
        DeviceTask::taskEntry,
        _deviceName,
        DEVICE_TASK_STACK_SIZE,
        this,
        DEVICE_TASK_PRIORITY,
        &_taskHandle);
    
    if(result != pdPASS)
    {
        vQueueDelete(_commandQueue);
        _commandQueue = nullptr;
        _taskHandle = nullptr;
        return false;
    }

    _running = true;
    return true;
}

// 4. hàm stop
bool DeviceTask::stop()
{
    if(!_running) return true;
    if(_taskHandle != nullptr)
    {
        vTaskDelete(_taskHandle);
        _taskHandle = nullptr;
    }

    digitalWrite(_gpio, LOW);
    _status = DeviceStatus::OFF;

    // Clear schedule
    ss = 3;

    _Tstart = 0;
    _Tend = 0;

    _running = false;
    return true;
}

// 5. hàm send command
bool DeviceTask::sendCommand(const DeviceCommand &command)
{
    if(!_running) return false;
    if(_commandQueue == nullptr) return false;

    BaseType_t result = xQueueSend(_commandQueue, &command, pdMS_TO_TICKS(100));
    return result == pdPASS;
}

// 6. hàm chính
void DeviceTask::taskEntry(void *parameter)
{
    DeviceTask *deviceTask = static_cast<DeviceTask*>(parameter);
    if(deviceTask != nullptr) deviceTask->taskLoop();
    vTaskDelete(nullptr);
}

// 7. Task Loop
void DeviceTask::taskLoop()
{
    DeviceCommand command;
    while(true)
    {
        if(xQueueReceive(_commandQueue, &command, pdMS_TO_TICKS(DEVICE_TASK_TICK_MS)) == pdPASS)
        {
            processCommand(command);
        }

        checkSchedule();
    }
}

// 8. hàm xử lý command
void DeviceTask::processCommand(const DeviceCommand &command)
{
    // đầu tiên là kiểm tra xem đây có phải hủy lịch ko
    if(command.action == DeviceAction::CANCEL_SCHEDULE)
    {
        cancelSchedule();
        return;
    }

    // tiếp theo, trước tiên tính Xo, Xyc, 1 - Xyc (trạng thái nghịch đảo)
    DeviceStatus Xo = _status;
    DeviceStatus Xyc = (command.action == (DeviceAction::ON))? (DeviceStatus::ON): (DeviceStatus::OFF);
    DeviceStatus Xyc_end = (Xyc == (DeviceStatus::ON)) ? (DeviceStatus::OFF): (DeviceStatus::ON);

    // cách xử lý là rẽ nhánh từng trường hợp
    // TH1: Chỉ có Action, còn lại là 0, "", null
    if (command.duration == 0 &&
        command.scheduled_delay == 0 &&
        command.scheduled_start_at == 0 &&
        command.scheduled_end_at == 0)
    {
        _Tnow = Timer::getTime(); // Xo
        _Tstart = _Tnow;  // Xo
        _Tend = _Tnow;    // Xyc
        createSchedule(_Tnow, _Tstart, _Tend, Xo, Xo, Xyc);
        return;
    }

    // cần create
    // TH2: Action + duration (duration > 0)
    if (command.duration > 0 &&
        command.scheduled_delay == 0 &&
        command.scheduled_start_at == 0 &&
        command.scheduled_end_at == 0)
    {
        // Xo, Xyc, 1-Xyc
        _Tnow = Timer::getTime();
        _Tstart = _Tnow;
        _Tend = _Tnow + (command.duration);
        createSchedule(_Tnow, _Tstart, _Tend, Xo, Xyc, Xyc_end);
        return;
    }

    // ========================================================
    // TH4: ACTION + SCHEDULED_DELAY
    // ========================================================
    if (command.duration == 0 &&
        command.scheduled_delay > 0 &&
        command.scheduled_start_at == 0 &&
        command.scheduled_end_at == 0)
    {
        // Xo, Xo, Xyc
        _Tnow = Timer::getTime();
        _Tstart = _Tnow;
        _Tend = _Tnow + ((command.scheduled_delay));
        createSchedule(_Tnow, _Tstart, _Tend, Xo, Xo, Xyc);
        return;
    }


    // ========================================================
    // TH3: ACTION + SCHEDULED_START_AT
    // ========================================================
    if ((command.duration == 0 &&
        command.scheduled_delay == 0 &&
        command.scheduled_start_at > 0 &&
        command.scheduled_end_at == 0)
        ||
        (command.duration == 0 &&
        command.scheduled_delay == 0 &&
        command.scheduled_start_at == 0 &&
        command.scheduled_end_at > 0))
    {
        // Xo,Xo,Xyc
        _Tnow = Timer::getTime();
        _Tstart = _Tnow;
        _Tend = command.scheduled_end_at > 0 ? command.scheduled_end_at: command.scheduled_start_at; 
        createSchedule(_Tnow, _Tstart, _Tend, Xo, Xo, Xyc);

        return;
    }


    // ========================================================
    // TH5: ACTION + SCHEDULED_AT + DURATION
    // ========================================================
    if ((command.duration > 0 &&
        command.scheduled_delay == 0 &&
        command.scheduled_start_at > 0 &&
        command.scheduled_end_at == 0)
        ||
        (command.duration > 0 &&
        command.scheduled_delay == 0 &&
        command.scheduled_start_at == 0 &&
        command.scheduled_end_at > 0)
        )
    {
        // Xo, Xyc, 1-Xyc
        _Tnow = Timer::getTime();
        _Tstart = command.scheduled_start_at > 0? command.scheduled_start_at: command.scheduled_end_at; 
        _Tend = _Tstart + command.duration;
        createSchedule(_Tnow, _Tstart, _Tend, Xo, Xyc, Xyc_end);
        return;
    }


    // ========================================================
    // TH6: ACTION + SCHEDULED_DELAY + DURATION
    // ========================================================
    if (command.duration > 0 &&
        command.scheduled_delay > 0 &&
        command.scheduled_start_at == 0 &&
        command.scheduled_end_at == 0)
    {
        // Xo, Xyc, 1-Xyc
        _Tnow = Timer::getTime();
        _Tstart = _Tnow + command.scheduled_delay;
        _Tend = _Tstart + command.duration;
        createSchedule(_Tnow, _Tstart, _Tend, Xo, Xyc, Xyc_end);

        return;
    }


    // ========================================================
    // TH7: ACTION + SCHEDULED_DELAY + SCHEDULED_AT
    // ========================================================
    if ((command.duration == 0 &&
        command.scheduled_delay > 0 &&
        command.scheduled_start_at == 0 &&
        command.scheduled_end_at > 0) 
        ||
        (command.duration == 0 &&
        command.scheduled_delay > 0 &&
        command.scheduled_start_at > 0 &&
        command.scheduled_end_at == 0)
    )
    {
        // tầng trên đảm bảo đầu vào đúng
        // Xo, Xyc, 1-Xyc
        _Tnow = Timer::getTime();
        _Tstart = _Tnow + command.scheduled_delay; 
        _Tend = command.scheduled_end_at > 0 ? command.scheduled_end_at : command.scheduled_start_at; 
        createSchedule(_Tnow, _Tstart, _Tend, Xo, Xyc, Xyc_end);

        return;
    }


    // ========================================================
    // TH8: ACTION + SCHEDULED_START_AT + SCHEDULED_END_AT
    // ========================================================
    if (command.duration == 0 &&
        command.scheduled_delay == 0 &&
        command.scheduled_start_at > 0 &&
        command.scheduled_end_at > 0)
    {
        // Xo, Xyc, 1-Xyc 
        _Tnow = Timer::getTime();
        // dùng min max để lỡ tầng trên truyền nhầm (ko sai)
        _Tstart = min(command.scheduled_start_at, command.scheduled_end_at); 
        _Tend = max(command.scheduled_start_at, command.scheduled_end_at); 
        createSchedule(_Tnow, _Tstart, _Tend, Xo, Xyc, Xyc_end);


        return;
    }
}


// 9. turn on/off
void DeviceTask::turnOn()
{
    digitalWrite(_gpio, HIGH);
    _status = DeviceStatus::ON;
}

void DeviceTask::turnOff()
{
    digitalWrite(_gpio, LOW);
    _status = DeviceStatus::OFF;
}

void DeviceTask::executeMotorControl(DeviceStatus status)
{
    if (status == DeviceStatus::ON)turnOn();
    else turnOff();
}
void DeviceTask::executeMotorControl(DeviceAction status)
{
    if (status == DeviceAction::ON)turnOn();
    else if(status == DeviceAction::OFF) turnOff();
}


// 10. create schedule
void DeviceTask::createSchedule(time_t t_now, time_t t_start, time_t t_end, DeviceStatus x1, DeviceStatus x2, DeviceStatus x3)
{
    if(t_end < t_start)
    {
        return;
    }
    // cập nhật
    _Tnow = t_now;
    _Tstart = t_start;
    _Tend = t_end;
    ss = 1;
    _statusScheduled[0] = x1;
    _statusScheduled[1] = x2;
    _statusScheduled[2] = x3;
}


// 11. check schedule
void DeviceTask::checkSchedule()
{
    if((ss != 1) && (ss != 2)) return;

    // nếu có rồi thì thực hiện đếm giờ
    // lấy t_now ra rồi kiểm tra có = t_start ko, nếu bằng thì đổi DeviceStatus thành
    _Tnow = Timer::getTime();
    if(ss == 1)
    {
        if(_Tnow >= _Tstart)
        {
            _status = _statusScheduled[1];
            ss += 1;
            executeMotorControl(_status);
        }
    } 
    else if(ss == 2)
    {
        if(_Tnow >= _Tend)
        {
            _status = _statusScheduled[2];
            ss += 1;
            executeMotorControl(_status);
        }
    }
}

// 12.  Cancel Schedule
void DeviceTask::cancelSchedule()
{
    ss = 3;
}


// 13. các hàm get
uint8_t DeviceTask::getGpio() const
{
    return _gpio;
}

const char *DeviceTask::getDeviceType() const
{
    return _deviceType;
}


const char *DeviceTask::getDeviceName() const
{
    return _deviceName;
}


DeviceStatus DeviceTask::getStatus() const
{
    return _status;
}

bool DeviceTask::isRunning() const
{
    return _running;
}

bool DeviceTask::hasSchedule() const
{
    return ((ss == 1) || (ss == 2));
}

