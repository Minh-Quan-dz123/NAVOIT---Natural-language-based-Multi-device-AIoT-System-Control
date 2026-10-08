#pragma once
#include <Arduino.h>
namespace WiFiMonitor
{
    void begin();
    void setRSSIThreshold(int32_t threshold);
    int32_t getRSSIThreshold();

}