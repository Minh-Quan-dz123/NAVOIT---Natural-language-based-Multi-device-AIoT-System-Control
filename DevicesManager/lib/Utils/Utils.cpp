#include "Utils.h"

#include <cstdlib>

namespace Utils
{
    // 1.
    bool getGpioFromJson(JsonVariantConst value, uint8_t &gpio)
    {
        // Trường hợp 1: GPIO là JSON number
        if (value.is<int>() ||
            value.is<uint8_t>() ||
            value.is<uint16_t>() ||
            value.is<uint32_t>() ||
            value.is<unsigned int>() ||
            value.is<long>() ||
            value.is<unsigned long>() )
        {
            long long number = value.as<long long>();

            if (number < 0 || number > 255) return false;

            gpio = static_cast<uint8_t>(number);
            return true;
        }

        // Trường hợp 2: GPIO là string, ví dụ "32"
        if (value.is<const char *>())
        {
            const char *str = value.as<const char *>();

            if (str == nullptr || *str == '\0') return false;

            char *endPtr = nullptr;
            long number = strtol(str, &endPtr, 10);

            // Không phải số hoặc còn ký tự sau số
            if (endPtr == str || *endPtr != '\0') return false;

            if (number < 0 || number > 255) return false;

            gpio = static_cast<uint8_t>(number);
            return true;
        }

        // Kiểu dữ liệu không hợp lệ
        return false;
    }

    // 2.
    bool getTimestampFromJson(JsonVariantConst value, time_t &timestamp)
    {
        // Trường không tồn tại hoặc null.
        if (value.isNull()) return false;

        // Trường hợp JSON là số nguyên.
        if (value.is<int64_t>())
        {
            timestamp = static_cast<time_t>(value.as<int64_t>());
            return true;
        }

        // Trường hợp JSON là số nguyên không dấu.
        if (value.is<uint64_t>())
        {
            timestamp = static_cast<time_t>(value.as<uint64_t>());
            return true;
        }

        // Trường hợp JSON là chuỗi.
        if (value.is<const char *>())
        {
            const char *text = value.as<const char *>();

            if (text == nullptr || *text == '\0') return false;

            char *end = nullptr;
            long long parsed = strtoll(text, &end, 10);

            // Chuỗi phải được parse toàn bộ thành số.
            if (end == text || *end != '\0') return false;

            timestamp = static_cast<time_t>(parsed);
            return true;
        }
        return false;
    }

    // 3.
    bool isSameMac(const char *mac1, const char *mac2)
    {
        if (mac1 == nullptr || mac2 == nullptr) return false;

        char normalized1[18];
        char normalized2[18];

        uint8_t index1 = 0;
        uint8_t index2 = 0;

        // Bỏ khoảng trắng đầu chuỗi MAC thứ nhất.
        while (isspace((unsigned char)*mac1)) mac1++;

        // Xóa ':' và bỏ khoảng trắng cuối chuỗi MAC thứ nhất.
        for (const char *p = mac1; *p != '\0'; ++p)
        {
            if (*p == ':') continue;
            if (isspace((unsigned char)*p)) continue;
            if (index1 >= sizeof(normalized1) - 1) return false;
            normalized1[index1++] = *p;
        }

        // Bỏ khoảng trắng đầu chuỗi MAC thứ hai.
        while (isspace((unsigned char)*mac2)) mac2++;

        // Xóa ':' khỏi MAC thứ hai.
        for (const char *p = mac2; *p != '\0'; ++p)
        {
            if (*p == ':') continue;
            if (isspace((unsigned char)*p)) continue;
            if (index2 >= sizeof(normalized2) - 1) return false;
            normalized2[index2++] = *p;
        }

        normalized1[index1] = '\0';
        normalized2[index2] = '\0';

        // MAC phải có đúng 12 ký tự sau khi bỏ ':'.
        if (index1 != 12 || index2 != 12) return false;

        return strcasecmp(normalized1, normalized2) == 0;
    }

    // 4.
    bool getSecondsFromJson(JsonVariantConst value, uint32_t &seconds)
    {
        if (value.isNull()) return false;

        // JSON number
        if (value.is<uint32_t>())
        {
            seconds = value.as<uint32_t>();
            return true;
        }

        // JSON string
        if (value.is<const char *>())
        {
            const char *text = value.as<const char *>();
            if (text == nullptr || *text == '\0') return false;

            char *end = nullptr;
            unsigned long parsed = strtoul(text, &end, 10);

            // Không phải số hoặc còn ký tự thừa.
            if (end == text || *end != '\0') return false;

            // Kiểm tra overflow uint32_t.
            if (parsed > UINT32_MAX) return false;

            seconds = static_cast<uint32_t>(parsed);
            return true;
        }

        return false;
    }

}