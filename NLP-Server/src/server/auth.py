
import jwt

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.server.config import (
    BASE_DIR,
    JWT_ISSUER,
    JWT_AUDIENCE,
    JWT_PUBLIC_KEY_PATH,
)


# Đọc Authorization: Bearer <token>
bearer_scheme = HTTPBearer(auto_error=False)


def verify_jwt(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),) -> str:

    # 1. Kiểm tra request có Bearer token không
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Chưa cung cấp Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 2. Đọc public key của Registry
    public_key_path = BASE_DIR / JWT_PUBLIC_KEY_PATH

    try:
        public_key = public_key_path.read_text(encoding="utf-8")
    except OSError:
        raise HTTPException(
            status_code=503,
            detail="Không đọc được JWT public key."
        )

    # 3. Xác thực JWT
    try:
        jwt.decode(
            credentials.credentials,
            public_key,
            algorithms=["RS256"],
            issuer=JWT_ISSUER,
            audience=JWT_AUDIENCE,
            leeway=30,
            options={ "require": ["exp", "nbf", "iss", "aud"]},
        )

    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail="JWT không hợp lệ hoặc đã hết hạn.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 4. Trả lại token đã xác thực
    return credentials.credentials
