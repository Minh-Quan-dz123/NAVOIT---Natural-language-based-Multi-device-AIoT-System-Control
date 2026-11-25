# 5. Refresh trạng thái MCU
# STT	Method	API	                            Chức năng
# 7 	POST	/api/microcontrollers/refresh	Cập nhật trạng thái Device và MCU


# 6. Đồng bộ liên kết Device
# STT	Method	API	                                Chức năng
# 8	    POST	/api/microcontrollers/reconcile	    Sửa sai lệch Device giữa MCU và Registry
from fastapi import APIRouter, Depends

from src.server.auth import verify_jwt

from src.server.services.device_refresh import (
    refresh_all_mcus,
)

from src.server.services.device_reconcile import (
    reconcile_all_mcus,
)


router = APIRouter(
    prefix="/api/microcontrollers",
    tags=["Device Refresh"],
)


# 1. CHỈ LÀM MỚI TRẠNG THÁI
@router.post("/refresh")
async def refresh_devices(token: str = Depends(verify_jwt),):
    return await refresh_all_mcus(token)


# 2. SỬA SAI LỆCH CẤU HÌNH DEVICE/GPIO
@router.post("/reconcile")
async def reconcile_devices(token: str = Depends(verify_jwt)):
    return await reconcile_all_mcus(token)
