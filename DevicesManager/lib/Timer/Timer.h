#pragma once

#include <Arduino.h>
#include <time.h>

namespace Timer
{
    bool begin();

    void setTime(time_t time);
    time_t getTime();
    bool isValid();
}