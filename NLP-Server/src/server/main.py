
from contextlib import asynccontextmanager

import httpx
import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request

from src.server.auth import verify_jwt
from src.server.config import (
    PREDICTOR_MODE,
    MODEL_CHECKPOINT_PATH,
    VNCORENLP_DIR,
    REGISTRY_BASE_URL,
    REGISTRY_TIMEOUT_SECONDS,
)
from src.server.registry_client import RegistryClient
from src.server.schemas import NaturalCommandRequest, ParsedCommand
from src.server.inference.predictor import Predictor
from src.server.inference.mock_predictor import MockPredictor
from src.server.inference.phobert_predictor import PhoBERTPredictor

import asyncio
import sys

from fastapi.middleware.cors import CORSMiddleware
from src.server.device_binding import router as binding_router
from src.server.device_control import router as control_router
from src.server.natural_control import router as natural_router
from src.server.device_schedule import router as schedule_router


# Aiomqtt 2.x cần SelectorEventLoop trên Windows.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(
        asyncio.WindowsSelectorEventLoopPolicy()
    )

# 1. KHỞI TẠO SERVER
@asynccontextmanager
async def lifespan(app: FastAPI):

    predictor: Predictor | None = None

    if PREDICTOR_MODE == "mock":
        predictor = MockPredictor()

    elif PREDICTOR_MODE == "phobert":
        predictor = PhoBERTPredictor(
            checkpoint_path=MODEL_CHECKPOINT_PATH,
            vncorenlp_dir=VNCORENLP_DIR,
        )

    elif PREDICTOR_MODE != "disabled":
        raise ValueError(
            f"PREDICTOR_MODE không hợp lệ: {PREDICTOR_MODE}"
        )

    app.state.predictor = predictor
    app.state.predictor_mode = PREDICTOR_MODE

    print(f"NLP Server started - Predictor: {PREDICTOR_MODE}")

    yield

    print("NLP Server stopped")


# 2. FASTAPI APPLICATION
app = FastAPI(
    title="Smart Home NLP Server",
    version="0.1.0",
    description="NLP Server cho hệ thống AIoT",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

# Đăng ký API binding.
app.include_router(binding_router)
app.include_router(control_router)
app.include_router(natural_router)
app.include_router(schedule_router)

# 3. HEALTH CHECK
@app.get("/health")
def health(request: Request):

    predictor = request.app.state.predictor

    return {
        "status": "running",
        "predictorMode": request.app.state.predictor_mode,
        "predictorReady": predictor is not None,
    }


# 4. PHÂN TÍCH CÂU LỆNH
@app.post("/api/commands/natural/parse", response_model=ParsedCommand,)
def parse_natural_command(payload: NaturalCommandRequest, request: Request,):

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


# 5. LẤY DEVICE CATALOG
@app.get("/api/devices/catalog")
async def get_device_catalog(token: str = Depends(verify_jwt),):

    # Kiểm tra cấu hình Registry
    if not REGISTRY_BASE_URL:
        raise HTTPException(
            status_code=503,
            detail="Chưa cấu hình REGISTRY_BASE_URL."
        )

    # Khởi tạo Registry Client
    registry = RegistryClient(
        REGISTRY_BASE_URL,
        REGISTRY_TIMEOUT_SECONDS,
    )

    try:
        # Gửi JWT tới Registry để lấy Catalog
        return await registry.get_device_catalog(token)

    except httpx.HTTPStatusError as exc:

        status_code = exc.response.status_code

        if status_code in (401, 403):
            raise HTTPException(
                status_code=status_code,
                detail="Registry từ chối quyền truy cập."
            )

        raise HTTPException(
            status_code=502,
            detail=f"Registry trả về HTTP {status_code}."
        )

    except httpx.RequestError:
        raise HTTPException(
            status_code=503,
            detail="Không kết nối được Device Registry."
        )

    except ValueError:
        raise HTTPException(
            status_code=502,
            detail="Device Catalog không đúng định dạng."
        )


# 6. CHẠY SERVER
if __name__ == "__main__":

    uvicorn.run(
        "src.server.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )
