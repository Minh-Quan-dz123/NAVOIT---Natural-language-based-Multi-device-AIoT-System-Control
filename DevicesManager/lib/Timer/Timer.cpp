#include "Timer.h"

namespace
{
    time_t _baseTime = 0;// thời gian hiện tại MQTT cập nhật cho (giây)
    unsigned long _baseMillis = 0; // millisecond, là giá trị millis() tại đúng thời điểm _baseTime được cập nhật
    bool _valid = false; //Cho biết Timer đã được MQTT cung cấp thời gian hay chưa.
}

namespace Timer
{
    bool begin()
    {
        _baseTime = 0;
        _baseMillis = millis();
        _valid = false;

        return true;
    }

    void setTime(time_t time)
    {
        // cho mqtt call tới, cài thời gian cho _baseTime
        _baseTime = time;
        _baseMillis = millis();
        _valid = true;
    }

    time_t getTime()
    {
        if (!_valid) return 0;
        return _baseTime + ((millis() - _baseMillis) / 1000);
    }

    bool isValid()
    {
        return _valid;
    }
}