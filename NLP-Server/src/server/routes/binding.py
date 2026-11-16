# Nhận yêu cầu từ Frontend.
# Gọi Registry bằng JWT của User để lấy Device và MCU thuộc tài khoản.
# Kiểm tra điều kiện liên kết/tháo.
# Gọi mqtt_binding.py.
# Nếu ESP32 trả success, gọi Internal API bằng REGISTRY_INTERNAL_KEY.


from fastapi import APIRouter, Depends

from src.server.services.device_binding import (
    BindRequest,
    binding_operation,
    user_token,
)


router = APIRouter(
    prefix="/api/devices",
    tags=["Device Binding"],
)


@router.post("/{device_id}/binding")
async def bind_device(
    device_id: int,
    body: BindRequest,
    token: str = Depends(user_token),
):
    return await binding_operation(
        device_id,
        token,
        "CREATE_DEVICE_REQUEST",
        body.microcontrollerId,
        body.gpio,
    )


@router.delete("/{device_id}/binding")
async def unbind_device(
    device_id: int,
    token: str = Depends(user_token),
):
    return await binding_operation(
        device_id,
        token,
        "DELETE_DEVICE_REQUEST",
    )
