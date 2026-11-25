import asyncio
import time

import httpx

from src.server.config import (
    REGISTRY_BASE_URL,
    REGISTRY_INTERNAL_KEY,
    REGISTRY_TIMEOUT_SECONDS,
    MQTT_HOST,
)

from src.server.clients.mqtt_binding import normalize_mac
from src.server.services.operation_locks import get_mcu_lock

from src.server.services.device_reconcile import (
    read_snapshot,
    snapshot_devices,
    desired_devices,
    matches,
    execute_action,
)

from src.server.services.device_refresh import refresh_one_mcu

from src.server.services.device_schedule import send_schedule_mqtt

from src.server.services.schedule_sync import (
    read_schedule_snapshot,
    compare_schedule,
    build_recovery_command,
)


# 1. LẤY CẤU HÌNH CHUẨN TỪ REGISTRY
async def load_restore_data(mac, mcu_type):

    async with httpx.AsyncClient(
        base_url=REGISTRY_BASE_URL,
        timeout=REGISTRY_TIMEOUT_SECONDS,
        follow_redirects=False,
    ) as client:

        response = await client.get(
            f"/api/internal/microcontrollers/{mac}/restore",
            headers={
                "X-Internal-Key": REGISTRY_INTERNAL_KEY,
            },
            params={"type": mcu_type},
        )

        response.raise_for_status()
        data = response.json()

    if not isinstance(data, dict):
        raise ValueError("Registry trả dữ liệu không hợp lệ.")

    mcu = data.get("microcontroller")
    devices = data.get("devices")

    if not isinstance(mcu, dict):
        raise ValueError("Thiếu thông tin MCU.")

    if not isinstance(devices, list):
        raise ValueError("Thiếu danh sách Device.")

    if type(mcu.get("id")) is not int:
        raise ValueError("MCU ID không hợp lệ.")

    if type(mcu.get("userId")) is not int:
        raise ValueError("MCU chưa có chủ sở hữu.")

    if str(mcu.get("type") or "").strip().lower() != mcu_type:
        raise ValueError("Loại MCU trong Registry không khớp yêu cầu.")

    if normalize_mac(mcu.get("macAddress")) != mac:
        raise ValueError("MAC trong Registry không khớp.")

    for device in devices:

        if not isinstance(device, dict):
            raise ValueError("Dữ liệu Device không hợp lệ.")

        if device.get("microcontrollerId") != mcu["id"]:
            raise ValueError("Device không thuộc MCU đang khôi phục.")

        schedule = device.get("schedule")

        if schedule is not None:

            if not isinstance(schedule, dict):
                raise ValueError("Schedule không hợp lệ.")

            if schedule.get("deviceId") != device.get("deviceId"):
                raise ValueError("Schedule không thuộc Device.")

    return mcu, devices


# 2. GỬI LỆNH SCHEDULE VÀ KIỂM TRA LẠI
async def apply_and_verify_schedule(mcu, gpio, command, schedule):

    # command = None nghĩa là hủy Schedule.
    _, ack, _ = await send_schedule_mqtt(
        mcu["macAddress"],
        gpio,
        command,
        mcu["type"],
    )

    if ack.get("status") != "success":
        raise RuntimeError(
            f"GPIO {gpio}: ESP32 từ chối lệnh Schedule."
        )

    # Chờ DeviceTask xử lý FreeRTOS Queue.
    await asyncio.sleep(0.3)

    snapshot, clock_ok = await read_schedule_snapshot(mcu)

    if not clock_ok:
        raise RuntimeError("Đồng hồ ESP32 chưa chính xác.")

    actual = snapshot.get(gpio)

    if actual is None:
        raise RuntimeError(
            f"GPIO {gpio}: DeviceTask không tồn tại."
        )

    # Kiểm tra sau khi hủy Schedule.
    if command is None:

        if actual["active"]:
            raise RuntimeError(
                f"GPIO {gpio}: Schedule vẫn đang hoạt động."
            )

    # Kiểm tra sau khi tạo Schedule.
    else:

        if compare_schedule(schedule, actual) != "matched":
            raise RuntimeError(
                f"GPIO {gpio}: Schedule chưa khớp Registry."
            )

    return snapshot


# 3. KHÔI PHỤC SCHEDULE
async def restore_schedules(mcu, devices):

    snapshot, clock_ok = await read_schedule_snapshot(mcu)

    if not clock_ok:
        raise RuntimeError(
            "ESP32 chưa đồng bộ thời gian chính xác."
        )

    action_count = 0

    for device in devices:

        gpio = device["gpio"]
        schedule = device.get("schedule")

        actual = snapshot.get(gpio)

        if actual is None:
            raise RuntimeError(
                f"GPIO {gpio}: chưa có DeviceTask."
            )

        # 3.1. Registry không có lịch.
        # Hoặc lịch đã hết hạn.
        expired = False

        if schedule is not None:

            expires_at = schedule.get("expiresAt")

            if type(expires_at) is not int:
                raise ValueError(
                    f"GPIO {gpio}: ExpiresAt không hợp lệ."
                )

            expired = expires_at <= int(time.time())

        if schedule is None or expired:

            # ESP32 có lịch thừa thì hủy.
            if actual["active"]:

                snapshot = await apply_and_verify_schedule(
                    mcu,
                    gpio,
                    None,
                    None,
                )

                action_count += 1

            continue

        # 3.2. Lịch đã khớp, không gửi lệnh lại.
        if actual["active"]:

            state = compare_schedule(schedule, actual)

            if state == "matched":
                continue

        # 3.3. Chuyển lịch Registry thành command ESP32.
        command = build_recovery_command(schedule)

        if command is None:
            raise RuntimeError(
                f"GPIO {gpio}: Không thể khôi phục "
                "Schedule an toàn ở thời điểm hiện tại."
            )

        # 3.4. Nếu ESP32 có lịch khác Registry,
        # hủy lịch cũ trước khi khôi phục.
        if actual["active"]:

            snapshot = await apply_and_verify_schedule(
                mcu,
                gpio,
                None,
                None,
            )

            action_count += 1

        # 3.5. Khôi phục lịch chuẩn từ Registry.
        snapshot = await apply_and_verify_schedule(
            mcu,
            gpio,
            command,
            schedule,
        )

        action_count += 1

    return action_count


# 4. KHÔI PHỤC DEVICE/GPIO
async def restore_devices(mcu, devices):

    desired = desired_devices(
        devices,
        mcu["id"],
        mcu["type"],
    )

    snapshot = await read_snapshot(mcu)
    actual = snapshot_devices(snapshot)

    action_count = 0

    # 4.1. Xóa DeviceTask không khớp Registry.
    for gpio, device in list(actual.items()):

        if gpio in desired and matches(
            device,
            desired[gpio],
        ):
            continue

        snapshot = await execute_action(
            mcu,
            "DELETE_DEVICE_REQUEST",
            device,
        )

        actual = snapshot_devices(snapshot)
        action_count += 1

    # 4.2. Tạo DeviceTask còn thiếu.
    for gpio, device in desired.items():

        if gpio in actual and matches(
            actual[gpio],
            device,
        ):
            continue

        if gpio in actual:
            raise RuntimeError(
                f"GPIO {gpio} đang bị chiếm."
            )

        snapshot = await execute_action(
            mcu,
            "CREATE_DEVICE_REQUEST",
            device,
        )

        actual = snapshot_devices(snapshot)
        action_count += 1

    # 4.3. Cập nhật trạng thái đồng bộ vào Registry.
    refresh = await refresh_one_mcu(mcu)

    if refresh["state"] != "success":
        raise RuntimeError(
            "Không cập nhật được trạng thái Registry: "
            + refresh["message"]
        )

    if (
        refresh["mismatchedDeviceIds"]
        or refresh["unknownGpios"]
    ):
        raise RuntimeError(
            "Device/GPIO vẫn chưa khớp Registry."
        )

    # Đảm bảo tất cả Device mong muốn đều đã được xác nhận.
    expected_ids = {
        device["deviceId"]
        for device in desired.values()
    }

    matched_ids = set(refresh["matchedDeviceIds"])

    if expected_ids != matched_ids:
        raise RuntimeError(
            "Registry chưa xác nhận đủ các Device."
        )

    return action_count


# 5. LUỒNG KHÔI PHỤC CHÍNH
async def restore_mcu(mac_address, mcu_type):

    if not REGISTRY_BASE_URL or not REGISTRY_INTERNAL_KEY:
        raise RuntimeError(
            "NLP chưa cấu hình Device Registry."
        )

    if not MQTT_HOST:
        raise RuntimeError(
            "NLP chưa cấu hình MQTT_HOST."
        )

    mac = normalize_mac(mac_address)

    mcu_type = str(mcu_type or "").strip().lower()

    if not mcu_type or any(c in mcu_type for c in "/+#"):
        raise ValueError("Loại MCU không hợp lệ.")

    # 1. Đọc Registry để biết ID của MCU.
    initial_mcu, _ = await load_restore_data(
        mac, mcu_type
    )

    mcu_id = initial_mcu["id"]

    # 2. Khóa đúng MCU cần khôi phục.
    async with get_mcu_lock(mcu_id):

        # 3. Đọc lại cấu hình chuẩn sau khi lấy khóa.
        mcu, devices = await load_restore_data(
            mac, mcu_type
        )

        if mcu["id"] != mcu_id:
            raise RuntimeError(
                "MCU đã thay đổi trong lúc chờ lock."
            )

        # 4. Khôi phục thiết bị và GPIO.
        device_actions = await restore_devices(
            mcu,
            devices,
        )

        # 5. Khôi phục lịch sau khi Device đã đúng.
        schedule_actions = await restore_schedules(
            mcu,
            devices,
        )

        return {
            "status": "success",
            "message": "Devices and schedules restored",
            "deviceActions": device_actions,
            "scheduleActions": schedule_actions,
        }