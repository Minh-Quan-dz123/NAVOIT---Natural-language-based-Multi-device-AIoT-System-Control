import asyncio
import httpx

from fastapi import HTTPException, Request

from src.server.config import (
    REGISTRY_BASE_URL,
    REGISTRY_TIMEOUT_SECONDS,
)
from src.server.clients.registry_client import RegistryClient
from src.server.schemas import NaturalCommandRequest

from src.server.services.device_resolver import resolve_device

from src.server.services.device_control import (
    ManualControlRequest,
    control_device,
)

from src.server.services.device_schedule import (
    CreateScheduleRequest,
    create_schedule,
    cancel_schedule,
)

from src.server.services.schedule_time_parser import parse_schedule_times

import logging

logger = logging.getLogger("uvicorn.error")

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


"""
Nhận câu lệnh từ Frontend.
Gọi Mock/PhoBERT để hiểu câu lệnh.
Xác định Device mà người dùng muốn điều khiển.
Quyết định thực hiện bật/tắt ngay, tạo Schedule hay hủy Schedule.
Gọi các service có sẵn và trả kết quả về Frontend
"""
async def execute_natural_command( body: NaturalCommandRequest, request: Request, token: str,):

    # 2.0 làm sạch câu lệnh
    text = body.text.strip()
    if not text:
        fail(422, "Câu lệnh không được để trống.")

    # 2.1. lựa chọn predictor dựa trên NLP_PREDICTOR_MODE. 
    predictor = request.app.state.predictor

    if predictor is None:
        fail(503, "Predictor chưa sẵn sàng.")

    # trả về cùng cấu trúc ParsedCommand.
    parsed = predictor.predict(text)
    """
    {
        "text": "Bật đèn học phòng con gái sau 10 phút",
        "intent": "TURN_ON",
        "deviceTags": ["đèn học", "phòng con gái"],
        "timeEntities": [
            {
            "type": "SCHEDULED_DELAY",
            "text": "10 phút"
            }
        ],
        "predictor": "mock"
    }
    """

    # 2.2. Kiểm tra intent
    if parsed.intent not in ("TURN_ON","TURN_OFF","CANCEL_SCHEDULE",):
        fail(422, "Mock chưa hiểu câu lệnh này.")

    if not parsed.deviceTags:
        fail(422, "Không xác định được Tag thiết bị.")

    # 2.3. Xác định Device của User
    # lấy ra danh sách devices từ user có trong token này
    devices = await load_catalog(token)

    # sau đó từ list[device] và các tags, chạy thuật toán để tìm ra các device đang muốn điều khiển
    target_devices = resolve_device(devices, parsed.deviceTags,)
    if not target_devices:
        fail(404, "Không tìm thấy Device phù hợp.")

    # 2.5. THÔNG TIN CHUNG CỦA CÂU LỆNH
    # Các thông tin này dùng chung cho mọi Device.
    common = {
        "text": text,
        "predictor": parsed.predictor,
        "intent": parsed.intent,
        "deviceTags": parsed.deviceTags,
    }


    # 2.6. KIỂM TRA VÀ CHUẨN BỊ THAM SỐ THỜI GIAN
    #
    # Câu lệnh hủy lịch không được có timeEntities.
    if parsed.intent == "CANCEL_SCHEDULE":
        if parsed.timeEntities:
            fail(422, "Lệnh hủy lịch không cần tham số thời gian.")

    # Nếu là lệnh bật/tắt có thời gian:
    # Chỉ cần parse thời gian MỘT LẦN cho cả danh sách Device.
    time_data = None

    if parsed.intent != "CANCEL_SCHEDULE" and parsed.timeEntities:
        time_data = parse_schedule_times(parsed.timeEntities)

        """
        Ví dụ:

        parsed.timeEntities = [
            {
                "type": "SCHEDULED_DELAY",
                "text": "10 phút"
            }
        ]

        time_data = {
            "scheduledDelay": 600,
            "duration": None,
            "scheduledStartAt": None,
            "scheduledEndAt": None
        }
        """


        # 3. HÀM XỬ LÝ RIÊNG CHO TỪNG DEVICE
    async def execute_one_device(device):

        device_id = device["deviceId"]

        device_info = {
            "deviceId": device_id,
            "deviceName": device.get("deviceName"),
            "deviceType": device.get("deviceType"),
            "microcontrollerId": device.get("microcontrollerId"),
            "gpio": device.get("gpio"),
        }

        try:

            # 3.1. HỦY SCHEDULE
            if parsed.intent == "CANCEL_SCHEDULE":

                result = await cancel_schedule(
                    device_id=device_id,
                    token=token,
                )

                return {
                    "state": "success",
                    "device": device_info,
                    "operation": "schedule_cancelled",
                    "scheduleId": result["scheduleId"],
                    "commandId": result["commandId"],
                    "message": result["message"],
                }

            # 3.2. TẠO SCHEDULE
            elif time_data is not None:

                action = (
                    "on"
                    if parsed.intent == "TURN_ON"
                    else "off"
                )

                schedule_body = CreateScheduleRequest(
                    action=action,
                    **time_data,
                )

                result = await create_schedule(
                    device_id=device_id,
                    body=schedule_body,
                    token=token,
                )

                return {
                    "state": "success",
                    "device": device_info,
                    "operation": "schedule_created",
                    "commandId": result["commandId"],
                    "schedule": result["schedule"],
                }

            # 3.3. ĐIỀU KHIỂN ON/OFF
            else:

                action = (
                    "ON"
                    if parsed.intent == "TURN_ON"
                    else "OFF"
                )

                result = await control_device(
                    device_id=device_id,
                    body=ManualControlRequest(
                        action=action
                    ),
                    token=token,
                )

                return {
                    "state": "success",
                    "device": device_info,
                    "operation": "device_controlled",
                    "commandId": result["commandId"],
                    "currentStatus": result["currentStatus"],
                }

        # 3.4. LỖI NGHIỆP VỤ CỦA DEVICE
        except HTTPException as exc:

            detail = exc.detail

            if isinstance(detail, dict):
                message = detail.get(
                    "message",
                    str(detail),
                )
            else:
                message = str(detail)

            return {
                "state": "failed",
                "device": device_info,
                "statusCode": exc.status_code,
                "message": message,
            }

        # 3.5. LỖI KHÔNG LƯỜNG TRƯỚC
        except Exception:

            logger.exception(
                "Natural command failed for deviceId=%s",
                device_id,
            )

            return {
                "state": "failed",
                "device": device_info,
                "statusCode": 500,
                "message": (
                    "Không thể thực hiện lệnh cho Device."
                ),
            }

    # 4. TẠO DANH SÁCH COROUTINE
    tasks = []

    for device in target_devices:

        tasks.append(
            execute_one_device(device)
        )

    # 5. XỬ LÝ ĐỒNG THỜI
    results = await asyncio.gather(*tasks)

    # 6. TỔNG HỢP KẾT QUẢ
    success_count = 0
    failed_count = 0

    for result in results:

        if result["state"] == "success":
            success_count += 1
        else:
            failed_count += 1

    if failed_count == 0:
        state = "success"

    elif success_count == 0:
        state = "failed"

    else:
        state = "partial"

    # 7. TRẢ KẾT QUẢ CHO FRONTEND
    return {
        **common,
        "state": state,
        "totalDevices": len(target_devices),
        "successCount": success_count,
        "failedCount": failed_count,
        "results": results,
    }