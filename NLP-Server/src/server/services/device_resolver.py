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
def resolve_device(devices: list, tags: list[str]) -> list[dict]:
    if not tags:
        raise HTTPException(
            422,
            detail={
                "state": "failed",
                "message": "Không xác định được Tag thiết bị."
            }
        )

    candidates = []
    seen_ids = set()

    for device in devices:
        # Khớp ít nhất một Tag
        if any(matches_tag(device, tag) for tag in tags):
            device_id = device.get("deviceId")

            # Tránh thêm trùng Device
            if device_id not in seen_ids:
                seen_ids.add(device_id)
                candidates.append(device)

    if not candidates:
        raise HTTPException(
            404,
            detail={
                "state": "failed",
                "message": "Không tìm thấy Device phù hợp.",
                "deviceTags": tags,
            }
        )

    return candidates