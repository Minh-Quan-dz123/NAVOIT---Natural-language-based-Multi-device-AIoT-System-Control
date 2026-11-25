# 1. Quản lý liên kết Device với MCU
# STT	Method	    API	                                Chức năng
# 1 	POST	    /api/devices/{deviceId}/binding	    Gắn Device vào MCU/GPIO
# 2	    DELETE	    /api/devices/{deviceId}/binding	    Tháo Device khỏi MCU

from fastapi import APIRouter, Depends
from src.server.auth import verify_jwt
from src.server.services.device_binding import (
    BindRequest,
    binding_operation,
)


router = APIRouter(
    prefix="/api/devices",
    tags=["Device Binding"],
)

# 1. POST /api/devices/{id}/binding . nội dung binding ở body
@router.post("/{device_id}/binding")
async def bind_device(device_id: int, body: BindRequest, token: str = Depends(verify_jwt)):
    return await binding_operation(
        device_id,
        token,
        "CREATE_DEVICE_REQUEST",
        body.microcontrollerId,
        body.gpio,
    )

# 2	    DELETE	    /api/devices/{deviceId}/binding	
@router.delete("/{device_id}/binding")
async def unbind_device(device_id: int, token: str = Depends(verify_jwt)):
    return await binding_operation(
        device_id,
        token,
        "DELETE_DEVICE_REQUEST",
    )
