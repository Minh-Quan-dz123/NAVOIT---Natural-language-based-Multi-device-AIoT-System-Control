# 2. Điều khiển thiết bị thủ công
# STT	Method	API	                                Chức năng
# 3	    POST	/api/devices/{deviceId}/control	    Bật/tắt Device
from fastapi import APIRouter, Depends

from src.server.auth import verify_jwt
from src.server.services.device_control import (
    ManualControlRequest,
    control_device as run_control_device,
)


router = APIRouter(
    prefix="/api/devices",
    tags=["Manual Device Control"],
)

# 3	    POST	/api/devices/{deviceId}/control	
@router.post("/{device_id}/control")
async def control_device(
    device_id: int,
    body: ManualControlRequest,
    token: str = Depends(verify_jwt),
):
    return await run_control_device(device_id,body,token,)
