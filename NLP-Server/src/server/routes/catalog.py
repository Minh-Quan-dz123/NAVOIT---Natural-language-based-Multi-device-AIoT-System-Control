import httpx

from fastapi import APIRouter, Depends, HTTPException

from src.server.auth import verify_jwt
from src.server.config import (
    REGISTRY_BASE_URL,
    REGISTRY_TIMEOUT_SECONDS,
)
from src.server.clients.registry_client import RegistryClient


router = APIRouter()

# 10	POST	/api/commands/natural/parse	Chỉ phân tích câu lệnh
@router.get("/api/devices/catalog")
async def get_device_catalog( token: str = Depends(verify_jwt),):
    if not REGISTRY_BASE_URL:
        raise HTTPException(
            status_code=503,
            detail="Chưa cấu hình REGISTRY_BASE_URL."
        )

    registry = RegistryClient(
        REGISTRY_BASE_URL,
        REGISTRY_TIMEOUT_SECONDS,
    )

    try:
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
