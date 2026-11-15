import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]

load_dotenv(BASE_DIR / ".env")



# 1. CHỌN BỘ DỰ ĐOÁN
# Có 3 chế độ:
# disabled: Chưa bật bộ dự đoán
# mock:     Dùng dữ liệu kiểm thử
# phobert:  Dùng model đã fine-tune
PREDICTOR_MODE = os.getenv(
    "NLP_PREDICTOR_MODE",
    "disabled"
).strip().lower()


# 2. ĐƯỜNG DẪN MODEL
MODEL_CHECKPOINT_PATH = os.getenv(
    "NLP_CHECKPOINT_PATH",
    "checkpoints/best_model.pt"
)


# 3. ĐƯỜNG DẪN VNCORENLP
VNCORENLP_DIR = os.getenv(
    "VNCORENLP_DIR",
    "D:/vncorenlp"
)


# 4. KẾT NỐI DEVICE REGISTRY
REGISTRY_BASE_URL = os.getenv("REGISTRY_BASE_URL", "").strip().rstrip("/")
REGISTRY_TIMEOUT_SECONDS = float(os.getenv("REGISTRY_TIMEOUT_SECONDS", "10"))


# 5. CẤU HÌNH JWT

JWT_ISSUER = os.getenv("JWT_ISSUER", "DeviceRegistry.Api").strip()
JWT_AUDIENCE = os.getenv("JWT_AUDIENCE", "DeviceRegistry.Client").strip()
JWT_PUBLIC_KEY_PATH = os.getenv("JWT_PUBLIC_KEY_PATH", "keys/jwt-public.pem").strip()

