#pragma once

#include <ArduinoJson.h>
#include <stdint.h>

namespace Utils
{

    // 1. Lấy GPIO từ JSON value.
    // GPIO có thể được truyền dưới dạng số hoặc chuỗi số.
    // Ví dụ hợp lệ: 32, 32u, "32"
    bool getGpioFromJson(JsonVariantConst value, uint8_t &gpio);

    // 2. Lấy Unix timestamp (giây) từ JSON value.
    // Timestamp có thể được truyền dưới dạng:
    // - số nguyên: 1833232000
    // - chuỗi số: "1833232000"
    bool getTimestampFromJson(JsonVariantConst value, time_t &timestamp);

    // 3. hàm kiểm tra 2 mac có giống nhau ko
    bool isSameMac(const char *mac1, const char *mac2);
    
    // 4. Lấy số giây từ JSON value.
    // Chấp nhận:
    // - number: 120
    // - string: "120"
    bool getSecondsFromJson(JsonVariantConst value, uint32_t &seconds);


}