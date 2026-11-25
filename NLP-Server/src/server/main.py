
import asyncio
import sys

from contextlib import asynccontextmanager, suppress

import uvicorn

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from src.server.config import (
    PREDICTOR_MODE,
    MODEL_CHECKPOINT_PATH,
    VNCORENLP_DIR,
    MQTT_HOST,
)

from src.server.inference.predictor import Predictor
from src.server.inference.mock_predictor import MockPredictor
from src.server.inference.phobert_predictor import PhoBERTPredictor

from src.server.routes.binding import router as binding_router
from src.server.routes.control import router as control_router
from src.server.routes.schedule import router as schedule_router
from src.server.routes.natural import router as natural_router
from src.server.routes.catalog import router as catalog_router
from src.server.routes.refresh import router as refresh_router

from src.server.clients.mqtt_time_sync import listen_time_sync

# 1. CẤU HÌNH EVENT LOOP CHO WINDOWS
# Aiomqtt 2.x cần SelectorEventLoop trên Windows.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(
        asyncio.WindowsSelectorEventLoopPolicy()
    )


# 2. KHỞI TẠO PREDICTOR
# @asynccontextmanager là một decorator có sẵn trong thư viện contextlib của Python, 
# giúp biến một hàm async generator thành một asynchronous context manager 
# (trình quản lý ngữ cảnh bất đồng bộ).
@asynccontextmanager
async def lifespan(app: FastAPI):

    # 2.1. khởi tạo 1 instance PhoBERTPredictor
    predictor: Predictor | None = None

    if PREDICTOR_MODE == "mock":
        predictor = MockPredictor()

    elif PREDICTOR_MODE == "phobert":
        predictor = PhoBERTPredictor(
            checkpoint_path=MODEL_CHECKPOINT_PATH,
            vncorenlp_dir=VNCORENLP_DIR,
        )

    elif PREDICTOR_MODE != "disabled":
        raise ValueError(f"PREDICTOR_MODE không hợp lệ: {PREDICTOR_MODE}")

    # tự tạo thêm thuộc tính (app.state là nơi lưu trữ dữ liệu dùng chung trong một ứng dụng FastAPI.)
    app.state.predictor = predictor
    app.state.predictor_mode = PREDICTOR_MODE

    print(f"NLP Server started - Predictor: {PREDICTOR_MODE}")

    # 2.2. Khởi động MQTT Time Sync Listener
    time_sync_task = None

    if MQTT_HOST:
        time_sync_task = asyncio.create_task(listen_time_sync())
        # .create_task: Hàm này tạo một Task và lên lịch thực thi coroutine listen_time_sync() trên event loop hiện tại.
    else:
        print("MQTT time sync disabled: chưa cấu hình MQTT_HOST")

    try:
        yield

    finally:
        # Dừng MQTT Listener khi FastAPI shutdown
        if time_sync_task is not None:
            time_sync_task.cancel()

            with suppress(asyncio.CancelledError):
                await time_sync_task

        print("NLP Server stopped")



# 3. FASTAPI APPLICATION
app = FastAPI(
    title="Smart Home NLP Server",
    version="0.1.0",
    description="NLP Server cho hệ thống AIoT",
    lifespan=lifespan,
)


# 4. CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


# 5. ĐĂNG KÝ ROUTER
app.include_router(binding_router)
app.include_router(control_router)
app.include_router(natural_router)
app.include_router(schedule_router)
app.include_router(catalog_router)
app.include_router(refresh_router)


# 6. HEALTH CHECK
@app.get("/health")
def health(request: Request):

    predictor = request.app.state.predictor

    return {
        "status": "running",
        "predictorMode": request.app.state.predictor_mode,
        "predictorReady": predictor is not None,
    }


# 7. CHẠY SERVER
if __name__ == "__main__":

    uvicorn.run(
        "src.server.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )
