import asyncio
import time
import ssl
from datetime import datetime, timezone
from uuid import uuid4

import httpx
from aiomqtt import Client
from fastapi import HTTPException

from src.server.config import (
    REGISTRY_BASE_URL,
    MQTT_HOST,
    MQTT_PORT,
    MQTT_USERNAME,
    MQTT_PASSWORD,
    MQTT_TLS,
    MQTT_TIMEOUT_SECONDS,
    REGISTRY_TIMEOUT_SECONDS,
)

from src.server.clients.mqtt_binding import normalize_mac
from src.server.services.operation_locks import get_mcu_lock
from src.server.services.device_control import (
    publish_command,
    wait_response,
)
from src.server.services.device_schedule import (
    CreateScheduleRequest,
    send_schedule_mqtt,
)


# 1. ĐỌC DỮ LIỆU PUBLIC API CỦA REGISTRY
async def registry_get(client, path, allow_not_found=False):
    response = await client.get(path)

    if allow_not_found and response.status_code == 404:
        return None

    response.raise_for_status()
    return response.json()


# 2. LẤY SNAPSHOT SCHEDULE CỦA MỘT ESP32
async def read_schedule_snapshot(mcu):
    mac = normalize_mac(mcu["macAddress"])
    mcu_type = str(mcu["type"]).strip().lower()
    prefix = f"iot/{mcu_type}/v1/{mac}"
    command_id = uuid4().hex
    send_time = datetime.now(timezone.utc).isoformat(timespec="seconds")

    payload = {
        "command": "REFRESH_SCHEDULE_REQUEST",
        "command_id": command_id,
        "microcontroller_id": mac,
        "send_time": send_time,
    }

    async with asyncio.timeout(MQTT_TIMEOUT_SECONDS + 5):
        async with Client(
            hostname=MQTT_HOST,
            port=MQTT_PORT,
            username=MQTT_USERNAME or None,
            password=MQTT_PASSWORD or None,
            tls_context=(
                ssl.create_default_context()
                if MQTT_TLS else None
            ),
            identifier=f"nlp-schedule-sync-{uuid4().hex[:12]}",
        ) as mqtt:

            response_topic = f"{prefix}/FROM_{mcu_type.upper()}/command"
            request_topic = f"{prefix}/FROM_SV/command"

            await mqtt.subscribe(response_topic)

            await publish_command(
                mqtt,
                request_topic,
                payload,
            )

            response = await wait_response(
                mqtt,
                response_topic,
                "REFRESH_SCHEDULE_RESPONSE",
                command_id,
                send_time,
                mac,
            )

    if response.get("status") != "success":
        raise ValueError("MCU không trả Schedule thành công.")

    # kiểm tra thời gian trên MCU đã được đồng bộ chưa
    if type(response.get("time_valid")) is not bool:
        raise ValueError("Thiếu trạng thái đồng bộ thời gian.")
    if type(response.get("current_time")) is not int:
        raise ValueError("Thời gian ESP32 không hợp lệ.")

    rows = response.get("schedules")
    if not isinstance(rows, list):
        raise ValueError("Danh sách Schedule không hợp lệ.")

    schedules = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Schedule snapshot không hợp lệ.")

        gpio = row.get("gpio")

        if type(gpio) is not int or gpio < 0:
            raise ValueError("GPIO không hợp lệ.")

        if gpio in schedules:
            raise ValueError("ESP32 trả về GPIO trùng.")

        if type(row.get("active")) is not bool:
            raise ValueError("Trạng thái Schedule không hợp lệ.")

        phase = row.get("phase")

        if type(phase) is not int or phase not in (1, 2, 3):
            raise ValueError("Phase không hợp lệ.")

        if row["active"] != (phase in (1, 2)):
            raise ValueError("Active và Phase không khớp.")

        if row["active"]:
            start = row.get("start_at")
            end = row.get("end_at")

            if (
                type(start) is not int
                or type(end) is not int
                or start <= 0
                or end < start
            ):
                raise ValueError("Mốc thời gian không hợp lệ.")

            if row.get("start_status") not in ("on", "off"):
                raise ValueError("StartStatus không hợp lệ.")

            if row.get("end_status") not in ("on", "off"):
                raise ValueError("EndStatus không hợp lệ.")

        schedules[gpio] = row

    # Kiểm tra đồng hồ ESP32 không lệch quá 10 giây.
    clock_ok = (
        response["time_valid"]
        and abs(response["current_time"] - int(time.time())) <= 10
    )

    return schedules, clock_ok


# 3. chuyển thông tin Schedule lưu trong Database thành các mốc thời 
# gian và trạng thái mà ESP32 dự kiến phải thực hiện.
def expected_schedule(schedule):
    action = str(schedule.get("action", "")).lower()

    if action not in ("on", "off"):
        raise ValueError("Action của Schedule không hợp lệ.")

    expires_at = schedule.get("expiresAt")
    if type(expires_at) is not int or expires_at <= 0:
        raise ValueError("ExpiresAt không hợp lệ.")

    duration = schedule.get("duration")
    delay = schedule.get("scheduledDelay")
    start_at = schedule.get("scheduledStartAt")
    end_at = schedule.get("scheduledEndAt")

    for value in (duration, delay, start_at, end_at):
        if value is not None and (type(value) is not int or value < 0):
            raise ValueError("Tham số thời gian không hợp lệ.")

    # Lịch có Duration/EndAt có hai hành động:
    # bắt đầu là action, kết thúc là đảo action.
    has_window = duration is not None or end_at is not None

    expected_start = None

    if has_window:
        if start_at is not None:
            expected_start = start_at
        elif duration is not None:
            expected_start = expires_at - duration

    if has_window:
        end_status = "off" if action == "on" else "on"
    else:
        end_status = action

    return {
        "expiresAt": expires_at,
        "startAt": expected_start,
        "startStatus": action if has_window else None,
        "endStatus": end_status,
        "hasWindow": has_window,
    }


# 4. SO SÁNH LỊCH THỰC TẾ VÀ LỊCH CHUẨN
def compare_schedule(schedule, actual):
    expected = expected_schedule(schedule)

    if not actual["active"]:
        return "missing"

    # Với Delay, thời điểm gửi MQTT và xử lý trên ESP32
    # có thể lệch vài giây.
    if abs(actual["end_at"] - expected["expiresAt"]) > 5:
        return "conflict"

    if actual["end_status"] != expected["endStatus"]:
        return "conflict"

    if expected["hasWindow"]:
        if actual["start_status"] != expected["startStatus"]:
            return "conflict"

        # Delay + EndAt không lưu mốc bắt đầu tuyệt đối
        # trong Registry nên chưa xác minh đủ.
        if expected["startAt"] is None:
            return "uncertain"

        if abs(actual["start_at"] - expected["startAt"]) > 5:
            return "conflict"

    return "matched"


# 5. CHUYỂN SCHEDULE CŨ SANG THỜI ĐIỂM TUYỆT ĐỐI
def build_recovery_command(schedule):
    expected = expected_schedule(schedule)

    now = int(time.time())
    expires_at = expected["expiresAt"]

    if expires_at <= now + 15:
        return None

    action = schedule["action"].lower()

    if not expected["hasWindow"]:
        # Delay hoặc StartAt đơn lẻ.
        # Hành động cần thực hiện tại ExpiresAt.
        return CreateScheduleRequest(
            action=action,
            scheduledStartAt=expires_at,
        )

    start_at = expected["startAt"]

    # Không khôi phục Delay + EndAt khi chưa biết
    # thời điểm bắt đầu chính xác.
    if start_at is None or start_at <= now + 15:
        return None

    duration = schedule.get("duration")
    end_at = schedule.get("scheduledEndAt")

    if duration is not None:
        if duration <= 0:
            return None

        if start_at + duration != expires_at:
            return None

        return CreateScheduleRequest(
            action=action,
            scheduledStartAt=start_at,
            duration=duration,
        )

    if end_at is not None:
        if end_at != expires_at or end_at <= start_at:
            return None

        return CreateScheduleRequest(
            action=action,
            scheduledStartAt=start_at,
            scheduledEndAt=end_at,
        )

    return None


# 6. ĐỒNG BỘ MỘT MCU
async def sync_one_mcu(mcu, devices, client, apply):
    result = {
        "mcuId": mcu.get("id"),
        "state": "success",
        "message": "",
        "items": [],
    }

    try:
        mcu_type = str(mcu.get("type") or "").strip().lower()
        if not mcu_type or any(c in mcu_type for c in "/+#"):
            raise ValueError("Loại MCU không hợp lệ.")

        snapshot, clock_ok = await read_schedule_snapshot(mcu)

        mcu_id = mcu["id"]

        desired = [
            device for device in devices
            if device.get("microcontrollerId") == mcu_id
        ]

        desired_gpios = set()

        for device in desired:
            device_id = device.get("deviceId")
            gpio = device.get("gpio")

            if (
                type(device_id) is not int
                or type(gpio) is not int
                or gpio in desired_gpios
            ):
                raise ValueError("Device Catalog không hợp lệ.")

            desired_gpios.add(gpio)

            item = {
                "deviceId": device_id,
                "gpio": gpio,
                "state": "",
                "message": "",
            }

            # 6.1. Không khôi phục lịch nếu binding sai.
            actual = snapshot.get(gpio)

            if (
                actual is None
                or device.get("syncStatus") != "synced"
            ):
                item["state"] = "device_mismatch"
                item["message"] = (
                    "Cần đồng bộ Device/GPIO trước."
                )
                result["items"].append(item)
                continue

            # 6.2. Lấy Schedule trong Registry.
            schedule = await registry_get(
                client,
                f"/api/device/{device_id}/schedule",
                allow_not_found=True,
            )

            # Không có lịch trên Registry.
            if schedule is None:
                if actual["active"]:
                    item["state"] = "orphan"
                    item["message"] = (
                        "ESP32 còn lịch nhưng Registry không có. "
                        "Chưa tự hủy."
                    )
                else:
                    item["state"] = "matched"
                    item["message"] = "Hai bên đều không có lịch."

                result["items"].append(item)
                continue

            # 6.3. Lịch hết hạn.
            if (
                schedule.get("isExpired") is True
                or schedule.get("expiresAt", 0) <= int(time.time())
            ):
                item["state"] = "expired_unverified"
                item["message"] = (
                    "Schedule đã hết hạn theo Registry, "
                    "chưa xác minh đã thực thi xong."
                )
                result["items"].append(item)
                continue

            # 6.4. So sánh lịch đang có.
            if actual["active"]:
                state = compare_schedule(schedule, actual)

                item["state"] = state

                if state == "matched":
                    item["message"] = "Schedule đang khớp."
                elif state == "uncertain":
                    item["message"] = (
                        "Thiếu thông tin để xác minh đầy đủ."
                    )
                else:
                    item["message"] = (
                        "Schedule đang khác Registry. "
                        "Chưa tự ghi đè."
                    )

                result["items"].append(item)
                continue

            # 6.5. Lịch thiếu trên ESP32.
            command = build_recovery_command(schedule)

            if command is None:
                item["state"] = "manual"
                item["message"] = (
                    "Không thể khôi phục lịch an toàn "
                    "từ các thông tin hiện có."
                )
                result["items"].append(item)
                continue

            if not apply:
                item["state"] = "recoverable"
                item["message"] = "Có thể khôi phục Schedule."
                result["items"].append(item)
                continue

            if not clock_ok:
                item["state"] = "manual"
                item["message"] = (
                    "Đồng hồ ESP32 chưa chính xác. "
                    "Không tạo Schedule."
                )
                result["items"].append(item)
                continue

            # 6.6. Gửi lịch xuống ESP32.
            # KHÔNG gọi Registry Confirm, vì lịch đã tồn tại.
            try:
                _, ack, _ = await send_schedule_mqtt(
                    mcu["macAddress"],
                    gpio,
                    command,
                    mcu["type"],
                )

                if ack.get("status") != "success":
                    item["state"] = "failed"
                    item["message"] = str(
                        ack.get("message") or "ESP32 từ chối lịch."
                    )
                else:
                    # Chờ DeviceTask lấy lệnh từ FreeRTOS Queue.
                    await asyncio.sleep(0.3)

                    new_snapshot, _ = await read_schedule_snapshot(mcu)
                    verified = new_snapshot.get(gpio)

                    if (
                        verified is not None
                        and compare_schedule(schedule, verified)
                            == "matched"
                    ):
                        item["state"] = "restored"
                        item["message"] = (
                            "Đã khôi phục và xác minh Schedule."
                        )
                    else:
                        item["state"] = "unknown"
                        item["message"] = (
                            "ESP32 đã nhận lệnh nhưng chưa xác minh "
                            "được Schedule. Không tự gửi lại."
                        )

            except Exception as exc:
                # Sau khi bắt đầu gửi MQTT, không thể kết luận
                # lệnh chưa được thực hiện.
                item["state"] = "unknown"

                if isinstance(exc, HTTPException):
                    item["message"] = str(exc.detail)
                else:
                    item["message"] = (
                        "Không xác minh được kết quả khôi phục. "
                        "Không tự gửi lại."
                    )

            result["items"].append(item)

        # 6.7. Phát hiện GPIO thừa trên firmware.
        for gpio, actual in snapshot.items():
            if gpio not in desired_gpios and actual["active"]:
                result["items"].append({
                    "deviceId": None,
                    "gpio": gpio,
                    "state": "orphan",
                    "message": (
                        "GPIO không có trong Registry "
                        "nhưng đang giữ Schedule."
                    ),
                })

        # 6.8. Tổng hợp kết quả.
        problems = [
            item for item in result["items"]
            if item["state"] not in ("matched", "restored")
        ]

        if problems:
            result["state"] = "partial"
            result["message"] = (
                f"Còn {len(problems)} Schedule cần xử lý."
            )
        else:
            result["message"] = (
                "Đã đối chiếu tất cả Schedule của MCU."
            )

    except Exception as exc:
        result["state"] = "failed"

        if isinstance(exc, HTTPException):
            result["message"] = str(exc.detail)
        elif isinstance(
            exc,
            (ValueError, TimeoutError, httpx.HTTPError)
        ):
            result["message"] = str(exc) or "Không đọc được Schedule."
        else:
            result["message"] = "Lỗi khi đồng bộ Schedule."

    return result


# 7. ĐỒNG BỘ TẤT CẢ MCU CỦA USER
async def sync_all_schedules(token, apply=False):

    if not REGISTRY_BASE_URL or not MQTT_HOST:
        raise HTTPException(
            503,
            "Thiếu cấu hình Registry hoặc MQTT.",
        )

    try:

        async with httpx.AsyncClient(
            base_url=REGISTRY_BASE_URL,
            headers={"Authorization": f"Bearer {token}"},
            timeout=REGISTRY_TIMEOUT_SECONDS,
            follow_redirects=False,
        ) as client:

            # 1. Lấy danh sách MCU của User.
            mcus = await registry_get(client, "/api/microcontroller",)
            if not isinstance(mcus, list):
                raise ValueError("Danh sách MCU không hợp lệ.")
            for mcu in mcus:
                if not isinstance(mcu, dict):
                    raise ValueError( "Dữ liệu MCU không hợp lệ.")

            # 2. Hàm đồng bộ lịch cho một MCU.
            async def run_sync(mcu):
                mcu_id = mcu.get("id")

                failed_result = {
                    "mcuId": mcu_id,
                    "state": "failed",
                    "message": "",
                    "items": [],
                }

                if type(mcu_id) is not int or mcu_id <= 0:
                    failed_result["message"] = ("MCU ID không hợp lệ.")
                    return failed_result

                operation_started = False

                try:

                    # Chỉ khóa MCU hiện tại.
                    async with get_mcu_lock(mcu_id):

                        # 3. Đọc lại thông tin MCU.
                        fresh_mcu = await registry_get(
                            client,
                            f"/api/microcontroller/{mcu_id}",
                            allow_not_found=True,
                        )

                        if not isinstance(fresh_mcu, dict):
                            failed_result["message"] = "MCU không còn thuộc User."
                            return failed_result

                        if fresh_mcu.get("id") != mcu_id:
                            raise ValueError("MCU ID không khớp.")

                        # 4. Đọc Catalog mới nhất (lấy toàn bộ Device thuộc User hiện tại,)
                        catalog = await registry_get(
                            client,
                            "/api/device/catalog",
                        )

                        if (
                            not isinstance(catalog, dict)
                            or not isinstance( catalog.get("devices"), list)
                        ):
                            raise ValueError("Device Catalog không hợp lệ.")

                        # 5. Đồng bộ Schedule của MCU.
                        operation_started = True

                        return await sync_one_mcu(
                            fresh_mcu,
                            catalog["devices"],
                            client,
                            apply,
                        )

                except HTTPException as exc:

                    if operation_started and apply:
                        failed_result["state"] = "unknown"

                    failed_result["message"] = str(exc.detail)

                    return failed_result

                except Exception as exc:

                    if operation_started and apply:
                        failed_result["state"] = "unknown"

                    failed_result["message"] = (
                        str(exc)
                        or "Không thể đồng bộ Schedule."
                    )

                    return failed_result

            # 6. Tạo danh sách coroutine.
            tasks = []

            for mcu in mcus:
                tasks.append(run_sync(mcu))

            # 7. Đồng bộ các MCU đồng thời.
            results = await asyncio.gather(*tasks)

    except httpx.HTTPStatusError as exc:

        if exc.response.status_code in (401, 403):
            raise HTTPException(
                exc.response.status_code,
                "Không có quyền truy cập Registry.",
            ) from exc

        raise HTTPException(
            502,
            "Registry không trả được dữ liệu.",
        ) from exc

    except (httpx.RequestError, ValueError) as exc:

        raise HTTPException(
            503,
            "Không lấy được dữ liệu Registry.",
        ) from exc

    # 8. Tổng hợp kết quả.
    success_count = sum(
        item["state"] == "success"
        for item in results
    )

    if not results:
        state = "empty"

    elif success_count == len(results):
        state = "success"

    else:
        state = "partial"

    return {
        "state": state,
        "mode": "apply" if apply else "preview",
        "totalMcus": len(results),
        "successCount": success_count,
        "results": results,
    }