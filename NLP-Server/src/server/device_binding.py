# Nhận yêu cầu từ Frontend.
# Gọi Registry bằng JWT của User để lấy Device và MCU thuộc tài khoản.
# Kiểm tra điều kiện liên kết/tháo.
# Gọi mqtt_binding.py.
# Nếu ESP32 trả success, gọi Internal API bằng REGISTRY_INTERNAL_KEY.

import asyncio

import httpx

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from src.server.config import (
    REGISTRY_BASE_URL,
    REGISTRY_INTERNAL_KEY,
)

from src.server.mqtt_binding import (
    send_device_command,
    normalize_mac,
)


router = APIRouter(
    prefix="/api/devices",
    tags=["Device Binding"],
)

bearer = HTTPBearer(auto_error=False)

# Chặn hai thao tác binding đồng thời trong 1 tiến trình.
lock = asyncio.Lock()

# GPIO OUTPUT hỗ trợ cho ESP32 DevKit
# Cần đồng bộ danh sách với firmware.
OUTPUT_GPIOS = {
    13, 14, 16, 17, 18, 19, 21,
    22, 23, 25, 26, 27, 32, 33
}


# 1. REQUEST LIÊN KẾT
class BindRequest(BaseModel):
    microcontrollerId: int = Field(gt=0)
    gpio: int = Field(ge=0, le=39)


# 2. TRẢ LỖI
def error(code: int, message: str, state: str = "failed"):
    raise HTTPException(
        code,
        {
            "state": state,
            "message": message,
        },
    )


# 3. LẤY JWT TỪ FRONTEND
def user_token(credentials: HTTPAuthorizationCredentials | None = Depends(bearer),) -> str:
    if credentials is None:
        error(401, "Thiếu JWT người dùng.")

    return credentials.credentials


# 4. GỌI PUBLIC API CỦA REGISTRY
async def get_json(client: httpx.AsyncClient, path: str):
    try:
        response = await client.get(path)
        response.raise_for_status()
        return response.json()

    except httpx.HTTPStatusError as exc:
        code = exc.response.status_code

        if code in (401, 403):
            error(code, "JWT không hợp lệ hoặc không đủ quyền.")

        error(502, f"Registry trả về HTTP {code}.")

    except (httpx.RequestError, ValueError):
        error(503, "Không đọc được dữ liệu Device Registry.")


# 5. LẤY DEVICE VÀ MCU CỦA USER
async def load_user_data(client: httpx.AsyncClient, device_id: int,):
    # Registry kiểm tra JWT và lọc theo UserId.
    catalog = await get_json(client, "/api/device/catalog")
    mcus = await get_json(client, "/api/microcontroller")

    if not isinstance(catalog, dict) or not isinstance(mcus, list):
        error(502, "Dữ liệu Registry không hợp lệ.")

    devices = catalog.get("devices")

    if not isinstance(devices, list):
        error(502, "Device Catalog không hợp lệ.")

    device = next((d for d in devices if d.get("deviceId") == device_id), None,)

    if device is None:
        error(404, "Device không thuộc người dùng hoặc không tồn tại.")

    return device, devices, mcus


# 6. KIỂM TRA MCU
def find_mcu(mcus: list, mcu_id: int):
    mcu = next(
        (m for m in mcus if m.get("id") == mcu_id),
        None,
    )

    if mcu is None:
        error(404, "MCU không thuộc người dùng hoặc không tồn tại.")

    if mcu.get("type") != "esp32":
        error(409, "Chỉ hỗ trợ MCU loại esp32.")

    if type(mcu.get("userId")) is not int or mcu["userId"] <= 0:
        error(409, "MCU chưa có chủ sở hữu hợp lệ.")

    normalize_mac(mcu.get("macAddress", ""))

    return mcu


# 7. CẬP NHẬT DEVICE REGISTRY SAU ACK
async def save_binding(
    device_id: int,
    user_id: int,
    mcu_id: int | None,
    gpio: int | None,
):
    try:
        async with httpx.AsyncClient(base_url=REGISTRY_BASE_URL, timeout=10,
        ) as client:

            response = await client.patch(
                f"/api/internal/devices/{device_id}/binding",
                headers={
                    "X-Internal-Key": REGISTRY_INTERNAL_KEY,
                },
                json={
                    "userId": user_id,
                    "microcontrollerId": mcu_id,
                    "gpio": gpio,
                },
            )

            response.raise_for_status()

            return response.json()

    except (httpx.HTTPError, ValueError):
        error(
            502,
            "ESP32 đã thực thi nhưng Registry chưa xác nhận "
            "lưu binding. Cần đối soát, không thử lại ngay.",
            "unknown",
        )


# 8. LUỒNG NGHIỆP VỤ LIÊN KẾT / THÁO
async def binding_operation(
    device_id: int,
    token: str,
    command: str,
    mcu_id: int | None = None,
    gpio: int | None = None,
):
    if not REGISTRY_INTERNAL_KEY:
        error(503, "NLP Server thiếu REGISTRY_INTERNAL_KEY.")

    if not REGISTRY_BASE_URL:
        error(503, "Thiếu REGISTRY_BASE_URL.")

    async with lock:

        # 8.1. Đọc dữ liệu theo quyền User
        async with httpx.AsyncClient(
            base_url=REGISTRY_BASE_URL,
            headers={ "Authorization": f"Bearer {token}",},
            timeout=10,
        ) as client:

            device, devices, mcus = await load_user_data( client, device_id)

        # 8.2. LIÊN KẾT DEVICE
        if command == "CREATE_DEVICE_REQUEST":

            mcu = find_mcu(mcus, mcu_id)

            if gpio not in OUTPUT_GPIOS:
                error(422, "GPIO không thuộc danh sách OUTPUT hỗ trợ.")

            # Device phải đang chưa liên kết.
            if (
                device.get("microcontrollerId") is not None
                or device.get("gpio") is not None
                or device.get("syncStatus") != "unassigned"
            ):
                error(409, "Device không ở trạng thái chưa liên kết.")

            # GPIO chưa được sử dụng.
            if any(
                d.get("microcontrollerId") == mcu_id
                and d.get("gpio") == gpio
                for d in devices
            ):
                error(409, "GPIO này đã có Device.")

            # Giới hạn 6 Device / ESP32.
            count = sum(
                d.get("microcontrollerId") == mcu_id
                for d in devices
            )

            if count >= 6:
                error(409, "ESP32 đã đủ 6 Device.")

        # 8.3. THÁO LIÊN KẾT DEVICE
        else:
            mcu_id = device.get("microcontrollerId")
            gpio = device.get("gpio")

            if (
                mcu_id is None
                or gpio is None
                or device.get("syncStatus") != "synced"
            ):
                error(
                    409,
                    "Device không có binding đã đồng bộ để tháo."
                )

            mcu = find_mcu(mcus, mcu_id)

        # 8.4. Chuẩn bị thông tin MQTT
        device_type = device.get("deviceType")

        if not isinstance(device_type, str) or not device_type:
            error(409, "DeviceType không hợp lệ.")

        device_name = device.get("deviceName") or ""

        # 8.5. GỬI MQTT VÀ NHẬN ACK
        ack, command_id = await send_device_command(
            mcu["macAddress"],
            command,
            gpio,
            device_type,
            device_name,
        )

        # 8.6. ESP32 báo lỗi => không sửa Registry
        if ack.get("status") != "success":
            error(
                409,
                str(ack.get("message") or "ESP32 từ chối thực hiện."),
            )

        # 8.7. ESP32 thành công => cập nhật Registry
        result = await save_binding(
            device_id,
            mcu["userId"],
            mcu_id if command == "CREATE_DEVICE_REQUEST" else None,
            gpio if command == "CREATE_DEVICE_REQUEST" else None,
        )

        return {
            "state": "success",
            "commandId": command_id,
            "binding": result,
        }


# 9. API LIÊN KẾT
@router.post("/{device_id}/binding")
async def bind_device(device_id: int, body: BindRequest, token: str = Depends(user_token),):
    return await binding_operation(
        device_id,
        token,
        "CREATE_DEVICE_REQUEST",
        body.microcontrollerId,
        body.gpio,
    )


# 10. API THÁO LIÊN KẾT
@router.delete("/{device_id}/binding")
async def unbind_device(device_id: int, token: str = Depends(user_token),):
    return await binding_operation(
        device_id,
        token,
        "DELETE_DEVICE_REQUEST",
    )
