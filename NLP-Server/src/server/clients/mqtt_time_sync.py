
import asyncio
import json
import logging
import re
import ssl
import time
from uuid import uuid4

from aiomqtt import Client, MqttError

from src.server.config import (
    MQTT_HOST,
    MQTT_PORT,
    MQTT_USERNAME,
    MQTT_PASSWORD,
    MQTT_TLS,
)


logger = logging.getLogger("uvicorn.error")

REQUEST_TOPIC = "iot/esp32/v1/+/FROM_ESP32/configuration"


# 1. CHUẨN HÓA MAC
def normalize_time_mac(value):
    if not isinstance(value, str):
        return None

    mac = value.replace(":", "").replace("-", "").upper()

    if not re.fullmatch(r"[0-9A-F]{12}", mac):
        return None

    return mac


# 2. XỬ LÝ MESSAGE TỪ ESP32
async def process_time_message(mqtt, message, pending_acks):
    topic = str(message.topic)
    parts = topic.split("/")

    # Kiểm tra cấu trúc topic
    if len(parts) != 6 or parts[:3] != ["iot", "esp32", "v1"]:
        return

    if parts[4:] != ["FROM_ESP32", "configuration"]:
        return

    mac = normalize_time_mac(parts[3])
    if mac is None:
        return

    if len(message.payload) > 2048:
        logger.warning("MQTT time: payload quá lớn từ %s", mac)
        return

    # Parse JSON
    try:
        data = json.loads(message.payload)
    except (ValueError, UnicodeError, TypeError):
        logger.warning("MQTT time: JSON không hợp lệ từ %s", mac)
        return

    if not isinstance(data, dict):
        return

    # Kiểm tra MAC trong payload có khớp topic
    if normalize_time_mac(data.get("microcontroller_id")) != mac:
        logger.warning(
            "MQTT time: microcontroller_id không khớp topic %s",
            mac,
        )
        return

    command_id = data.get("command_id")

    if not isinstance(command_id, str) or not (0 < len(command_id) <= 128):
        return

    command = data.get("command")

    # 3. ESP32 YÊU CẦU ĐỒNG BỘ THỜI GIAN
    if command == "REFRESH_TIME_REQUEST":

        response = {
            "command": "REFRESH_TIME_RESPONSE",
            "command_id": command_id,
            "microcontroller_id": mac,
            "current_time": int(time.time()),
        }

        response_topic = (f"iot/esp32/v1/{mac}/FROM_SV/configuration")

        await mqtt.publish(
            response_topic,
            json.dumps(response),
            qos=0,
            retain=False,
        )

        pending_acks[mac] = command_id

        logger.info(
            "MQTT time: đã gửi thời gian tới ESP32 %s",
            mac,
        )

    # 4. ESP32 XÁC NHẬN KẾT QUẢ
    elif command == "REFRESH_TIME_ACK":

        if pending_acks.get(mac) != command_id:
            logger.warning(
                "MQTT time: ACK không khớp yêu cầu từ %s",
                mac,
            )
            return

        del pending_acks[mac]

        if data.get("status") == "success":
            logger.info(
                "MQTT time: ESP32 %s xác nhận đồng bộ thành công",
                mac,
            )
        else:
            logger.warning(
                "MQTT time: ESP32 %s báo đồng bộ thất bại: %s",
                mac,
                data.get("message"),
            )


# 5. MQTT LISTENER CHẠY LIÊN TỤC
async def listen_time_sync():

    while True:
        try:
            async with Client(
                hostname=MQTT_HOST,
                port=MQTT_PORT,
                username=MQTT_USERNAME or None,
                password=MQTT_PASSWORD or None,
                tls_context=(
                    ssl.create_default_context()
                    if MQTT_TLS else None
                ),
                identifier=f"nlp-time-{uuid4().hex[:12]}",
            ) as mqtt:

                await mqtt.subscribe(REQUEST_TOPIC)

                logger.info(
                    "MQTT time: đang lắng nghe %s",
                    REQUEST_TOPIC,
                )

                pending_acks = {}

                async for message in mqtt.messages:
                    await process_time_message(
                        mqtt,
                        message,
                        pending_acks,
                    )

        except (MqttError, OSError) as exc:
            logger.warning(
                "MQTT time: mất kết nối (%s)",
                exc,
            )

        except Exception:
            logger.exception(
                "MQTT time: lỗi ngoài dự kiến"
            )

        # Đợi 5 giây trước khi kết nối lại
        await asyncio.sleep(5)
