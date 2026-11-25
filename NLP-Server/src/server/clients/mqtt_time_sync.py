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

from src.server.services.device_auto_restore import restore_mcu


logger = logging.getLogger("uvicorn.error")

REQUEST_TOPIC = "iot/+/v1/+/+/configuration"


# 1. CHUẨN HÓA MAC
def normalize_time_mac(value):
    if not isinstance(value, str):
        return None

    mac = value.replace(":", "").replace("-", "").upper()

    if not re.fullmatch(r"[0-9A-F]{12}", mac):
        return None

    return mac


# 2. GỬI KẾT QUẢ KHÔI PHỤC VỀ MCU
async def send_restore_response(
    mqtt, mcu_type, mac, command_id, status, message
):
    response = {
        "command": "RESTORE_STATE_RESPONSE",
        "command_id": command_id,
        "microcontroller_id": mac,
        "status": status,
        "message": message,
    }

    response_topic = f"iot/{mcu_type}/v1/{mac}/FROM_SV/configuration"

    await mqtt.publish(
        response_topic,
        json.dumps(response, ensure_ascii=False),
        qos=0,
        retain=False,
    )


# 3. KHÔI PHỤC TRONG TASK RIÊNG
async def run_restore(
    mqtt, mcu_type, mac, command_id, restoring, restored
):
    try:
        try:
            # Gọi service khôi phục Device/GPIO và Schedule.
            result = await restore_mcu(mac, mcu_type)

            if result.get("status") != "success":
                raise RuntimeError(
                    "Service chưa khôi phục thành công."
                )

            # Ghi nhớ command_id thành công.
            # Nếu MCU gửi lại cùng request,
            # không cần khôi phục lần nữa.
            restored[(mcu_type, mac)] = command_id

            status = "success"
            message = result.get(
                "message",
                "Devices and schedules restored",
            )

            logger.info(
                "MQTT restore: MCU %s khôi phục thành công",
                mac,
            )

        except asyncio.CancelledError:
            raise

        except Exception:
            logger.exception(
                "MQTT restore: lỗi khôi phục MCU %s",
                mac,
            )

            status = "error"
            message = "Restore failed; will retry"

        # Chỉ gửi success sau khi service hoàn tất.
        await send_restore_response(
            mqtt,
            mcu_type,
            mac,
            command_id,
            status,
            message,
        )

    except asyncio.CancelledError:
        raise

    except (MqttError, OSError):
        logger.warning(
            "MQTT restore: không gửi được kết quả tới %s",
            mac,
        )

    finally:
        # Cho phép MCU gửi request mới sau khi kết thúc.
        restoring.pop((mcu_type, mac), None)


# 4. XỬ LÝ MESSAGE TỪ MCU
async def process_time_message(
    mqtt, message, pending_acks, restoring, restored
):
    topic = str(message.topic)
    parts = topic.split("/")

    # Kiểm tra cấu trúc topic.
    if len(parts) != 6 or parts[0] != "iot" or parts[2] != "v1":
        return

    mcu_type = parts[1].strip().lower()

    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", mcu_type):
        return

    if parts[4:] != [f"FROM_{mcu_type.upper()}", "configuration"]:
        return

    mac = normalize_time_mac(parts[3])

    if mac is None:
        return

    mcu_key = (mcu_type, mac)

    if len(message.payload) > 2048:
        logger.warning(
            "MQTT time: payload quá lớn từ %s",
            mac,
        )
        return

    # Parse JSON.
    try:
        data = json.loads(message.payload)

    except (ValueError, UnicodeError, TypeError):
        logger.warning(
            "MQTT time: JSON không hợp lệ từ %s",
            mac,
        )
        return

    if not isinstance(data, dict):
        return

    # Kiểm tra MAC trong payload có khớp topic.
    if normalize_time_mac(
        data.get("microcontroller_id")
    ) != mac:

        logger.warning(
            "MQTT time: microcontroller_id không khớp topic %s",
            mac,
        )
        return

    command_id = data.get("command_id")

    if (
        not isinstance(command_id, str)
        or not (0 < len(command_id) <= 128)
    ):
        return

    command = data.get("command")

    # 4.1. MCU YÊU CẦU ĐỒNG BỘ THỜI GIAN
    if command == "REFRESH_TIME_REQUEST":

        response = {
            "command": "REFRESH_TIME_RESPONSE",
            "command_id": command_id,
            "microcontroller_id": mac,
            "current_time": int(time.time()),
        }

        response_topic = f"iot/{mcu_type}/v1/{mac}/FROM_SV/configuration"

        await mqtt.publish(
            response_topic,
            json.dumps(response),
            qos=0,
            retain=False,
        )

        pending_acks[mcu_key] = command_id

        logger.info(
            "MQTT time: đã gửi thời gian tới MCU %s",
            mac,
        )

    # 4.2. MCU XÁC NHẬN ĐỒNG BỘ THỜI GIAN
    elif command == "REFRESH_TIME_ACK":

        if pending_acks.get(mcu_key) != command_id:
            logger.warning(
                "MQTT time: ACK không khớp yêu cầu từ %s",
                mac,
            )
            return

        del pending_acks[mcu_key]

        if data.get("status") == "success":
            logger.info(
                "MQTT time: MCU %s xác nhận đồng bộ thành công",
                mac,
            )
        else:
            logger.warning(
                "MQTT time: MCU %s báo đồng bộ thất bại: %s",
                mac,
                data.get("message"),
            )

    # 4.3. MCU YÊU CẦU KHÔI PHỤC SAU REBOOT
    elif command == "RESTORE_STATE_REQUEST":

        # Trường hợp 1:
        # Request này đã khôi phục thành công trước đó.
        # Chỉ gửi lại response, không chạy lại service.
        if restored.get(mcu_key) == command_id:

            await send_restore_response(
                mqtt,
                mcu_type,
                mac,
                command_id,
                "success",
                "Devices and schedules restored",
            )
            return

        # Trường hợp 2:
        # MCU đang có một tiến trình khôi phục.
        running = restoring.get(mcu_key)

        if running is not None:

            old_command_id, task = running

            if not task.done():

                # Cùng request đang chạy.
                # Không tạo task trùng lặp.
                if old_command_id == command_id:
                    return

                # Request khác đang chạy.
                # Báo error để MCU thử lại.
                await send_restore_response(
                    mqtt,
                    mcu_type,
                    mac,
                    command_id,
                    "error",
                    "Another restore is running",
                )
                return

        # Trường hợp 3:
        # Tạo task khôi phục mới.
        # Không chặn MQTT listener.
        task = asyncio.create_task(
            run_restore(
                mqtt,
                mcu_type,
                mac,
                command_id,
                restoring,
                restored,
            )
        )

        restoring[mcu_key] = (command_id, task)

        logger.info(
            "MQTT restore: bắt đầu khôi phục MCU %s",
            mac,
        )


# 5. MQTT LISTENER CHẠY LIÊN TỤC
async def listen_time_sync():

    # Lưu request khôi phục thành công.
    # Giữ lại khi MQTT listener reconnect.
    restored = {}

    while True:

        # Các task khôi phục của kết nối MQTT hiện tại.
        restoring = {}

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
                        restoring,
                        restored,
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

        finally:
            # Hủy các task dùng kết nối MQTT cũ.
            # MCU sẽ retry nếu chưa được xác nhận.
            tasks = [
                item[1]
                for item in restoring.values()
            ]

            for task in tasks:
                task.cancel()

            if tasks:
                await asyncio.gather(
                    *tasks,
                    return_exceptions=True,
                )

        # Đợi 5 giây trước khi kết nối lại.
        await asyncio.sleep(5)