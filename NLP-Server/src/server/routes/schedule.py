# 3. Quản lý Schedule
# STT	Method	API	Chức năng
# 4	    POST	/api/devices/{deviceId}/schedule	Tạo lịch
# 5	    DELETE	/api/devices/{deviceId}/schedule	Hủy lịch

# 4. Đồng bộ Schedule
# STT	Method	API	                            Chức năng
# 6	    POST	/api/devices/schedules/sync	    Kiểm tra và khôi phục Schedule
from pydantic import BaseModel

from src.server.services.schedule_sync import (
    sync_all_schedules,
)
from fastapi import APIRouter, Depends

from src.server.auth import verify_jwt
from src.server.services.device_schedule import (
    CreateScheduleRequest,
    create_schedule as run_create_schedule,
    cancel_schedule as run_cancel_schedule,
)


router = APIRouter(
    prefix="/api/devices",
    tags=["Manual Schedule"],
)


@router.post("/{device_id}/schedule")
async def create_schedule( device_id: int, body: CreateScheduleRequest, token: str = Depends(verify_jwt),):
    return await run_create_schedule(device_id, body, token,)


@router.delete("/{device_id}/schedule")
async def cancel_schedule(device_id: int, token: str = Depends(verify_jwt),):
    return await run_cancel_schedule( device_id, token,)


class SyncSchedulesRequest(BaseModel):
    apply: bool = False

@router.post("/schedules/sync")
async def sync_schedules(body: SyncSchedulesRequest, token: str = Depends(verify_jwt)):
    return await sync_all_schedules(token, apply=body.apply,)
