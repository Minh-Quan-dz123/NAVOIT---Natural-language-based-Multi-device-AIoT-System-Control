# Nhận yêu cầu từ Frontend.
# Gọi Registry bằng JWT của User để lấy Device và MCU thuộc tài khoản.
# Kiểm tra điều kiện liên kết/tháo.
# Gọi mqtt_binding.py.
# Nếu ESP32 trả success, gọi Internal API bằng REGISTRY_INTERNAL_KEY.

import httpx

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field

from src.server.config import (
    REGISTRY_BASE_URL,
    REGISTRY_INTERNAL_KEY,
)

from src.server.clients.mqtt_binding import (
    send_device_command,
    normalize_mac,
)

from src.server.services.operation_locks import (
    get_mcu_lock,
    get_device_lock,
)

# GPIO OUTPUT hỗ trợ cho ESP32 DevKit
# Cần đồng bộ danh sách với firmware.
OUTPUT_GPIOS = {
    13, 14, 16, 17, 18, 19, 21,
    22, 23, 25, 26, 27, 32, 33
}


# 1. REQUEST LIÊN KẾT
# BaseModel: Class có sẵn của Pydantic, giúp tự động kiểm tra kiểu dữ liệu, 
# kiểm tra điều kiện và chuyển đổi dữ liệu khi phù hợp.
class BindRequest(BaseModel):
    microcontrollerId: int = Field(gt=0) # gt=0: Greater Than (lớn hơn 0).
    gpio: int = Field(ge=0) # ge=0: Greater than or Equal (lớn hơn hoặc bằng 0).


# 2. TRẢ LỖI
def error(code: int, message: str, state: str = "failed"):
    raise HTTPException(
        code,
        {
            "state": state,
            "message": message,
        },
    )

# 3. GỌI PUBLIC API CỦA REGISTRY
async def get_json(client: httpx.AsyncClient, path: str):
    try:
        response = await client.get(path) # gửi request theo API đó và nhận response
        response.raise_for_status()   # phương thức có sẵn của class httpx.Response. Nó kiểm tra mã HTTP mà Registry trả về
        return response.json() # đọc nội dung JSON trong response và chuyển thành dữ liệu Python.

    except httpx.HTTPStatusError as exc:
        code = exc.response.status_code

        if code in (401, 403):
            error(code, "JWT không hợp lệ hoặc không đủ quyền.")

        error(502, f"Registry trả về HTTP {code}.")

    except (httpx.RequestError, ValueError):
        error(503, "Không đọc được dữ liệu Device Registry.")


# 3. LẤY DEVICE VÀ MCU CỦA USER
async def load_user_data(client: httpx.AsyncClient, device_id: int,):
    
    # bên registry trả về với /api/device/catalog
    # return Ok(new
    # {
    #     DeviceCount = result.Count,
    #     Devices = result
    # });
    catalog = await get_json(client, "/api/device/catalog")
    mcus = await get_json(client, "/api/microcontroller")

    if not isinstance(catalog, dict) or not isinstance(mcus, list):
        error(502, "Dữ liệu Registry không hợp lệ.")

    devices = catalog.get("devices")
    if not isinstance(devices, list):
        error(502, "Device Catalog không hợp lệ.")

    # lấy ra device trong danh sách
    device = next((d for d in devices if d.get("deviceId") == device_id), None,)

    if device is None:
        error(404, "Device không thuộc người dùng hoặc không tồn tại.")

    return device, devices, mcus

# 5. Đọc thông tin Device và MCU từ Registry bằng JWT User.
async def read_binding_data(token: str, device_id: int):

    async with httpx.AsyncClient(
        base_url=REGISTRY_BASE_URL,
        headers={
            "Authorization": f"Bearer {token}",
        },
        timeout=10,
    ) as client:

        return await load_user_data(client, device_id)
    
# 6. KIỂM TRA MCU
def find_mcu(mcus: list, mcu_id: int):
    mcu = next((m for m in mcus if m.get("id") == mcu_id), None,)

    if mcu is None:
        error(404, "MCU không thuộc người dùng hoặc không tồn tại.")

    normalize_mac(mcu.get("macAddress", "")) # dạng "AABBCCDDEEFF"

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
                headers={"X-Internal-Key": REGISTRY_INTERNAL_KEY,},
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



# 8. LUỒNG NGHIỆP VỤ LIÊN KẾT/THÁO device <=>GPIO
async def binding_operation(
    device_id: int,
    token: str,
    command: str,
    mcu_id: int | None = None,
    gpio: int | None = None,
):
    # 8.1. kiểm tra các biến nội trước
    if not REGISTRY_INTERNAL_KEY:
        error(503, "NLP Server thiếu REGISTRY_INTERNAL_KEY.")

    if not REGISTRY_BASE_URL:
        error(503, "Thiếu REGISTRY_BASE_URL.")

    if command not in ("CREATE_DEVICE_REQUEST", "DELETE_DEVICE_REQUEST",):
        error(400, "Command không hợp lệ.")

    # Chờ lấy được khóa của Device tương ứng, sau đó mới thực hiện các câu lệnh 
    # bên trong khối async with. Khi thực hiện xong, tự động giải phóng khóa.
    async with get_device_lock(device_id):

        # 8.2. Đọc trước để xác định MCU cần khóa. 
        device, devices, mcus = await read_binding_data(token, device_id)

        # 8.3. nếu là tạo thiết bị thì phải có mcu_id và gpio, còn lệch khác thì ko sao 
        if command == "CREATE_DEVICE_REQUEST":
            if mcu_id is None or gpio is None:
                error(422, "Thiếu MCU hoặc GPIO.")

            find_mcu(mcus, mcu_id) # kiểm tra cho chắc
            target_mcu_id = mcu_id

        # nếu là tháo liên kết thì chỉ cần device id là được
        else:
            target_mcu_id = device.get("microcontrollerId")

            if target_mcu_id is None:
                error(409, "Device chưa liên kết với MCU.")

            find_mcu(mcus, target_mcu_id)

        # Chỉ khóa đúng MCU đang thao tác.
        async with get_mcu_lock(target_mcu_id):

            # Đọc lại dữ liệu sau khi lấy được lock.
            # Tránh sử dụng dữ liệu cũ trong lúc chờ.
            device, devices, mcus = await read_binding_data(token, device_id)

            mcu = find_mcu(mcus, target_mcu_id)

            # LIÊN KẾT
            if command == "CREATE_DEVICE_REQUEST":

                if ( (mcu["type"].strip().lower() == "esp32") and (gpio not in OUTPUT_GPIOS)):
                    error(422, "GPIO không được hỗ trợ.")

                if ( device.get("microcontrollerId") is not None
                    or device.get("gpio") is not None
                ):
                    error(409, "Device đã có liên kết.")

                if any( # 	Trả về True nếu có ít nhất một phần tử thỏa mãn
                    (d.get("microcontrollerId") == target_mcu_id) and (d.get("gpio") == gpio)
                    for d in devices
                ):
                    error(409, "GPIO đã được sử dụng.")


            # THÁO LIÊN KẾT
            else:
                if device.get("microcontrollerId") != target_mcu_id:
                    error(409, "Liên kết MCU đã thay đổi.")

                gpio = device.get("gpio")
                if (gpio is None):
                    error(409, "Device không có binding để tháo.")

            device_type = device.get("deviceType")

            if not isinstance(device_type, str) or not device_type:
                error(409, "DeviceType không hợp lệ.")

            device_name = device.get("deviceName") or ""

            # Gửi MQTT và chờ ESP32 phản hồi.
            ack, command_id = await send_device_command(
                mcu["macAddress"],
                command,
                gpio,
                device_type,
                device_name,
                mcu_type=mcu["type"],
            )

            if ack.get("status") != "success":
                error(409, str(ack.get("message") or "ESP32 từ chối thực hiện."),)

            # Chỉ cập nhật Registry sau khi ESP32 thành công.
            result = await save_binding(
                device_id,
                mcu["userId"],
                target_mcu_id
                if command == "CREATE_DEVICE_REQUEST"
                else None,
                gpio
                if command == "CREATE_DEVICE_REQUEST"
                else None,
            )

            return {
                "state": "success",
                "commandId": command_id,
                "binding": result,
            }
