import httpx

from fastapi import APIRouter, Depends, HTTPException, Request

from src.server.auth import verify_jwt
from src.server.config import (
    REGISTRY_BASE_URL,
    REGISTRY_TIMEOUT_SECONDS,
)
from src.server.registry_client import RegistryClient
from src.server.schemas import NaturalCommandRequest

from src.server.device_resolver import resolve_device
from src.server.device_control import (
    ManualControlRequest,
    control_device,
)
from src.server.device_schedule import (
    CreateScheduleRequest,
    create_schedule,
    cancel_schedule,
)
from src.server.schedule_time_parser import parse_schedule_times


router = APIRouter(
    prefix="/api/commands/natural",
    tags=["Natural Language Control"],
)


def fail(code: int, message: str):
    raise HTTPException(
        status_code=code,
        detail={
            "state": "failed",
            "message": message,
        },
    )


# 1. LẤY DEVICE CATALOG THEO JWT USER
async def load_catalog(token: str) -> list:
    registry = RegistryClient(
        REGISTRY_BASE_URL,
        REGISTRY_TIMEOUT_SECONDS,
    )

    try:
        catalog = await registry.get_device_catalog(token)
        return catalog["devices"]

    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code

        if status in (401, 403):
            fail(status, "Không có quyền xem Device Catalog.")

        fail(502, f"Registry trả về HTTP {status}.")

    except (httpx.RequestError, ValueError, KeyError):
        fail(503, "Không lấy được Device Catalog.")


# 2. API THỰC THI CÂU LỆNH
@router.post("/execute")
async def execute_natural_command(
    body: NaturalCommandRequest,
    request: Request,
    token: str = Depends(verify_jwt),
):
    text = body.text.strip()

    if not text:
        fail(422, "Câu lệnh không được để trống.")

    # 2.1. MockPredictor hoặc PhoBERT
    predictor = request.app.state.predictor

    if predictor is None:
        fail(503, "Predictor chưa sẵn sàng.")

    parsed = predictor.predict(text)

    # 2.2. Kiểm tra intent
    if parsed.intent not in (
        "TURN_ON",
        "TURN_OFF",
        "CANCEL_SCHEDULE",
    ):
        fail(422, "Mock chưa hiểu câu lệnh này.")

    if not parsed.deviceTags:
        fail(422, "Không xác định được Tag thiết bị.")

    # 2.3. Xác định Device của User
    devices = await load_catalog(token)

    device = resolve_device(
        devices,
        parsed.deviceTags,
    )

    device_id = device["deviceId"]

    device_info = {
        "deviceId": device_id,
        "deviceName": device.get("deviceName"),
        "deviceType": device.get("deviceType"),
        "microcontrollerId": device.get("microcontrollerId"),
        "gpio": device.get("gpio"),
    }

    common = {
        "state": "success",
        "text": text,
        "predictor": parsed.predictor,
        "intent": parsed.intent,
        "deviceTags": parsed.deviceTags,
        "device": device_info,
    }

    # 3. HỦY SCHEDULE
    if parsed.intent == "CANCEL_SCHEDULE":

        if parsed.timeEntities:
            fail(422, "Lệnh hủy lịch không cần tham số thời gian.")

        # DÙNG LẠI API HỦY SCHEDULE THỦ CÔNG
        result = await cancel_schedule(
            device_id=device_id,
            token=token,
        )

        return {
            **common,
            "operation": "schedule_cancelled",
            "scheduleId": result["scheduleId"],
            "commandId": result["commandId"],
            "message": result["message"],
        }

    # 4. TẠO SCHEDULE KHI CÓ THÔNG TIN THỜI GIAN
    if parsed.timeEntities:

        # 4.1. Chuẩn hóa thời gian
        time_data = parse_schedule_times(parsed.timeEntities)

        action = (
            "on" if parsed.intent == "TURN_ON"
            else "off"
        )

        # 4.2. Tạo request giống chức năng Schedule thủ công
        schedule_body = CreateScheduleRequest(
            action=action,
            **time_data,
        )

        # 4.3. DÙNG LẠI API TẠO SCHEDULE THỦ CÔNG
        result = await create_schedule(
            device_id=device_id,
            body=schedule_body,
            token=token,
        )

        return {
            **common,
            "operation": "schedule_created",
            "commandId": result["commandId"],
            "schedule": result["schedule"],
        }

    # 5. ĐIỀU KHIỂN ON/OFF TỨC THỜI
    action = (
        "ON" if parsed.intent == "TURN_ON"
        else "OFF"
    )

    # DÙNG LẠI CHỨC NĂNG ON/OFF THỦ CÔNG
    result = await control_device(
        device_id=device_id,
        body=ManualControlRequest(action=action),
        token=token,
    )

    return {
        **common,
        "operation": "device_controlled",
        "commandId": result["commandId"],
        "currentStatus": result["currentStatus"],
    }
