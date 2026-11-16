# Đây là thuật toán xác định Device từ các Tag mà MockPredictor đã trả về.

# Quy tắc so khớp:
# - Các Tag trong cùng một TagGroup là đồng nghĩa.
# - Nếu câu có nhiều Tag thì Device phải khớp tất cả Tag.
# - Có thể khớp chính xác với DeviceName hoặc DeviceType.
# - Nếu nhiều Device cùng khớp, không tự chọn bừa một Device.


import unicodedata

from fastapi import HTTPException


# 1. CHUẨN HÓA TAG
def normalize_tag(value: str) -> str:
    if not isinstance(value, str):
        return ""

    value = " ".join(value.strip().casefold().split())
    return unicodedata.normalize("NFC", value)


# 2. KIỂM TRA MỘT TAG CÓ KHỚP DEVICE KHÔNG
def matches_tag(device: dict, tag: str) -> bool:

    wanted = normalize_tag(tag)

    if not wanted:
        return False

    # 2.1. So khớp tên Device
    if normalize_tag(device.get("deviceName")) == wanted:
        return True

    # 2.2. So khớp loại Device
    if normalize_tag(device.get("deviceType")) == wanted:
        return True

    # 2.3. So khớp các TagGroup
    groups = device.get("tagGroups") or []

    for group in groups:
        if not isinstance(group, list):
            continue

        for value in group:
            if normalize_tag(value) == wanted:
                return True

    return False


# 3. TÌM DEVICE PHÙ HỢP
def resolve_device(devices: list, tags: list[str]) -> dict:

    if not tags:
        raise HTTPException(
            422,
            detail={
                "state": "failed",
                "message": "Không xác định được Tag thiết bị."
            }
        )

    candidates = []

    for device in devices:

        # Device phải khớp tất cả Tag
        matched = all(
            matches_tag(device, tag)
            for tag in tags
        )

        if matched:
            candidates.append(device)

    # 4. KHÔNG TÌM THẤY
    if len(candidates) == 0:
        raise HTTPException(
            404,
            detail={
                "state": "failed",
                "message": "Không tìm thấy Device phù hợp với các Tag.",
                "deviceTags": tags,
            }
        )

    # 5. NHIỀU DEVICE CÙNG KHỚP
    if len(candidates) > 1:
        raise HTTPException(
            409,
            detail={
                "state": "failed",
                "message": (
                    "Có nhiều Device phù hợp. "
                    "Hãy bổ sung Tag để xác định rõ thiết bị."
                ),
                "candidates": [
                    {
                        "deviceId": device["deviceId"],
                        "deviceName": device.get("deviceName"),
                        "deviceType": device.get("deviceType"),
                    }
                    for device in candidates
                ],
            }
        )

    # 6. CHỈ CÓ MỘT DEVICE
    device = candidates[0]

    if (
        device.get("microcontrollerId") is None
        or device.get("gpio") is None
    ):
        raise HTTPException(
            409,
            detail={
                "state": "failed",
                "message": "Device chưa được liên kết MCU/GPIO."
            }
        )

    if device.get("syncStatus") != "synced":
        raise HTTPException(
            409,
            detail={
                "state": "failed",
                "message": "Device chưa được đồng bộ với ESP32."
            }
        )

    return device
