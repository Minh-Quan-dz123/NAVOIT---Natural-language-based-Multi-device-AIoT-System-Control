
import asyncio
import json
import ssl
import time

from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4
import httpx
from aiomqtt import Client, MqttError
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.server.auth import verify_jwt
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
from src.server.device_binding import lock as operation_lock
from src.server.device_control import load_device_context
from src.server.mqtt_binding import normalize_mac


router = APIRouter(
    prefix="/api/devices",
    tags=["Manual Schedule"],
)


# 1. REQUEST TẠO LỊCH
class CreateScheduleRequest(BaseModel):
    action: Literal["on", "off"]

    scheduledDelay: int | None = Field(default=None, ge=1, le=2147483647)
    duration: int | None = Field(default=None, ge=1, le=2147483647)

    # Unix timestamp UTC (giây).
    scheduledStartAt: int | None = Field(default=None, ge=1)
    scheduledEndAt: int | None = Field(default=None, ge=1)


def fail(code, message, state="failed"):
    raise HTTPException(
        status_code=code,
        detail={"state": state, "message": message},
    )


# 2. KIỂM TRA CÁC THAM SỐ THỜI GIAN
def validate_schedule(body: CreateScheduleRequest):
    now = int(time.time())

    delay = body.scheduledDelay
    duration = body.duration
    start = body.scheduledStartAt
    end = body.scheduledEndAt

    if all(value is None for value in (delay, duration, start, end)):
        fail(422, "Lệnh không có thời gian. Hãy dùng ON/OFF thủ công.")

    if delay is not None and start is not None:
        fail(422, "Không dùng đồng thời Delay và StartAt.")

    if duration is not None and end is not None:
        fail(422, "Không dùng đồng thời Duration và EndAt.")

    # EndAt đơn lẻ dễ bị hiểu nhầm là bật ngay và tắt lúc đó.
    # Với luồng thủ công, yêu cầu chỉ rõ điểm bắt đầu.
    if end is not None and delay is None and start is None:
        fail(422, "Cần chọn thời điểm bắt đầu khi dùng EndAt.")

    # Chừa thời gian cho MQTT và Registry.
    if start is not None and start <= now + 15:
        fail(422, "StartAt phải cách hiện tại trên 15 giây.")

    expected_start = start if start is not None else now + (delay or 0)

    if end is not None and end <= expected_start + 15:
        fail(422, "EndAt phải sau thời điểm bắt đầu trên 15 giây.")


# 3. KIỂM TRA DEVICE ĐÃ CÓ LỊCH CHƯA
async def check_existing_schedule(device_id: int, token: str):
    try:
        async with httpx.AsyncClient(
            base_url=REGISTRY_BASE_URL,
            headers={"Authorization": f"Bearer {token}"},
            timeout=REGISTRY_TIMEOUT_SECONDS,
            follow_redirects=False,
        ) as client:
            response = await client.get(
                f"/api/device/{device_id}/schedule"
            )

        if response.status_code == 404:
            return

        if response.status_code in (401, 403):
            fail(response.status_code, "Không có quyền truy cập Schedule.")

        if response.status_code == 200:
            fail(
                409,
                "Device đã có Schedule. Cần xử lý lịch cũ trước."
            )

        fail(502, f"Registry trả về HTTP {response.status_code}.")

    except httpx.RequestError:
        fail(503, "Không kết nối được Registry.")


# 4. GỬI DEVICE_CONTROL_REQUEST VÀ NHẬN RESPONSE
async def send_schedule_mqtt(
    mac_address: str,
    gpio: int,
    body: CreateScheduleRequest | None,
):
    if not MQTT_HOST:
        fail(503, "Chưa cấu hình MQTT_HOST.")

    mac = normalize_mac(mac_address)
    prefix = f"iot/esp32/v1/{mac}"

    request_topic = f"{prefix}/FROM_SV/command"
    response_topic = f"{prefix}/FROM_ESP32/command"

    command_id = uuid4().hex
    send_time = datetime.now(
        timezone.utc
    ).isoformat(timespec="seconds")

    
    # body = None nghĩa là hủy Schedule.
    detail = {
        "action": body.action if body is not None
        else "cancel_schedule"
    }

    # Chỉ gửi tham số thời gian khi tạo lịch.
    if body is not None:
        if body.duration is not None:
            detail["duration"] = body.duration

        if body.scheduledDelay is not None:
            detail["scheduled_delay"] = body.scheduledDelay

        if body.scheduledStartAt is not None:
            detail["scheduled_start_at"] = body.scheduledStartAt

        if body.scheduledEndAt is not None:
            detail["scheduled_end_at"] = body.scheduledEndAt

    payload = {
        "command": "DEVICE_CONTROL_REQUEST",
        "command_id": command_id,
        "microcontroller_id": mac,
        "gpio": gpio,
        "send_time": send_time,
        "detail": detail,
    }

    attempted = False

    try:
        async with asyncio.timeout(MQTT_TIMEOUT_SECONDS):
            async with Client(
                hostname=MQTT_HOST,
                port=MQTT_PORT,
                username=MQTT_USERNAME or None,
                password=MQTT_PASSWORD or None,
                tls_context=(
                    ssl.create_default_context() if MQTT_TLS else None
                ),
                identifier=f"nlp-schedule-{uuid4().hex[:12]}",
            ) as mqtt:

                # Subscribe trước khi gửi để nhận được ACK.
                await mqtt.subscribe(response_topic)

                attempted = True

                await mqtt.publish(
                    request_topic,
                    json.dumps(payload, ensure_ascii=False),
                    qos=0,
                    retain=False,
                )

                async for message in mqtt.messages:
                    if str(message.topic) != response_topic:
                        continue

                    try:
                        ack = json.loads(message.payload)
                    except (ValueError, TypeError):
                        continue

                    if not isinstance(ack, dict):
                        continue

                    if ack.get("command") != "DEVICE_CONTROL_RESPONSE":
                        continue

                    if ack.get("command_id") != command_id:
                        continue

                    if ack.get("gpio") != gpio:
                        continue

                    if ack.get("send_time") != send_time:
                        continue

                    response_mac = ack.get("microcontroller_id")

                    if not isinstance(response_mac, str):
                        continue

                    try:
                        if normalize_mac(response_mac) != mac:
                            continue
                    except HTTPException:
                        continue

                    # ACK thuộc đúng request.
                    return command_id, ack

    except (TimeoutError, MqttError, OSError) as exc:
        fail(
            504 if isinstance(exc, TimeoutError) else 503,
            (
                "Không xác định được ESP32 đã nhận lịch hay chưa. "
                "Cần đối soát, không thử lại ngay."
                if attempted else
                "Chưa gửi được lệnh MQTT."
            ),
            "unknown" if attempted else "failed",
        )

    fail(504, "Không nhận được ACK hợp lệ.", "unknown")


# 5. GHI NHẬN SCHEDULE TRONG REGISTRY SAU ACK
async def confirm_schedule(
    device_id: int,
    user_id: int,
    mcu_id: int,
    gpio: int,
    command_id: str,
    body: CreateScheduleRequest,
):
    payload = {
        "userId": user_id,
        "microcontrollerId": mcu_id,
        "gpio": gpio,
        "commandId": command_id,
        "action": body.action,
        "scheduledDelay": body.scheduledDelay,
        "duration": body.duration,
        "scheduledStartAt": body.scheduledStartAt,
        "scheduledEndAt": body.scheduledEndAt,
    }

    try:
        async with httpx.AsyncClient(
            base_url=REGISTRY_BASE_URL,
            timeout=REGISTRY_TIMEOUT_SECONDS,
            follow_redirects=False,
        ) as client:
            response = await client.post(
                f"/api/internal/devices/{device_id}/schedule/confirm",
                headers={"X-Internal-Key": REGISTRY_INTERNAL_KEY},
                json=payload,
            )

            response.raise_for_status()
            return response.json()

    except (httpx.HTTPError, ValueError):
        fail(
            502,
            "ESP32 đã xác nhận tiếp nhận lệnh nhưng Registry "
            "chưa xác nhận lưu Schedule. Cần đối soát.",
            "unknown",
        )


# 6. API TẠO LỊCH THỦ CÔNG
@router.post("/{device_id}/schedule")
async def create_schedule(device_id: int, body: CreateScheduleRequest, token: str = Depends(verify_jwt),):
    if device_id <= 0:
        fail(422, "DeviceId không hợp lệ.")

    if not REGISTRY_BASE_URL or not REGISTRY_INTERNAL_KEY:
        fail(503, "Thiếu cấu hình Device Registry.")

    validate_schedule(body)

    async with operation_lock:
        # 6.1. Registry xác minh JWT, quyền sở hữu,
        # binding và trạng thái đồng bộ.
        device, mcu = await load_device_context( token, device_id)

        # 6.2. Một Device chỉ có một Schedule.
        await check_existing_schedule(device_id, token)

        # 6.3. Gửi lịch xuống ESP32.
        command_id, ack = await send_schedule_mqtt( mcu["macAddress"], device["gpio"], body,)

        # 6.4. ESP32 từ chối -> không lưu Schedule.
        if ack.get("status") != "success":
            fail(409, str(ack.get("message") or "ESP32 từ chối lịch."))

        # 6.5. ACK success -> gọi Internal API lưu Schedule.
        saved = await confirm_schedule(
            device_id,
            mcu["userId"],
            mcu["id"],
            device["gpio"],
            command_id,
            body,
        )

        return {
            "state": "success",
            "commandId": command_id,
            "deviceId": device_id,
            "schedule": saved,
        }



# 7. LẤY SCHEDULE HIỆN TẠI CỦA USER
async def load_schedule(device_id: int, token: str):
    try:
        async with httpx.AsyncClient(
            base_url=REGISTRY_BASE_URL,
            headers={"Authorization": f"Bearer {token}"},
            timeout=REGISTRY_TIMEOUT_SECONDS,
            follow_redirects=False,
        ) as client:
            response = await client.get(
                f"/api/device/{device_id}/schedule"
            )

    except httpx.RequestError:
        fail(503, "Không kết nối được Device Registry.")

    if response.status_code == 404:
        fail(404, "Device không có Schedule.")

    if response.status_code in (401, 403):
        fail(response.status_code, "Không có quyền xem Schedule.")

    if response.status_code != 200:
        fail(502, "Registry trả về lỗi khi đọc Schedule.")

    try:
        schedule = response.json()
    except ValueError:
        fail(502, "Dữ liệu Schedule không hợp lệ.")

    if not isinstance(schedule, dict):
        fail(502, "Dữ liệu Schedule không hợp lệ.")

    return schedule


# 8. GHI NHẬN HỦY SAU ACK CỦA ESP32
async def confirm_cancel_schedule(
    device_id: int,
    user_id: int,
    mcu_id: int,
    gpio: int,
    schedule_id: int,
    command_id: str,
):
    try:
        async with httpx.AsyncClient(
            base_url=REGISTRY_BASE_URL,
            timeout=REGISTRY_TIMEOUT_SECONDS,
            follow_redirects=False,
        ) as client:

            response = await client.post(
                f"/api/internal/devices/{device_id}/schedule/cancel-confirm",
                headers={
                    "X-Internal-Key": REGISTRY_INTERNAL_KEY,
                },
                json={
                    "userId": user_id,
                    "microcontrollerId": mcu_id,
                    "gpio": gpio,
                    "scheduleId": schedule_id,
                    "commandId": command_id,
                },
            )

            response.raise_for_status()

            # Internal API trả HTTP 204, không có body.
            return

    except httpx.HTTPError:
        fail(
            502,
            "ESP32 đã tiếp nhận lệnh hủy nhưng Registry "
            "chưa xác nhận xóa Schedule. Cần đối soát.",
            "unknown",
        )


# 9. API HỦY SCHEDULE THỦ CÔNG
@router.delete("/{device_id}/schedule")
async def cancel_schedule(
    device_id: int,
    token: str = Depends(verify_jwt),
):
    if device_id <= 0:
        fail(422, "DeviceId không hợp lệ.")

    if not REGISTRY_BASE_URL or not REGISTRY_INTERNAL_KEY:
        fail(503, "Thiếu cấu hình Device Registry.")

    async with operation_lock:

        # 9.1. Registry xác minh JWT và Device/MCU thuộc User.
        device, mcu = await load_device_context(
            token, device_id
        )

        # 9.2. Đọc lịch hiện tại.
        schedule = await load_schedule(device_id, token)

        schedule_id = schedule.get("id")

        if type(schedule_id) is not int or schedule_id <= 0:
            fail(502, "ScheduleId không hợp lệ.")

        # Chỉ hủy lịch đã được ESP32 tiếp nhận.
        # Trạng thái pending/unknown phải đối soát riêng.
        if schedule.get("syncStatus") != "acknowledged":
            fail(
                409,
                "Schedule chưa ở trạng thái acknowledged. "
                "Cần đối soát trước khi hủy."
            )

        # 9.3. Gửi cancel_schedule tới ESP32.
        command_id, ack = await send_schedule_mqtt(
            mcu["macAddress"],
            device["gpio"],
            None,
        )

        # 9.4. ESP32 từ chối -> không sửa Registry.
        if ack.get("status") != "success":
            fail(
                409,
                str(ack.get("message") or "ESP32 từ chối hủy lịch.")
            )

        # 9.5. ESP32 tiếp nhận -> xác nhận hủy trong Registry.
        await confirm_cancel_schedule(
            device_id,
            mcu["userId"],
            mcu["id"],
            device["gpio"],
            schedule_id,
            command_id,
        )

        return {
            "state": "success",
            "deviceId": device_id,
            "scheduleId": schedule_id,
            "commandId": command_id,
            "message": (
                "ESP32 đã tiếp nhận lệnh hủy; "
                "Registry đã xóa Schedule."
            ),
        }

