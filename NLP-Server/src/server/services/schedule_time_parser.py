
import re

from datetime import datetime, timedelta, timezone
from fastapi import HTTPException

# Giờ Việt Nam: UTC+7
VN_TZ = timezone(timedelta(hours=7))

UNIT_SECONDS = {
    "giây": 1,
    "phút": 60,
    "giờ": 3600,
}


def invalid(message: str):
    raise HTTPException(
        status_code=422,
        detail={
            "state": "failed",
            "message": message,
        }
    )


# 1. ĐỔI "10 PHÚT" THÀNH 600 GIÂY
def parse_seconds(text: str) -> int:
    match = re.fullmatch(
        r"(?:sau\s+|trong\s+)?(\d+)\s+(giây|phút|giờ)",
        text.strip().casefold()
    )

    if not match:
        invalid(f"Không hiểu thời lượng: {text}")

    seconds = int(match.group(1)) * UNIT_SECONDS[match.group(2)]

    if seconds <= 0 or seconds > 2147483647:
        invalid("Thời lượng không hợp lệ.")

    return seconds


# 2. ĐỔI "NGÀY MAI LÚC 07:30" THÀNH UNIX TIMESTAMP
def parse_start_at(text: str) -> int:
    match = re.fullmatch(
        r"(?:(hôm nay|ngày mai)\s+)?"
        r"lúc\s+(\d{1,2}):(\d{2})",
        text.strip().casefold()
    )

    if not match:
        invalid(f"Không hiểu thời điểm: {text}")

    day_text, hour_text, minute_text = match.groups()

    hour = int(hour_text)
    minute = int(minute_text)

    if hour > 23 or minute > 59:
        invalid("Giờ hoặc phút không hợp lệ.")

    now = datetime.now(VN_TZ)

    day = now.date()

    if day_text == "ngày mai":
        day += timedelta(days=1)

    scheduled = datetime(
        day.year, day.month, day.day,
        hour, minute,
        tzinfo=VN_TZ,
    )

    timestamp = int(scheduled.timestamp())

    if timestamp <= int(now.timestamp()) + 15:
        invalid(
            "Thời điểm đã qua hoặc quá gần hiện tại. "
            "Hãy nhập thời điểm khác."
        )

    return timestamp


# 3. CHUẨN HÓA CÁC TIME ENTITY
def parse_schedule_times(entities: list) -> dict:
    result = {
        "scheduledDelay": None,
        "duration": None,
        "scheduledStartAt": None,
        "scheduledEndAt": None,
    }

    field_names = {
        "SCHEDULED_DELAY": "scheduledDelay",
        "DURATION": "duration",
        "SCHEDULED_START_AT": "scheduledStartAt",
    }

    for entity in entities:
        field = field_names.get(entity.type)

        if field is None:
            invalid(
                f"Mock chưa hỗ trợ kiểu thời gian: {entity.type}"
            )

        if result[field] is not None:
            invalid("Thông tin thời gian bị trùng lặp.")

        if entity.type == "SCHEDULED_START_AT":
            result[field] = parse_start_at(entity.text)
        else:
            result[field] = parse_seconds(entity.text)

    if all(value is None for value in result.values()):
        invalid("Không tìm thấy thông tin thời gian.")

    # Không sử dụng đồng thời Delay và StartAt.
    if (result["scheduledDelay"] is not None
        and result["scheduledStartAt"] is not None):
        invalid("Không thể dùng đồng thời Delay và StartAt.")

    return result
