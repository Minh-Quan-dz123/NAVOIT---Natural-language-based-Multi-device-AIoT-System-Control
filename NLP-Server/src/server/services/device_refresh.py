
import asyncio
import ssl

from datetime import datetime, timezone
from uuid import uuid4

import httpx
from aiomqtt import Client, MqttError
from fastapi import HTTPException

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

from src.server.services.device_control import (
    publish_command,
    wait_response,
    get_registry_data,
)

from src.server.services.operation_locks import get_mcu_lock


# 1. KIỂM TRA RESPONSE TỪ MCU
def validate_refresh_response(data, mcu_type="esp32"):
    if data.get("status") != "success":
        raise ValueError(data.get("message") or "ESP32 từ chối REFRESH.")

    count = data.get("device_count")

    if type(count) is not int or count < 0:
        raise ValueError("device_count không hợp lệ.")

    if mcu_type == "esp32" and count > 6:
        raise ValueError("ESP32 vượt giới hạn 6 Device.")

    gpios = data.get("gpios")
    types = data.get("device_types")
    names = data.get("device_names")
    statuses = data.get("device_status")

    arrays = [gpios, types, names, statuses]

    if not all(isinstance(items, list) for items in arrays):
        raise ValueError("ESP32 trả về danh sách không hợp lệ.")

    if not all(len(items) == count for items in arrays):
        raise ValueError("Số phần tử không khớp device_count.")

    if any(type(pin) is not int or pin < 0 for pin in gpios):
        raise ValueError("Danh sách GPIO không hợp lệ.")

    if len(set(gpios)) != count:
        raise ValueError("Danh sách GPIO bị trùng.")

    if any(
        not isinstance(value, str) or not value.strip()
        for value in types
    ):
        raise ValueError("Danh sách DeviceType không hợp lệ.")

    if any(not isinstance(value, str) for value in names):
        raise ValueError("Danh sách DeviceName không hợp lệ.")

    normalized_statuses = []

    for status in statuses:
        if not isinstance(status, str):
            raise ValueError("DeviceStatus không hợp lệ.")

        value = status.strip().upper()

        if value not in ("ON", "OFF"):
            raise ValueError("DeviceStatus chỉ được ON/OFF.")

        normalized_statuses.append(value)

    return {
        "deviceCount": count,
        "gpios": gpios,
        "deviceTypes": types,
        "deviceNames": names,
        "deviceStatus": normalized_statuses,
    }


# 2. ĐỒNG BỘ MỘT MCU
async def refresh_one_mcu(mcu):
    mcu_id = mcu.get("id")

    result = {
        "mcuId": mcu_id,
        "state": "failed",
        "message": "",
        "matchedDeviceIds": [],
        "mismatchedDeviceIds": [],
        "unknownGpios": [],
    }

    mcu_type = str(mcu.get("type") or "").strip().lower()

    if not mcu_type or any(c in mcu_type for c in "/+#"):
        result["message"] = "Loại MCU không hợp lệ."
        return result

    user_id = mcu.get("userId")

    if type(user_id) is not int or user_id <= 0:
        result["message"] = "MCU chưa có chủ sở hữu hợp lệ."
        return result

    try:
        mac = normalize_mac(mcu.get("macAddress"))
    except HTTPException:
        result["message"] = "MAC của MCU không hợp lệ."
        return result

    base_topic = f"iot/{mcu_type}/v1/{mac}"

    request_topic = f"{base_topic}/FROM_SV/command"
    response_topic = f"{base_topic}/FROM_{mcu_type.upper()}/command"

    command_id = uuid4().hex
    send_time = datetime.now(
        timezone.utc
    ).isoformat(timespec="seconds")

    payload = {
        "command": "REFRESH_DEVICE_REQUEST",
        "command_id": command_id,
        "microcontroller_id": mac,
        "send_time": send_time,
    }

    try:
        # 2.1. Gửi request và nhận response
        async with Client(
            hostname=MQTT_HOST,
            port=MQTT_PORT,
            username=MQTT_USERNAME or None,
            password=MQTT_PASSWORD or None,
            tls_context=(
                ssl.create_default_context() if MQTT_TLS else None
            ),
            identifier=f"nlp-refresh-{uuid4().hex[:12]}",
        ) as mqtt:

            # Subscribe trước khi publish.
            await mqtt.subscribe(response_topic)

            await publish_command(
                mqtt,
                request_topic,
                payload,
            )

            response = await wait_response(
                mqtt,
                response_topic,
                "REFRESH_DEVICE_RESPONSE",
                command_id,
                send_time,
                mac,
            )

        # 2.2. Kiểm tra dữ liệu ESP32
        refresh_data = validate_refresh_response(response, mcu_type)

        # 2.3. Gửi snapshot sang Registry
        registry_payload = {
            "userId": user_id,
            "hardwareId": mac,
            **refresh_data,
        }

        async with httpx.AsyncClient(
            base_url=REGISTRY_BASE_URL,
            timeout=REGISTRY_TIMEOUT_SECONDS,
            follow_redirects=False,
        ) as client:

            registry_response = await client.post(
                f"/api/internal/microcontrollers/{mcu_id}/refresh",
                headers={
                    "X-Internal-Key": REGISTRY_INTERNAL_KEY,
                },
                json=registry_payload,
            )

            registry_response.raise_for_status()
            saved = registry_response.json()

        # 2.4. Trả kết quả cho Frontend
        result["state"] = "success"
        result["message"] = "Đã nhận và lưu trạng thái MCU."
        result["matchedDeviceIds"] = saved["matchedDeviceIds"]
        result["mismatchedDeviceIds"] = saved["mismatchedDeviceIds"]
        result["unknownGpios"] = saved["unknownGpios"]

    except TimeoutError:
        result["message"] = (
            "MCU không phản hồi trong thời gian chờ."
        )

    except (MqttError, OSError):
        result["message"] = "Không thể giao tiếp MQTT với MCU."

    except httpx.HTTPStatusError as exc:
        result["message"] = (
            f"Registry từ chối cập nhật: HTTP "
            f"{exc.response.status_code}."
        )

    except httpx.RequestError:
        result["message"] = "Không kết nối được Registry."

    except (ValueError, KeyError, TypeError, HTTPException) as exc:
        if isinstance(exc, HTTPException):
            result["message"] = str(exc.detail)
        else:
            result["message"] = str(exc)

    return result


# 3. ĐỒNG BỘ TẤT CẢ MCU CỦA USER
async def refresh_all_mcus(token: str):

    if not REGISTRY_BASE_URL or not REGISTRY_INTERNAL_KEY:
        raise HTTPException(
            503, "Thiếu cấu hình Device Registry."
        )

    if not MQTT_HOST:
        raise HTTPException(
            503, "Chưa cấu hình MQTT_HOST."
        )

    # Registry tự kiểm tra JWT và chỉ trả MCU của User.
    try:
        async with httpx.AsyncClient(
            base_url=REGISTRY_BASE_URL,
            headers={"Authorization": f"Bearer {token}"},
            timeout=REGISTRY_TIMEOUT_SECONDS,
            follow_redirects=False,
        ) as client:

            response = await client.get("/api/microcontroller")
            response.raise_for_status()
            mcus = response.json()

    except httpx.HTTPStatusError as exc:
        code = exc.response.status_code

        if code in (401, 403):
            raise HTTPException(
                code, "Registry từ chối quyền truy cập."
            )

        raise HTTPException(
            502, f"Registry trả về HTTP {code}."
        )

    except (httpx.RequestError, ValueError):
        raise HTTPException(
            503, "Không lấy được danh sách MCU từ Registry."
        )

    if not isinstance(mcus, list):
        raise HTTPException(
            502, "Danh sách MCU không hợp lệ."
        )

    if any(not isinstance(mcu, dict) for mcu in mcus):
        raise HTTPException(
            502, "Dữ liệu MCU không hợp lệ."
        )

    if not mcus:
        return {
            "state": "empty",
            "totalMcus": 0,
            "successCount": 0,
            "failedCount": 0,
            "results": [],
        }

    # Giới hạn tối đa 4 kết nối Refresh đồng thời.
    semaphore = asyncio.Semaphore(4)


    async def run_refresh(mcu):

        mcu_id = mcu.get("id")

        if type(mcu_id) is not int or mcu_id <= 0:
            return {
                "mcuId": mcu_id,
                "state": "failed",
                "message": "MCU ID không hợp lệ.",
                "matchedDeviceIds": [],
                "mismatchedDeviceIds": [],
                "unknownGpios": [],
            }

        async with get_mcu_lock(mcu_id):

            async with semaphore:

                try:
                    # Đọc lại MCU sau khi lấy lock.
                    async with httpx.AsyncClient(
                        base_url=REGISTRY_BASE_URL,
                        headers={
                            "Authorization": f"Bearer {token}"
                        },
                        timeout=REGISTRY_TIMEOUT_SECONDS,
                        follow_redirects=False,
                    ) as client:

                        fresh_mcu = await get_registry_data(
                            client,
                            f"/api/microcontroller/{mcu_id}",
                        )

                    if (
                        not isinstance(fresh_mcu, dict)
                        or fresh_mcu.get("id") != mcu_id
                    ):
                        raise HTTPException(
                            502, "Dữ liệu MCU không hợp lệ."
                        )

                    # Hàm này không tự lấy lock.
                    return await refresh_one_mcu(fresh_mcu)

                except HTTPException as exc:
                    return {
                        "mcuId": mcu_id,
                        "state": "failed",
                        "message": str(exc.detail),
                        "matchedDeviceIds": [],
                        "mismatchedDeviceIds": [],
                        "unknownGpios": [],
                    }


    tasks = [run_refresh(mcu) for mcu in mcus]

    results = await asyncio.gather(*tasks)
    success_count = sum(
        item["state"] == "success"
        for item in results
    )

    failed_count = len(results) - success_count

    if success_count == len(results):
        state = "success"
    elif success_count > 0:
        state = "partial"
    else:
        state = "failed"

    return {
        "state": state,
        "totalMcus": len(results),
        "successCount": success_count,
        "failedCount": failed_count,
        "results": results,
    }