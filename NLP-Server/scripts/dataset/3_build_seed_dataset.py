
"""
SINH DATASET NLU SMART HOME TỪ seed_config.py

Ý tưởng:
    1) Đọc ACTIONS, DEVICES, LOCATIONS, TEMPLATES từ seed_config.py.
    2) Chỉ chọn các template chứa đúng n placeholder Location khác nhau.
    3) Sinh Action x Device x TỔ HỢP n Location KHÔNG LẶP.
    4) Thay placeholder, gắn nhãn entity và ghi thành JSONL.

Cách chạy tại thư mục gốc của dự án:
    python scripts/3_build_seed_dataset.py --mode preview --n 3
    python scripts/3_build_seed_dataset.py --mode all --n 2
    python scripts/3_build_seed_dataset.py --mode sample --n 3 --max-samples 1000

Mặc định ghi vào: data/raw/smarthome_seed.jsonl
Chú ý: chế độ all vẫn có thể sinh nhiều dữ liệu dù đã dùng tổ hợp.
"""

from __future__ import annotations

# %% 1. IMPORT VÀ XÁC ĐỊNH ĐƯỜNG DẪN
import argparse
import json
import math
import os
import random
import re
import sqlite3
import sys
import tempfile
import unicodedata
from contextlib import closing
from itertools import combinations 
from pathlib import Path
from string import Formatter

try:
    SCRIPT_DIR = Path(__file__).resolve().parent
except NameError:
    SCRIPT_DIR = Path.cwd() / "scripts" / "dataset"
    if not (SCRIPT_DIR / "seed_config.py").exists():
        SCRIPT_DIR = Path.cwd()

# Cho phép `from seed_config import ...` khi chạy từ thư mục khác.
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from seed_config import ACTIONS, DEVICES, LOCATIONS, RANDOM_SEED, TEMPLATES

ROOT = SCRIPT_DIR.parents[1] / "dataset"
OUTPUT = ROOT / "data" / "raw" / "smarthome_seed.jsonl"


# %% 2. TÁCH MARKER VÀ GÁN NHÃN ENTITY
# Hai kiểu marker mà annotate() hiểu:
#     [[D:đèn]]                       -> entity TAG
#     [[D:phòng khách]]               -> entity TAG (giữ tương thích với code cũ)
#     [[S:DURATION:5 phút]]           -> entity DURATION
#     [[S:SCHEDULED_DELAY:10 phút]]   -> entity SCHEDULED_DELAY
# group(1): D/S; group(2): loại Schedule (nếu có); group(3): nội dung.
PATTERN = re.compile(
    r"\[\[(D|S):(?:(DURATION|SCHEDULED_DELAY|SCHEDULED_START_AT|"
    r"SCHEDULED_END_AT):)?([^\[\]]+)\]\]"
)


def annotate(rendered: str) -> tuple[str, list[dict], list[dict]]:
    """Bỏ marker [[...]] và tính vị trí bắt đầu/kết thúc của từng entity.

    Ví dụ:
        rendered = "Bật [[D:đèn]] ở [[D:phòng khách]]"

    Kết quả:
        text = "Bật đèn ở phòng khách"
        device_entities = [
            {"type": "TAG", "text": "đèn", "start": 4, "end": 7},
            {"type": "TAG", "text": "phòng khách", "start": 10, "end": 20}
        ]
        schedule_entities = []

    `start` có tính, `end` không tính; vì thế text[start:end] == entity.text.
    """
    output: list[str] = []
    device_entities: list[dict] = []
    schedule_entities: list[dict] = []

    # cursor: vị trí đang đọc trong chuỗi có marker (rendered).
    # offset: độ dài của câu sạch đã xử lý; dùng để ghi start/end.
    cursor = 0
    offset = 0

    for match in PATTERN.finditer(rendered):
        # Ví dụ đoạn trước [[D:đèn]] là "Bật ".
        before = unicodedata.normalize("NFC", rendered[cursor:match.start()])
        value = unicodedata.normalize("NFC", match.group(3))

        output.append(before)
        offset += len(before)
        start, end = offset, offset + len(value)

        if match.group(1) == "D":
            # D không được có nhãn thời gian; [[D:DURATION:...]] là sai.
            if match.group(2) is not None:
                raise ValueError("Device marker không được có loại Schedule")
            device_entities.append({
                "type": "TAG", "text": value, "start": start, "end": end
            })
        else:
            # S buộc phải chỉ rõ loại: DURATION, SCHEDULED_DELAY,...
            if match.group(2) is None:
                raise ValueError("Schedule marker thiếu loại")
            schedule_entities.append({
                "type": match.group(2), "text": value,
                "start": start, "end": end
            })

        # Chỉ ghép nội dung entity, KHÔNG ghép marker [[D:...]].
        output.append(value)
        offset = end
        cursor = match.end()

    # Nối phần còn lại sau marker cuối cùng.
    output.append(unicodedata.normalize("NFC", rendered[cursor:]))
    text = "".join(output)

    # Nếu vẫn còn [[ hoặc ]] thì có marker sai định dạng.
    if "[[" in text or "]]" in text:
        raise ValueError(f"Marker sai định dạng: {rendered!r}")

    return text, device_entities, schedule_entities


# %% 3. KIỂM TRA DỮ LIỆU NGUỒN VÀ LẬP KẾ HOẠCH SINH
# Chấp nhận {l1}, {l2}, ..., {l10}; ngoài ra hỗ trợ {l} cho code cũ.
LOCATION_FIELD = re.compile(r"l[1-9]\d*\Z")

def get_template_fields(template: str) -> list[str]:
    """Lấy placeholder KHÁC NHAU theo đúng thứ tự xuất hiện.

    Ví dụ:
        "{action} {device} ở {l1} và {l2}, gần {l1}"
        -> ["action", "device", "l1", "l2"]

    Mặc dù {l1} có 2 lần xuất hiện, nó chỉ được tính 1 Location.
    """
    fields: list[str] = []
    for _, name, fmt, conversion in Formatter().parse(template):
        if name is None:  # Phần chữ bình thường, không phải {placeholder}.
            continue
        if (
            fmt or conversion or
            (name not in {"device", "action", "l"}
             and not LOCATION_FIELD.fullmatch(name))
        ):
            raise ValueError( f"Placeholder không hợp lệ: {{{name}}} trong {template!r}")
        if name not in fields:
            fields.append(name)
    return fields


def validate_source() -> None:
    """Kiểm tra cấu hình để tránh lỗi khi sinh câu.

    Ví dụ: DEVICES = ["đèn", "ĐÈN"] -> báo trùng (không phân biệt hoa/thường).
    DEVICES = ["đèn", ""] -> báo phần tử rỗng.
    """
    if not TEMPLATES:
        raise ValueError("TEMPLATES đang rỗng")

    for key, values in (("DEVICES", DEVICES), ("LOCATIONS", LOCATIONS)):
        if not values:
            raise ValueError(f"{key} đang rỗng")
        if any(
            not isinstance(x, str) or not x.strip()
            or any(c in x for c in "[]{}")
            for x in values
        ):
            raise ValueError(f"{key} có giá trị rỗng hoặc ký tự marker không hợp lệ")
        if len({x.strip().casefold() for x in values}) != len(values):
            raise ValueError(f"{key} chứa phần tử trùng")

    for intent, actions in ACTIONS.items():
        if not actions or any(
            not isinstance(x, str) or not x.strip() for x in actions
        ):
            raise ValueError(f"ACTIONS[{intent!r}] không hợp lệ")


def make_plans(n: int) -> list[dict]:
    """Chọn template có ĐÚNG n Location và đếm số câu có thể sinh.

    Đổi từ CHỈNH HỢP P(L,n) sang TỔ HỢP C(L,n):
        C(L,n) = L! / (n! * (L-n)!)

    Ví dụ: 3 Location, n=2, 2 Action, 2 Device, 1 template:
        C(3,2) = 3 -> tổng lý thuyết = 2 * 2 * 3 = 12 câu.
    """
    if n < 0:
        raise ValueError("n phải >= 0")
    validate_source()
    plans: list[dict] = []

    # TEMPLATES cũ chứa mỗi dòng là (intent, group, template).
    for intent, group, template in TEMPLATES:
        fields = get_template_fields(template)
        location_fields = [
            f for f in fields
            if f == "l" or LOCATION_FIELD.fullmatch(f)
        ]

        # --n 3 chỉ chọn template có đúng 3 placeholder Location khác nhau.
        if len(location_fields) != n or n > len(LOCATIONS):
            continue

        # Nếu không có {action}/{device}, ta chỉ lặp một lần qua None.
        actions = ACTIONS.get(intent, []) if "action" in fields else [None]
        if not actions:
            raise ValueError(f"Thiếu ACTIONS cho intent {intent!r}: {group}")
        devices = DEVICES if "device" in fields else [None]

        # QUAN TRỌNG: math.comb thay cho math.perm.
        total = len(actions) * len(devices) * math.comb(len(LOCATIONS), n)
        plans.append({
            "intent": intent,
            "group": group,
            "template": template,
            "location_fields": location_fields,
            "actions": actions,
            "devices": devices,
            "total": total,
        })

    return plans


# %% 4. PREVIEW: ƯỚC LƯỢNG MÀ KHÔNG TẠO CÂU

def estimate_dataset(n: int) -> dict:
    """Trả thống kê cho số Location n.

    Ví dụ: 20 Location, n=3 -> mỗi template dùng đủ Action/Device
    có C(20,3) = 1140 cách chọn nhóm Location, KHÔNG phải 6840.
    """
    plans = make_plans(n)
    return {
        "n": n,
        "templates": len(plans),
        "theoretical_samples": sum(p["total"] for p in plans),
        # Mỗi câu phủ được tối đa n Location khác nhau.
        # Ví dụ 20 Location, n=3 -> ít nhất ceil(20/3) = 7 câu.
        "location_coverage_min": math.ceil(len(LOCATIONS) / n) if n else 0,
    }


def print_estimate(n: int | None = None) -> None:
    """In thống kê ra terminal; n=None thì thống kê mọi n có template.

    Ví dụ: `--mode preview --n 3` chỉ in hàng thống kê cho n=3.
    """
    if n is not None:
        values = [n]
    else:
        values = sorted({
            sum(f == "l" or bool(LOCATION_FIELD.fullmatch(f))
                for f in get_template_fields(template))
            for _, _, template in TEMPLATES
        })

    print(f"DEVICES={len(DEVICES)}, LOCATIONS={len(LOCATIONS)}")
    print("n | templates | tổng tổ hợp lý thuyết | tối thiểu để phủ Location")
    for k in values:
        info = estimate_dataset(k)
        print(
            f"{k:>1} | {info['templates']:>9} | "
            f"{info['theoretical_samples']:>23,} | "
            f"{info['location_coverage_min']:>6}"
        )
    print("Lưu ý: số lý thuyết chưa trừ câu trùng và câu sai ngữ nghĩa.")


# %% 5. RENDER: THAY PLACEHOLDER VÀ GÁN NHÃN
def render_template(
    plan: dict,
    action: str | None,
    device: str | None,
    locations: tuple[str, ...],
) -> dict:
    """Biến một (template, action, device, tổ hợp Location) thành 1 mẫu.

    Ví dụ:
        template = "{action} {device} ở {l1} và {l2}"
        action = "bật", device = "đèn"
        locations = ("phòng khách", "phòng ngủ")

    Trung gian:
        "Bật [[D:đèn]] ở [[D:phòng khách]] và [[D:phòng ngủ]]"
    Đầu ra:
        {"text": "Bật đèn ở phòng khách và phòng ngủ", "intent": ..., ...}
    """
    template = plan["template"]
    replacements: dict[str, str] = {}

    if action is not None:
        # Nếu {action} đứng đầu câu, viết hoa ký tự đầu cho tự nhiên.
        if template.lstrip().startswith("{action}"):
            action = action[0].upper() + action[1:]
        replacements["action"] = action

    if device is not None:
        replacements["device"] = f"[[D:{device}]]"

    # Ví dụ location_fields=["l1","l2"] và locations=("A","B"):
    # replacements["l1"]="[[D:A]]", replacements["l2"]="[[D:B]]".
    for field, location in zip(plan["location_fields"], locations):
        replacements[field] = f"[[D:{location}]]"

    # format_map thay tất cả placeholder; kể cả {l1} lặp 2 lần.
    filled = template.format_map(replacements)
    text, device_entities, schedule_entities = annotate(filled)

    # Chống lỗi gán lệch vị trí entity sau khi xóa marker.
    for entity in device_entities + schedule_entities:
        if text[entity["start"]:entity["end"]] != entity["text"]:
            raise ValueError(f"Offset sai trong câu {text!r}: {entity}")

    return {
        "text": text,
        "intent": plan["intent"],
        "device_entities": device_entities,
        "schedule_entities": schedule_entities,
        "template_group": plan["group"],
    }


def normalized_text(row: dict) -> str:
    """Tạo khóa so trùng từ câu đã sinh.

    Ví dụ: "  Bật  ĐÈN ở phòng khách " -> "bật đèn ở phòng khách".
    Hai bản ghi có cùng khóa sẽ chỉ được ghi ra file một lần.
    """
    return " ".join(row["text"].casefold().split())


# %% 6. ALL: SINH TOÀN BỘ TỔ HỢP
def generate_all(n: int):
    """Lần lượt sinh Action x Device x C(Location,n) cho mỗi template.

    Ví dụ LOCATIONS=["A","B","C"], n=2:
        combinations(LOCATIONS,2) -> (A,B), (A,C), (B,C).
    KHÔNG có (B,A), (C,A), (C,B).

    Dùng `yield` thay vì trả một list rất lớn để tiết kiệm RAM.
    """
    plans = make_plans(n)
    if not plans:
        raise ValueError(f"Không có template với n={n} Location")

    for plan in plans:
        for action in plan["actions"]:
            for device in plan["devices"]:
                # combinations có sẵn thay permutations.
                for locations in combinations(LOCATIONS, n):
                    yield render_template(plan, action, device, locations)


# %% 7. SAMPLE: LẤY NGẪU NHIÊN VỚI GIỚI HẠN
def generate_sampled(
    n: int,
    max_samples: int,
    seed: int = RANDOM_SEED,
):
    """Lấy ngẫu nhiên tối đa max_samples câu khác nhau; yêu cầu n>=3.

    Thuật toán 2 giai đoạn:
        1) Phủ Location: chia danh sách Location sau khi xáo trộn
           thành nhóm n phần tử. Nhóm cuối thiếu thì thêm phần tử khác.
        2) Sinh ngẫu nhiên thêm cho đến khi đạt giới hạn hoặc hết lượt thử.

    QUAN TRỌNG: Các nhóm đều được sắp theo THỨ TỰ GỐC của LOCATIONS.
    Ví dụ LOCATIONS=[A,B,C], nếu rng.sample chọn [C,A], ta đổi về (A,C).
    Nhờ đó (A,C) và (C,A) không bị tính thành 2 tổ hợp.

    Lưu ý: không đảm bảo phân phối đều trên tất cả template; cũng không
    đảm bảo mọi Action/Device đều được phủ. Nếu câu chữ trùng nhiều,
    số câu thực tế có thể thấp hơn max_samples.
    """
    if n == 1:
        raise ValueError("Chế độ sample không hỗ trợ n=1; dùng --mode all --n 1")
    if n < 0:
        raise ValueError("n phải >= 0")
    if max_samples <= 0:
        raise ValueError("max_samples phải > 0")

    plans = make_plans(n)
    if not plans:
        raise ValueError(f"Không có template với n={n} Location")

    # Ví dụ L=20, n=3 thì tối thiểu 7 câu mới phủ đủ 20 Location.
    minimum = math.ceil(len(LOCATIONS) / n)
    if max_samples < minimum:
        raise ValueError(f"Cần ít nhất {minimum} mẫu để phủ {len(LOCATIONS)} Location")

    rng = random.Random(seed)  # Seed cố định giúp tái tạo cùng mẫu.
    seen: set[str] = set()      # Chống trùng ngay trong chế độ sample.
    count = 0
    total_possible = sum(p["total"] for p in plans)
    target = min(max_samples, total_possible)

    # Vị trí gốc quyết định thứ tự chuẩn khi đổi nhóm ngẫu nhiên thành tổ hợp.
    # Ví dụ: {"A":0, "B":1, "C":2} => ["C","A"] được sắp thành ["A","C"].
    location_order = {location: i for i, location in enumerate(LOCATIONS)}

    # GIAI ĐOẠN 1: BẢO ĐẢM MỖI LOCATION XUẤT HIỆN ÍT NHẤT MỘT LẦN.
    shuffled = LOCATIONS.copy()
    rng.shuffle(shuffled)

    # Chia thành các nhóm cỡ n; các nhóm đầu không trùng phần tử với nhau.
    for start in range(0, len(shuffled), n):
        block = shuffled[start:start + n]

        # Nếu nhóm cuối thiếu n phần tử, bổ sung từ Location khác trong danh sách.
        # Ví dụ L=7, n=3: [A,B,C], [D,E,F], [G] -> thêm 2 giá trị vào [G].
        if len(block) < n:
            extras = rng.sample(
                [loc for loc in shuffled if loc not in block],
                n - len(block),
            )
            block.extend(extras)

        # Không phụ thuộc vào thứ tự ngẫu nhiên trong block.
        picked = tuple(sorted(block, key=location_order.__getitem__))

        # Thử tối đa 200 lựa chọn Action / Device / Template để tìm câu mới.
        for _ in range(200):
            plan = rng.choice(plans)
            row = render_template(
                plan,
                rng.choice(plan["actions"]),
                rng.choice(plan["devices"]),
                picked,
            )
            key = normalized_text(row)
            if key not in seen:
                seen.add(key)
                count += 1
                yield row
                break
        else:
            raise ValueError("Không sinh được mẫu duy nhất để bảo đảm độ phủ Location")

    # GIAI ĐOẠN 2: SINH NGẪU NHIÊN ĐẾN KHI ĐẠT GIỚI HẠN.
    attempts = 0
    max_attempts = max(1000, 30 * (target - count))

    while count < target and attempts < max_attempts:
        attempts += 1
        plan = rng.choice(plans)

        # THAY ĐỔI CỐT LÕI so với random.sample(LOCATIONS,n):
        # sample INDEX, sau đó SORT index để có MỘT thứ tự cố định.
        # Ví dụ indices ngẫu nhiên [2,0] -> sort -> [0,2] -> (A,C).
        indices = sorted(rng.sample(range(len(LOCATIONS)), n))
        picked = tuple(LOCATIONS[i] for i in indices)

        row = render_template(
            plan,
            rng.choice(plan["actions"]),
            rng.choice(plan["devices"]),
            picked,
        )
        key = normalized_text(row)
        if key in seen:
            continue  # Đã có câu này: không tăng count, thử câu khác.

        seen.add(key)
        count += 1
        yield row

    if count < target:
        print(f"Cảnh báo: chỉ sinh được {count}/{target} mẫu không trùng")


# %% 8. GHI JSONL, LỌC TRÙNG BẰNG SQLITE

def write_dataset(rows, output: Path = OUTPUT) -> int:
    """Ghi từng mẫu ra JSONL mà không lưu toàn bộ dataset trong RAM.

    Thuật toán:
        1) Tạo file JSONL tạm và cơ sở dữ liệu SQLite tạm.
        2) Mỗi row: thử INSERT khóa normalized_text vào SQLite.
        3) Nếu khóa mới: thêm id, ghi 1 dòng JSON; nếu trùng: bỏ qua.
        4) Chỉ sau khi thành công mới thay file đầu ra bằng file tạm.

    Ví dụ hai row có text "Bật đèn" và "  bật  ĐÈN "
    -> chỉ ghi một dòng, id bắt đầu từ ex_000001.
    """
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    written = 0

    # File tạm nằm cùng thư mục đích để os.replace() thay file thuận lợi.
    with tempfile.TemporaryDirectory(prefix="seed_tmp_", dir=output.parent) as tmp:
        tmp_dir = Path(tmp)
        with closing(sqlite3.connect(tmp_dir / "seen.sqlite")) as conn:
            conn.execute("CREATE TABLE seen (key TEXT PRIMARY KEY)")

            with (tmp_dir / "result.jsonl").open(
                "w", encoding="utf-8", newline="\n"
            ) as f:
                for row in rows:
                    key = normalized_text(row)

                    # SQLite dùng PRIMARY KEY để phát hiện và bỏ qua khóa trùng.
                    cursor = conn.execute(
                        "INSERT OR IGNORE INTO seen(key) VALUES (?)", (key,)
                    )
                    if cursor.rowcount == 0:
                        continue

                    written += 1
                    record = {"id": f"ex_{written:06d}", **row}
                    # ensure_ascii=False: giữ nguyên dấu tiếng Việt.
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")

                conn.commit()

        # Nếu sinh thất bại giữa chừng, file output cũ chưa bị ghi đè.
        os.replace(tmp_dir / "result.jsonl", output)

    print(f"Đã ghi {written:,} mẫu không trùng vào: {output}")
    return written


# %% 9. MAIN: CHỌN CHẾ ĐỘ TỪ DÒNG LỆNH

def main() -> None:
    """Đọc tham số CLI rồi chạy preview/all/sample.

    Ví dụ:
        --mode preview --n 3: chỉ thống kê.
        --mode all --n 2: sinh tất cả nhóm 2 Location.
        --mode sample --n 3 --max-samples 1000: sinh tối đa 1000 câu.
    """
    parser = argparse.ArgumentParser(description="Sinh dataset Smart Home NLU")
    parser.add_argument(
        "--mode", choices=["preview", "all", "sample"], default="preview"
    )
    parser.add_argument(
        "--n", type=int, default=None,
        help="Số placeholder Location khác nhau trong mỗi template"
    )
    parser.add_argument(
        "--max-samples", type=int, default=None,
        help="Số câu tối đa khi dùng --mode sample"
    )
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()

    if args.mode == "preview":
        print_estimate(args.n)
        return  # Không sinh câu hoặc tạo file JSONL.

    if args.n is None:
        parser.error("Cần truyền --n khi sinh dataset")

    print_estimate(args.n)
    if args.mode == "all":
        write_dataset(generate_all(args.n), args.output)
    else:
        if args.max_samples is None:
            parser.error("Chế độ sample cần --max-samples")
        write_dataset(generate_sampled(args.n, args.max_samples), args.output)


# Chạy `python script.py`: gọi main().
# Trong Jupyter: có thể gọi từng hàm, không tự parse các tham số notebook.
if __name__ == "__main__" and "ipykernel" not in sys.modules:
    main()
