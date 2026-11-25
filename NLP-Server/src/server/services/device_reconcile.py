
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

from src.server.clients.mqtt_binding import (
    normalize_mac,
    send_device_command,
)

from src.server.services.device_binding import OUTPUT_GPIOS
from src.server.services.operation_locks import get_mcu_lock

from src.server.services.device_control import (
    publish_command,
    wait_response,
)

from src.server.services.device_refresh import (
    validate_refresh_response,
    refresh_one_mcu,
)


# 1. LẤY CẤU HÌNH CHUẨN TỪ REGISTRY
async def load_registry_data(token):
    try:
        async with httpx.AsyncClient(
            base_url=REGISTRY_BASE_URL,
            headers={"Authorization": f"Bearer {token}"},
            timeout=REGISTRY_TIMEOUT_SECONDS,
            follow_redirects=False,
        ) as client:

            catalog_response = await client.get(
                "/api/device/catalog"
            )
            catalog_response.raise_for_status()

            mcu_response = await client.get(
                "/api/microcontroller"
            )
            mcu_response.raise_for_status()

            catalog = catalog_response.json()
            mcus = mcu_response.json()

        if (
            not isinstance(catalog, dict)
            or not isinstance(catalog.get("devices"), list)
        ):
            raise ValueError("Catalog không đúng định dạng.")

        if not isinstance(mcus, list):
            raise ValueError("Danh sách MCU không đúng định dạng.")

        return catalog["devices"], mcus

    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code

        if status in (401, 403):
            raise HTTPException(
                status,
                "Không có quyền đọc dữ liệu Registry.",
            ) from exc

        raise HTTPException(
            502,
            f"Registry trả về HTTP {status}.",
        ) from exc

    except (httpx.RequestError, ValueError, TypeError) as exc:
        raise HTTPException(
            503,
            "Không lấy được cấu hình từ Registry.",
        ) from exc


# 2. ĐỌC SNAPSHOT THỰC TẾ TỪ ESP32
async def read_snapshot(mcu):
    mac = normalize_mac(mcu["macAddress"])
    mcu_type = str(mcu["type"]).strip().lower()

    base = f"iot/{mcu_type}/v1/{mac}"

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
            identifier=f"nlp-reconcile-{uuid4().hex[:12]}",
        ) as mqtt:

            response_topic = f"{base}/FROM_{mcu_type.upper()}/command"
            request_topic = f"{base}/FROM_SV/command"

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

    return validate_refresh_response(response, mcu_type)


# 3. CHUYỂN SNAPSHOT THÀNH DANH SÁCH DEVICE
def snapshot_devices(snapshot):
    devices = {}

    for index, gpio in enumerate(snapshot["gpios"]):
        # Kiểm tra GPIO có hợp lệ không
        if type(gpio) is not int or gpio < 0:
            raise ValueError(f"MCU trả về GPIO không hợp lệ: {gpio}")
        
        devices[gpio] = {
            "gpio": gpio,
            "deviceType": snapshot["deviceTypes"][index],
            "deviceName": snapshot["deviceNames"][index],
        }

    return devices


# 4. KIỂM TRA HAI DEVICE CÓ CÙNG CẤU HÌNH
def matches(first, second):
    same_type = (
        first["deviceType"].strip().casefold()
        == second["deviceType"].strip().casefold()
    )

    same_name = (
        first["deviceName"].strip().casefold()
        == second["deviceName"].strip().casefold()
    )

    return same_type and same_name


# 5. KIỂM TRA SCHEDULE ĐANG CÒN HIỆU LỰC
async def has_active_schedule(client, device_id):
    response = await client.get(
        f"/api/device/{device_id}/schedule"
    )

    if response.status_code == 404:
        return False

    response.raise_for_status()

    schedule = response.json()

    if not isinstance(schedule, dict):
        raise ValueError("Schedule không hợp lệ.")

    # Thiếu isExpired thì coi như lịch còn hiệu lực.
    return schedule.get("isExpired") is not True


# 6. CHUẨN BỊ CẤU HÌNH CHUẨN CỦA MỘT MCU
def desired_devices(catalog, mcu_id, mcu_type="esp32"):
    desired = {}
    is_esp32 = str(mcu_type).strip().lower() == "esp32"

    for device in catalog:
        if not isinstance(device, dict):
            raise ValueError("Device Catalog không hợp lệ.")

        if device.get("microcontrollerId") != mcu_id:
            continue

        gpio = device.get("gpio")
        device_type = device.get("deviceType")
        device_name = device.get("deviceName") or ""
        device_id = device.get("deviceId")

        if (
            type(gpio) is not int
            or gpio < 0
            or (is_esp32 and gpio not in OUTPUT_GPIOS)
        ):
            raise ValueError(f"Device #{device_id} có GPIO không hỗ trợ.")

        if not isinstance(device_type, str) or not device_type.strip():
            raise ValueError(f"Device #{device_id} có loại không hợp lệ.")

        if not isinstance(device_name, str):
            raise ValueError(f"Device #{device_id} có tên không hợp lệ.")

        # Bộ đệm trong DeviceTask.h:
        # DeviceType: 64 bytes, DeviceName: 128 bytes.
        # Chừa 1 byte cho ký tự kết thúc chuỗi.
        if is_esp32 and (
            len(device_type.encode("utf-8")) > 63
            or len(device_name.encode("utf-8")) > 127
        ):
            raise ValueError(f"Device #{device_id} có tên/loại vượt bộ đệm ESP32.")

        if gpio in desired:
            raise ValueError(f"Registry trùng GPIO {gpio} trên MCU #{mcu_id}.")

        desired[gpio] = {
            "gpio": gpio,
            "deviceId": device_id,
            "deviceType": device_type,
            "deviceName": device_name,
        }

        if is_esp32 and len(desired) > 6:
            raise ValueError("Registry khai báo hơn 6 Device trên ESP32." )

    return desired


# 7. THỰC HIỆN DELETE/CREATE VÀ ĐỐI SOÁT
async def execute_action(mcu, command, device):

    # Với DELETE, kiểm tra snapshot mới nhất trước khi xóa.
    # Firmware hiện xóa theo GPIO, không kiểm tra Type/Name.
    if command == "DELETE_DEVICE_REQUEST":
        before = snapshot_devices(
            await read_snapshot(mcu)
        )

        gpio = device["gpio"]

        if gpio not in before or not matches(before[gpio], device):
            raise RuntimeError(
                f"GPIO {gpio} đã thay đổi so với snapshot. "
                "Dừng thao tác để tránh xóa nhầm."
            )

    # Tái sử dụng MQTT Binding Client hiện có.
    ack, _ = await send_device_command(
        mcu["macAddress"],
        command,
        device["gpio"],
        device["deviceType"],
        device["deviceName"],
        mcu_type=mcu["type"],
    )

    if ack.get("status") != "success":
        raise RuntimeError(
            str(ack.get("message") or "ESP32 từ chối lệnh.")
        )

    # ACK thành công chưa đủ.
    # Phải REFRESH để xác minh cấu hình thực tế.
    snapshot = await read_snapshot(mcu)

    actual = snapshot_devices(snapshot)
    gpio = device["gpio"]

    if command == "DELETE_DEVICE_REQUEST":
        if gpio in actual:
            raise RuntimeError(
                f"GPIO {gpio} vẫn còn Device sau DELETE."
            )

    elif command == "CREATE_DEVICE_REQUEST":
        if (
            gpio not in actual
            or not matches(actual[gpio], device)
        ):
            raise RuntimeError(
                f"GPIO {gpio} không khớp sau CREATE."
            )

    return snapshot


# 8. ĐỒNG BỘ CẤU HÌNH CỦA MỘT MCU
async def reconcile_one_mcu(mcu, catalog, token):

    result = {
        "mcuId": mcu.get("id"),
        "state": "failed",
        "message": "",
        "actions": [],
        "skipped": [],
        "refresh": None,
    }

    snapshot_received = False
    mutation_started = False

    try:
        mcu_id = mcu.get("id")

        mcu_type = str(mcu.get("type") or "").strip().lower()

        if not mcu_type or any(c in mcu_type for c in "/+#"):
            raise ValueError("Loại MCU không hợp lệ.")

        if type(mcu_id) is not int or mcu_id <= 0:
            raise ValueError("MCU ID không hợp lệ.")

        if (
            type(mcu.get("userId")) is not int
            or mcu["userId"] <= 0
        ):
            raise ValueError("MCU không có UserId hợp lệ.")

        normalize_mac(mcu.get("macAddress"))

        # 8.1. Lấy cấu hình chuẩn.
        desired = desired_devices(catalog, mcu_id, mcu_type)

        # 8.2. Lấy cấu hình thực tế.
        snapshot = await read_snapshot(mcu)
        snapshot_received = True

        actual = snapshot_devices(snapshot)

        # 8.3. Kiểm tra Schedule trước khi sửa bất kỳ GPIO nào.
        protected = set()

        async with httpx.AsyncClient(
            base_url=REGISTRY_BASE_URL,
            headers={"Authorization": f"Bearer {token}"},
            timeout=REGISTRY_TIMEOUT_SECONDS,
            follow_redirects=False,
        ) as client:

            for gpio, device in desired.items():

                # Đã khớp thì không phải tạo lại.
                if gpio in actual and matches(actual[gpio], device):
                    continue

                if await has_active_schedule(
                    client,
                    device["deviceId"],
                ):
                    protected.add(gpio)

                    result["skipped"].append({
                        "gpio": gpio,
                        "reason": (
                            "Device còn Schedule hiệu lực; "
                            "chưa tự tạo/xóa DeviceTask."
                        ),
                    })

        # 8.4. XÓA DEVICE THỪA HOẶC SAI CẤU HÌNH
        for gpio, device in actual.items():

            if gpio in protected:
                continue

            if gpio in desired and matches(
                device,
                desired[gpio],
            ):
                continue

            mutation_started = True

            snapshot = await execute_action(
                mcu,
                "DELETE_DEVICE_REQUEST",
                device,
            )

            result["actions"].append({
                "command": "DELETE",
                "gpio": gpio,
            })

        # 8.5. TẠO DEVICE CÒN THIẾU
        # Xóa trước, tạo sau để không vượt giới hạn 6.
        actual = snapshot_devices(snapshot)

        for gpio, device in desired.items():

            if gpio in protected:
                continue

            if gpio in actual and matches(
                actual[gpio],
                device,
            ):
                continue

            if gpio in actual:
                raise RuntimeError(
                    f"GPIO {gpio} đang bị chiếm, không CREATE."
                )

            mutation_started = True

            snapshot = await execute_action(
                mcu,
                "CREATE_DEVICE_REQUEST",
                device,
            )

            result["actions"].append({
                "command": "CREATE",
                "gpio": gpio,
            })

            actual = snapshot_devices(snapshot)

        result["state"] = "success"
        result["message"] = "Đã xử lý cấu hình MCU."

    except HTTPException as exc:
        result["state"] = ("unknown" if mutation_started else "failed")
        result["message"] = str(exc.detail)

    except (
        TimeoutError,
        MqttError,
        OSError,
        httpx.HTTPError,
        ValueError,
        TypeError,
        KeyError,
        RuntimeError,
    ) as exc:
        result["state"] = ("unknown" if mutation_started else "failed")
        result["message"] = str(exc) or "Không thể đối soát MCU."

    # 8.6. ĐỐI SOÁT CUỐI VÀ CẬP NHẬT REGISTRY
    # Nếu MQTT có lỗi, vẫn cố đọc lại mà không retry CREATE/DELETE.
    if snapshot_received:
        final = await refresh_one_mcu(mcu)
        result["refresh"] = final

        if final["state"] != "success":
            if result["state"] == "success":
                result["state"] = "unknown"

            result["message"] += (
                " Không cập nhật được Registry: "
                + final["message"]
            )

        elif (
            result["state"] == "success"
            and (
                result["skipped"]
                or final["mismatchedDeviceIds"]
                or final["unknownGpios"]
            )
        ):
            result["state"] = "partial"
            result["message"] = (
                "Còn sai lệch chưa thể tự xử lý."
            )

    return result


# 9. ĐỒNG BỘ TẤT CẢ MCU CỦA USER
# 9. ĐỒNG BỘ TẤT CẢ MCU CỦA USER
async def reconcile_all_mcus(token):

    if (
        not REGISTRY_BASE_URL
        or not REGISTRY_INTERNAL_KEY
        or not MQTT_HOST
    ):
        raise HTTPException(
            503,
            "Thiếu cấu hình Registry/MQTT.",
        )

    # 1. Lấy danh sách MCU thuộc User.
    _, mcus = await load_registry_data(token)

    # Kiểm tra dữ liệu trước khi bắt đầu các task.
    for mcu in mcus:

        if not isinstance(mcu, dict):
            raise HTTPException(
                502, "Danh sách MCU không hợp lệ."
            )

        mcu_id = mcu.get("id")

        if type(mcu_id) is not int or mcu_id <= 0:
            raise HTTPException(
                502, "MCU ID không hợp lệ."
            )

    # 2. Hàm xử lý độc lập cho từng MCU.
    async def run_reconcile(mcu):

        mcu_id = mcu["id"]

        failed_result = {
            "mcuId": mcu_id,
            "state": "failed",
            "message": "",
            "actions": [],
            "skipped": [],
            "refresh": None,
        }

        operation_started = False

        try:

            # Chỉ khóa MCU đang được xử lý.
            async with get_mcu_lock(mcu_id):

                # Đọc lại dữ liệu sau khi lấy lock.
                catalog, fresh_mcus = await load_registry_data(token)

                fresh_mcu = None

                for item in fresh_mcus:

                    if (
                        isinstance(item, dict)
                        and item.get("id") == mcu_id
                    ):
                        fresh_mcu = item
                        break

                # Kiểm tra lại quyền sở hữu MCU.
                if fresh_mcu is None:

                    failed_result["message"] = (
                        "MCU không còn thuộc User."
                    )

                    return failed_result

                # Xử lý toàn bộ nghiệp vụ dưới lock MCU.
                operation_started = True

                return await reconcile_one_mcu(
                    fresh_mcu,
                    catalog,
                    token,
                )

        except HTTPException as exc:

            if operation_started:
                failed_result["state"] = "unknown"

            failed_result["message"] = str(exc.detail)

            return failed_result

        except Exception as exc:

            if operation_started:
                failed_result["state"] = "unknown"

            failed_result["message"] = (
                str(exc) or "Không thể đối soát MCU."
            )

            return failed_result

    # 3. Tạo danh sách coroutine.
    tasks = []

    for mcu in mcus:
        tasks.append(run_reconcile(mcu))

    # 4. Xử lý các MCU đồng thời.
    results = await asyncio.gather(*tasks)

    # 5. Tổng hợp kết quả.
    successful = sum(
        item["state"] == "success"
        for item in results
    )

    partial = sum(
        item["state"] == "partial"
        for item in results
    )

    if not results:
        state = "empty"

    elif successful == len(results):
        state = "success"

    elif successful or partial:
        state = "partial"

    else:
        state = "failed"

    # 6. Trả kết quả cho FE.
    return {
        "state": state,
        "totalMcus": len(results),
        "successCount": successful,
        "partialCount": partial,
        "failedCount": len(results) - successful - partial,
        "results": results,
    }