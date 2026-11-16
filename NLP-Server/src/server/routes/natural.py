from fastapi import APIRouter, Depends, HTTPException, Request

from src.server.auth import verify_jwt
from src.server.schemas import NaturalCommandRequest, ParsedCommand
from src.server.services.natural_control import (
    execute_natural_command as run_natural_command,
)


router = APIRouter(prefix="/api/commands/natural",)


# Phân tích câu lệnh, không thực thi thiết bị.
@router.post("/parse", response_model=ParsedCommand)
def parse_natural_command( payload: NaturalCommandRequest, request: Request,):
    text = payload.text.strip()

    if not text:
        raise HTTPException(
            status_code=422,
            detail="Câu lệnh không được để trống."
        )

    predictor = request.app.state.predictor

    if predictor is None:
        raise HTTPException(
            status_code=503,
            detail="Bộ dự đoán chưa sẵn sàng."
        )

    return predictor.predict(text)


# Thực thi câu lệnh thông qua nghiệp vụ hiện có.
@router.post( "/execute", tags=["Natural Language Control"],)
async def execute_natural_command(
    body: NaturalCommandRequest,
    request: Request,
    token: str = Depends(verify_jwt),
):
    return await run_natural_command(body, request, token,)
