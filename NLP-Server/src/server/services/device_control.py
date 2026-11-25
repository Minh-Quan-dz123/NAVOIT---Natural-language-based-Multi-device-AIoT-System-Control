import asyncio
import json
import ssl

from datetime import datetime, timezone
from uuid import uuid4
from typing import Literal

import httpx
from aiomqtt import Client, MqttError
from fastapi import HTTPException
from pydantic import BaseModel


from src.server.config import (
    REGISTRY_BASE_URL,
    REGISTRY_INTERNAL_KEY,
    REGISTRY_TIMEOUT_SECONDS,
    MQTT_HOST,
    MQTT_PORT,
    MQTT_USERNAME,
    MQTT_PASSWORD,
    MQTT_TLS,
    MQTT_TIMEOUT_SECONDS,
)
from src.server.clients.mqtt_binding import normalize_mac

from contextlib import asynccontextmanager

from src.server.services.operation_locks import (
    get_device_lock,
    get_mcu_lock,
)


# 1. REQUEST TỪ FRONTEND
class ManualControlRequest(BaseModel):
    action: Literal["ON", "OFF"] # chỉ nhận 1 trong 2 giá trị


# 2. TRẢ LỖI
def fail(code: int, message: str, state: str = "failed"):
    raise HTTPException(
        status_code=code,
        detail={"state": state, "message": message},
    )


# 3. GỌI REGISTRY BẰNG JWT USER
async def get_registry_data(client, path):
    try:
        response = await client.get(path)
        response.raise_for_status()
        return response.json()

    except httpx.HTTPStatusError as exc:
        code = exc.response.status_code

        if code in (401, 403):
            fail(code, "JWT không hợp lệ hoặc không có quyền.")

        if code == 404:
            fail(404, "Không tìm thấy dữ liệu thuộc tài khoản.")

        fail(502, f"Registry trả về HTTP {code}.")

    except (httpx.RequestError, ValueError):
        fail(503, "Không đọc được dữ liệu Registry.")


# 4. LẤY DEVICE VÀ MCU CỦA USER
async def load_device_context(token: str, device_id: int):
    async with httpx.AsyncClient(
        base_url=REGISTRY_BASE_URL,
        headers={"Authorization": f"Bearer {token}"},
        timeout=REGISTRY_TIMEOUT_SECONDS,
        follow_redirects=False,
    ) as client:

        catalog = await get_registry_data(client, "/api/device/catalog")
        if not isinstance(catalog, dict):
            fail(502, "Device Catalog không hợp lệ.")

        devices = catalog.get("devices")
        if not isinstance(devices, list):
            fail(502, "Device Catalog không hợp lệ.")

        device = next(
            (d for d in devices
             if d.get("deviceId") == device_id),
            None,
        )

        if device is None:
            fail(404, "Device không tồn tại hoặc không thuộc User.")

        mcu_id = device.get("microcontrollerId")
        gpio = device.get("gpio")

        if mcu_id is None or gpio is None:
            fail(409, "Device chưa liên kết với MCU/GPIO.")

        if device.get("syncStatus") != "synced":
            fail(409, "Device chưa đồng bộ, không thể điều khiển.")

        # Registry xác thực JWT và kiểm tra MCU thuộc User.
        mcu = await get_registry_data(client, f"/api/microcontroller/{mcu_id}")

        if not isinstance(mcu, dict):
            fail(502, "Dữ liệu MCU không hợp lệ.")

        if mcu.get("id") != mcu_id:
            fail(409, "MCU không khớp.")

        mcu_type = str(mcu.get("type") or "").strip().lower()
        if not mcu_type or any(c in mcu_type for c in "/+#"):
            fail(409, "Loại MCU không hợp lệ.")

        user_id = mcu.get("userId")

        if type(user_id) is not int or user_id <= 0:
            fail(409, "MCU chưa có chủ sở hữu hợp lệ.")

        if normalize_mac(device.get("macAddress", "")) != normalize_mac(mcu.get("macAddress", "")):
            fail(409, "MAC của Device và MCU không khớp.")

        return device, mcu

@asynccontextmanager
async def locked_device_context(token: str, device_id: int):

    # Khóa Device trước.
    async with get_device_lock(device_id):

        # Đọc để xác định MCU hiện tại.
        device, mcu = await load_device_context(token, device_id)

        mcu_id = mcu["id"]

        # Khóa MCU tương ứng.
        async with get_mcu_lock(mcu_id):

            # Đọc lại dữ liệu sau khi đã lấy khóa.
            device, mcu = await load_device_context(token, device_id)

            # Không dùng thông tin MCU cũ nếu liên kết thay đổi.
            if mcu["id"] != mcu_id:
                fail(409, "Binding đã thay đổi, hãy thử lại.")

            yield device, mcu

# 5. CHỜ MQTT RESPONSE KHỚP REQUEST
async def wait_response(
    mqtt,
    response_topic,
    expected_command,
    command_id,
    send_time,
    mac,
    gpio=None,
):
    async with asyncio.timeout(MQTT_TIMEOUT_SECONDS):
        async for message in mqtt.messages:
            if str(message.topic) != response_topic:
                continue

            # 1. chuyển message.payload thành json
            try:
                data = json.loads(message.payload)
            except (ValueError, TypeError):
                continue

            if not isinstance(data, dict):
                continue

            # kiểm tra các thông tin khác xem response có khớp ko
            if data.get("command") != expected_command:
                continue

            if data.get("command_id") != command_id:
                continue

            if data.get("send_time") != send_time:
                continue

            response_mac = data.get("microcontroller_id")

            if not isinstance(response_mac, str):
                continue

            try:
                if normalize_mac(response_mac) != mac:
                    continue
            except HTTPException:
                continue

            if gpio is not None and data.get("gpio") != gpio:
                continue

            return data

    fail(504, "Không nhận được MQTT RESPONSE.", "unknown")


# 6. GỬI MESSAGE MQTT
async def publish_command(mqtt, topic, payload):
    await mqtt.publish(
        topic,
        json.dumps(payload, ensure_ascii=False),
        qos=0,
        retain=False,
    )


# 7. ĐIỀU KHIỂN VÀ XÁC NHẬN TRẠNG THÁI
async def control_mqtt(
    mac_address: str,
    gpio: int,
    action: str,
    device_type: str,
    device_name: str,
    mcu_type: str,
):
    if not MQTT_HOST:
        fail(503, "Chưa cấu hình MQTT_HOST.")

    mac = normalize_mac(mac_address)

    mcu_type = mcu_type.strip().lower()

    base = f"iot/{mcu_type}/v1/{mac}"
    request_topic = f"{base}/FROM_SV/command"
    response_topic = f"{base}/FROM_{mcu_type.upper()}/command"

    command_id = uuid4().hex
    send_time = datetime.now(timezone.utc).isoformat(timespec="seconds")

    control_payload = {
        "command": "DEVICE_CONTROL_REQUEST",
        "command_id": command_id,
        "microcontroller_id": mac,
        "gpio": gpio,
        "send_time": send_time,
        "detail": {
            "action": action.lower(),
        },
    }

    attempted = False

    try:
        async with Client(
            hostname=MQTT_HOST,
            port=MQTT_PORT,
            username=MQTT_USERNAME or None,
            password=MQTT_PASSWORD or None,
            tls_context=(
                ssl.create_default_context() if MQTT_TLS else None
            ),
            identifier=f"nlp-control-{uuid4().hex[:12]}",
        ) as mqtt:

            # Subscribe trước khi publish để không mất ACK.
            await mqtt.subscribe(response_topic)

            attempted = True

            # 7.1. Gửi lệnh ON/OFF
            await publish_command(mqtt, request_topic, control_payload)

            # 7.2. ESP32 xác nhận đã nhận lệnh
            ack = await wait_response(
                mqtt,
                response_topic,
                "DEVICE_CONTROL_RESPONSE",
                command_id,
                send_time,
                mac,
                gpio,
            )

            if ack.get("status") != "success":
                fail(409, str(ack.get("message")or "ESP32 từ chối điều khiển."))

            # 7.3. Chờ DeviceTask xử lý Queue (tick 100ms).
            await asyncio.sleep(0.25)

            # 7.4. Đọc lại trạng thái thực tế từ DeviceTask.
            # Đây là truy vấn, không gửi lệnh ON/OFF lần hai.
            refresh_id = uuid4().hex
            refresh_time = datetime.now(timezone.utc).isoformat(timespec="seconds")

            refresh_payload = {
                "command": "REFRESH_DEVICE_REQUEST",
                "command_id": refresh_id,
                "microcontroller_id": mac,
                "send_time": refresh_time,
            }

            # tiếp tục gửi refresh
            await publish_command(mqtt, request_topic, refresh_payload)

            refreshed = await wait_response(
                mqtt,
                response_topic,
                "REFRESH_DEVICE_RESPONSE",
                refresh_id,
                refresh_time,
                mac,
            )

            if refreshed.get("status") != "success":
                fail(
                    409,
                    "ESP32 không đọc được trạng thái Device.",
                    "unknown",
                )

            gpios = refreshed.get("gpios")
            types = refreshed.get("device_types")
            names = refreshed.get("device_names")
            statuses = refreshed.get("device_status")

            if not all(
                isinstance(items, list)
                for items in [gpios, types, names, statuses]
            ):
                fail(502, "Dữ liệu REFRESH không hợp lệ.", "unknown")

            if not (
                len(gpios) == len(types)
                == len(names) == len(statuses)
            ):
                fail(502, "Danh sách REFRESH bị lệch.", "unknown")

            # 7.5. Tìm đúng Device theo GPIO + Type + Name
            actual_status = None

            for index, pin in enumerate(gpios):
                if (
                    pin == gpio
                    and types[index] == device_type
                    and names[index] == device_name
                ):
                    actual_status = str(statuses[index]).upper()
                    break

            if actual_status != action:
                fail(
                    409,
                    "Trạng thái ESP32 chưa khớp yêu cầu. "
                    "Cần kiểm tra trước khi điều khiển lại.",
                    "unknown",
                )

            return command_id, actual_status

    except TimeoutError:
        fail(
            504,
            "Hết thời gian chờ ESP32. "
            "Kết quả điều khiển chưa xác định.",
            "unknown" if attempted else "failed",
        )

    except (MqttError, OSError):
        fail(
            503,
            "Lỗi kết nối MQTT. "
            "Cần kiểm tra trạng thái thiết bị.",
            "unknown" if attempted else "failed",
        )


# 8. GHI TRẠNG THÁI VÀO REGISTRY
async def save_device_status(
    device_id: int,
    user_id: int,
    mcu_id: int,
    gpio: int,
    status: str,
):
    try:
        async with httpx.AsyncClient(
            base_url=REGISTRY_BASE_URL,
            timeout=REGISTRY_TIMEOUT_SECONDS,
            follow_redirects=False,
        ) as client:

            response = await client.put(
                f"/api/internal/devices/{device_id}/status",
                headers={
                    "X-Internal-Key": REGISTRY_INTERNAL_KEY,
                },
                json={
                    "userId": user_id,
                    "microcontrollerId": mcu_id,
                    "gpio": gpio,
                    "syncStatus": "synced",
                    "currentStatus": status,
                },
            )

            response.raise_for_status()
            return response.json()

    except (httpx.HTTPError, ValueError):
        fail(
            502,
            "ESP32 đã xác nhận trạng thái, nhưng Registry "
            "chưa xác nhận lưu dữ liệu.",
            "unknown",
        )


# Hàm chính
async def control_device(
    device_id: int,
    body: ManualControlRequest,
    token: str,
):
    if device_id <= 0:
        fail(422, "DeviceId không hợp lệ.")

    if not REGISTRY_BASE_URL or not REGISTRY_INTERNAL_KEY:
        fail(503, "Thiếu cấu hình Device Registry.")

    # Khóa Device và MCU tương ứng.
    async with locked_device_context(token, device_id) as (device, mcu):

        # Gửi MQTT và xác nhận trạng thái thực tế.
        command_id, actual_status = await control_mqtt(
            mcu["macAddress"],
            device["gpio"],
            body.action,
            device["deviceType"],
            device.get("deviceName") or "",
            mcu["type"],
        )

        # Cập nhật Registry sau khi ESP32 xác nhận.
        result = await save_device_status(
            device_id,
            mcu["userId"],
            mcu["id"],
            device["gpio"],
            actual_status,
        )

        return {
            "state": "success",
            "commandId": command_id,
            "deviceId": device_id,
            "currentStatus": actual_status,
            "registry": result,
        }