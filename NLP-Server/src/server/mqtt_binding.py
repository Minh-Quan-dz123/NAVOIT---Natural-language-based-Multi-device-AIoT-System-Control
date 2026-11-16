
import asyncio
import json
import re
import ssl

from datetime import datetime, timezone
from uuid import uuid4

from aiomqtt import Client, MqttError
from fastapi import HTTPException

from src.server.config import (
    MQTT_HOST,
    MQTT_PORT,
    MQTT_USERNAME,
    MQTT_PASSWORD,
    MQTT_TLS,
    MQTT_TIMEOUT_SECONDS,
)


# 1. CHUẨN HÓA ĐỊNH DANH MCU
def normalize_mac(value: str) -> str:
    if not isinstance(value, str):
        raise HTTPException(409, "MAC của MCU không hợp lệ.")

    mac = value.replace(":", "").replace("-", "").upper()

    if not re.fullmatch(r"[0-9A-F]{12}", mac):
        raise HTTPException(409, "MAC của MCU không hợp lệ.")

    return mac


# 2. GỬI LỆNH VÀ ĐỢI ACK TỪ ESP32
async def send_device_command(
    mac_address: str,
    command: str,
    gpio: int,
    device_type: str,
    device_name: str,
):
    if not MQTT_HOST:
        raise HTTPException(503, "Chưa cấu hình MQTT_HOST.")

    mac = normalize_mac(mac_address)

    # Topic giống firmware ESP32
    base = f"iot/esp32/v1/{mac}"

    request_topic = f"{base}/FROM_SV/command"
    response_topic = f"{base}/FROM_ESP32/command"

    command_id = uuid4().hex

    send_time = datetime.now(timezone.utc).isoformat(timespec="seconds")

    # Payload gửi tới ESP32
    payload = {
        "command": command,
        "command_id": command_id,
        "microcontroller_id": mac,
        "gpio": gpio,
        "device_type": device_type,
        "device_name": device_name,
        "send_time": send_time,
    }

    expected_response = command.replace("_REQUEST", "_RESPONSE")

    attempted = False

    try:
        async with asyncio.timeout(MQTT_TIMEOUT_SECONDS):

            async with Client(
                hostname=MQTT_HOST,
                port=MQTT_PORT,
                username=MQTT_USERNAME or None,
                password=MQTT_PASSWORD or None,
                tls_context=(
                    ssl.create_default_context()
                    if MQTT_TLS else None
                ),
                identifier=f"nlp-binding-{uuid4().hex[:12]}",
            ) as mqtt:

                # Subscribe trước khi publish
                await mqtt.subscribe(response_topic)

                # Gửi lệnh MQTT
                attempted = True

                await mqtt.publish(
                    request_topic,
                    json.dumps(payload, ensure_ascii=False),
                    qos=0,
                    retain=False,
                )

                # Chờ response tương ứng
                async for message in mqtt.messages:

                    if str(message.topic) != response_topic:
                        continue

                    try:
                        ack = json.loads(message.payload)
                    except (ValueError, TypeError):
                        continue

                    if not isinstance(ack, dict):
                        continue

                    # Kiểm tra loại lệnh
                    if ack.get("command") != expected_response:
                        continue

                    # Kiểm tra đúng request
                    if ack.get("command_id") != command_id:
                        continue

                    # Kiểm tra GPIO
                    if ack.get("gpio") != gpio:
                        continue

                    # Firmware trả lại send_time gốc
                    if ack.get("send_time") != send_time:
                        continue

                    # Kiểm tra MCU
                    response_mac = ack.get("microcontroller_id")

                    if not isinstance(response_mac, str):
                        continue

                    try:
                        if normalize_mac(response_mac) != mac:
                            continue
                    except HTTPException:
                        continue

                    # Response hợp lệ
                    return ack, command_id

    except (TimeoutError, MqttError, OSError) as exc:

        # Nếu đã thử publish, không thể chắc ESP32
        # đã thực hiện lệnh hay chưa.
        state = "unknown" if attempted else "failed"

        message = (
            "Không nhận được xác nhận chắc chắn từ ESP32; "
            "cần đối soát trước khi thử lại."
            if attempted else
            "Không thể kết nối/đăng ký nhận MQTT trước khi gửi lệnh."
        )

        raise HTTPException(
            status_code=(504 if isinstance(exc, TimeoutError) else 503),
            detail={"state": state, "message": message,},
        ) from exc

    raise HTTPException(
        504,
        {
            "state": "unknown",
            "message": "Không có ACK hợp lệ.",
        },
    )
