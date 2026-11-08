# làm nhiệm vụ
# TURN_ON          → 0
# TURN_OFF         → 1
# CANCEL_SCHEDULE  → 2
# QUERY_STATUS     → 3
# NO_ACTION        → 4
# UNKNOWN          → 5


# Tạo ID mapping cho 3 output head từ labels.json

import json
from pathlib import Path

# 1. Xác định thư mục gốc của Backend.
ROOT = Path(__file__).resolve().parents[1]

# 2. Đường dẫn file đầu vào và đầu ra.
source = ROOT / "config" / "labels.json"
target = ROOT / "config" / "label_maps.json"

# 3. Đọc dữ liệu JSON thành Python dictionary.
config = json.loads(source.read_text(encoding="utf-8"))

# 4. Khởi tạo dictionary chứa các mapping.
maps = {}

# 5. Duyệt qua bộ nhãn của 3 nhiệm vụ.
for name, labels in (
    ("intent", config["intents"]),
    ("tag", config["device_tag_labels"]),
    ("time", config["time_tag_labels"]),
):
    # Kiểm tra không có nhãn bị trùng.
    assert len(set(labels)) == len(labels), (f"Các nhãn {name} không được trùng")

    # Ánh xạ từ nhãn sang ID.
    maps[f"{name}2id"] = {label: idx for idx, label in enumerate(labels)}

    # Ánh xạ ngược từ ID sang nhãn.
    maps[f"id2{name}"] = {
        str(idx): label
        for idx, label in enumerate(labels)
    }

    print(
        f"{name}: {len(labels)} nhãn | "
        f"{maps[f'{name}2id']}"
    )

# 6. Xuất kết quả thành file JSON.
target.write_text(json.dumps(maps, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

print("Saved:", target)
