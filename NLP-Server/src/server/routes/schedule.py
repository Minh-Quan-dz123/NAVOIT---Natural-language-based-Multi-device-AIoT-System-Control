
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
