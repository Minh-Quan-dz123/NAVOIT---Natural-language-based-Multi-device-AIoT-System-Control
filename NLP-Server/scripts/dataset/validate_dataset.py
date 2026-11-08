
"""Kiểm tra JSONL trước khi huấn luyện SmartHomePhoBERT (Python >= 3.10).

Chạy từ thư mục gốc dự án:
    python scripts/validate_dataset.py

    python scripts/validate_dataset.py --input data/splits/train.jsonl

    python scripts/validate_dataset.py --train data/splits/train.jsonl \
        --validation data/splits/validation.jsonl --test data/splits/test.jsonl
"""

from __future__ import annotations

import argparse
import collections
import importlib.util
import io
import json
import re
import sqlite3
import sys
import tempfile
import tokenize
import unicodedata
from pathlib import Path
from string import Formatter


# ============================================================
# 1. CẤU HÌNH
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

DATA_FILE = ROOT / "data" / "raw" / "smarthome_seed.jsonl"
LABEL_FILE = ROOT / "config" / "labels.json"
SEED_FILE = ROOT / "scripts" / "seed_config.py"

SCHEDULE_MARKER = re.compile(
    r"\[\[S:([A-Z_]+):[^\[\]]+\]\]"
)

FLOOR_PATTERN = re.compile(r"^tầng\s+(?:\d+|trệt|hầm)$")

ROOM_PREFIXES = ("phòng ", "nhà bếp")


# ============================================================
# 2. HÀM CHUẨN HÓA TEXT
# ============================================================

def normalize_text(text: str) -> str:
    """Dùng cùng quy tắc chống trùng với build_seed_dataset.py."""
    return " ".join(
        unicodedata.normalize("NFC", text).casefold().split()
    )


# ============================================================
# 3. QUẢN LÝ LỖI VÀ CẢNH BÁO
# ============================================================

class Report:
    """Đếm toàn bộ vấn đề nhưng giới hạn số thông báo lưu trong RAM."""

    def __init__(self, max_messages: int = 60):
        self.counts = collections.Counter()
        self.messages: list[str] = []
        self.max_messages = max_messages

    def add(self, level: str, message: str) -> None:
        self.counts[level] += 1

        if len(self.messages) < self.max_messages:
            self.messages.append(f"[{level}] {message}")

    def error(self, message: str) -> None:
        self.add("ERROR", message)

    def warn(self, message: str) -> None:
        self.add("WARN", message)


# ============================================================
# 4. THỐNG KÊ DATASET
# ============================================================

class Stats:

    def __init__(self, name: str):
        self.name = name
        self.rows = 0

        self.intents = collections.Counter()
        self.groups = collections.Counter()
        self.schedule_types = collections.Counter()

        self.device_spans = 0
        self.no_devices = 0
        self.no_schedules = 0

        self.device_span_distribution = collections.Counter()
        self.schedule_span_distribution = collections.Counter()

    def update(self, obj: dict) -> None:
        """Chỉ thống kê các mẫu vượt qua kiểm tra cấu trúc."""

        self.rows += 1

        self.intents[obj["intent"]] += 1
        self.groups[obj["template_group"]] += 1

        device_count = len(obj["device_entities"])
        schedule_count = len(obj["schedule_entities"])

        self.device_spans += device_count
        self.no_devices += (device_count == 0)
        self.no_schedules += (schedule_count == 0)

        self.device_span_distribution[device_count] += 1
        self.schedule_span_distribution[schedule_count] += 1

        self.schedule_types.update(
            entity["type"]
            for entity in obj["schedule_entities"]
        )

    def show(self) -> None:

        print(f"\n--- {self.name}: {self.rows:,} mẫu hợp lệ ---")
        print("Intent:", dict(sorted(self.intents.items())))

        print(f"Số template_group: {len(self.groups)}")
        print("15 nhóm có nhiều mẫu nhất:", self.groups.most_common(15))

        print(
            f"Device spans: {self.device_spans:,}; "
            f"câu không có Device: {self.no_devices:,}"
        )

        print(f"Câu không có Schedule: {self.no_schedules:,}")

        print(
            "Loại Schedule:",
            dict(sorted(self.schedule_types.items()))
        )

        print(
            "Số Device/câu:",
            dict(sorted(self.device_span_distribution.items()))
        )

        print(
            "Số Schedule/câu:",
            dict(sorted(self.schedule_span_distribution.items()))
        )


# ============================================================
# 5. KIỂM TRA LABELS.JSON
# ============================================================

def _get_label_list(labels: dict, key: str) -> list[str]:
    """Kiểm tra một danh sách nhãn có hợp lệ hay không."""

    value = labels.get(key)

    if (
        not isinstance(value, list)
        or not value
        or any(
            not isinstance(v, str) or not v.strip()
            for v in value
        )
        or len(value) != len(set(value))
    ):
        raise ValueError(
            f"labels.json: '{key}' phải là list chuỗi "
            "không rỗng, không trùng"
        )

    return value


def _check_bio(values: list[str], key: str) -> set[str]:
    """Kiểm tra tính nhất quán của bộ nhãn BIO."""

    if "O" not in values:
        raise ValueError(f"labels.json: '{key}' thiếu nhãn 'O'")

    types_b = set()
    types_i = set()

    for value in values:

        if value == "O":
            continue

        if value.startswith("B-") and len(value) > 2:
            types_b.add(value[2:])

        elif value.startswith("I-") and len(value) > 2:
            types_i.add(value[2:])

        else:
            raise ValueError(
                f"labels.json: '{key}' có nhãn BIO sai: {value!r}"
            )

    if types_b != types_i:
        raise ValueError(
            f"labels.json: '{key}' thiếu B-/I- tương ứng: "
            f"{types_b ^ types_i}"
        )

    return types_b


def load_labels(path: Path) -> tuple[set[str], set[str]]:
    """Đọc và kiểm tra bộ nhãn của 3 head."""

    with path.open("r", encoding="utf-8") as file:
        labels = json.load(file)

    if not isinstance(labels, dict):
        raise ValueError("labels.json phải là JSON object")

    # Head 1: Intent
    intents = set(_get_label_list(labels, "intents"))

    # Head 2: Device Tag
    tag_key = next(
        (
            key for key in ("tag_labels", "device_tag_labels")
            if key in labels
        ),
        None
    )

    if tag_key is None:
        raise ValueError(
            "labels.json thiếu 'tag_labels' "
            "(hoặc 'device_tag_labels')"
        )

    tag_types = _check_bio(
        _get_label_list(labels, tag_key),
        tag_key
    )

    if tag_types != {"TAG"}:
        raise ValueError(
            f"{tag_key} phải chứa đúng các nhãn "
            "O, B-TAG, I-TAG"
        )

    # Head 3: Schedule Tag
    time_types = _check_bio(
        _get_label_list(labels, "time_tag_labels"),
        "time_tag_labels"
    )

    if "TAG" in time_types:
        raise ValueError(
            "Schedule không được dùng loại TAG của Device head"
        )

    return intents, time_types


# ============================================================
# 6. KIỂM TRA SEED_CONFIG.PY
# ============================================================

def load_seed_catalog(
    path: Path,
    report: Report
) -> tuple[dict, set[str]]:
    """Đọc template và kiểm tra dữ liệu nguồn."""

    source = path.read_text(encoding="utf-8")

    # 6.1. Phát hiện hai string literal kề nhau.
    # Ví dụ: "phòng bếp" "bếp" -> Python tự nối chuỗi.
    previous = None

    for tok in tokenize.generate_tokens(
        io.StringIO(source).readline
    ):

        if tok.type in (
            tokenize.NL,
            tokenize.COMMENT,
            tokenize.ENCODING
        ):
            continue

        if (
            tok.type == tokenize.STRING
            and previous is not None
            and previous.type == tokenize.STRING
        ):
            report.error(
                f"{path.name}:{tok.start[0]}: "
                "hai chuỗi kề nhau; kiểm tra dấu phẩy"
            )

        previous = tok

    # 6.2. Import seed_config.py.
    spec = importlib.util.spec_from_file_location(
        "dataset_seed_config", path
    )

    if spec is None or spec.loader is None:
        raise ValueError(f"Không thể import {path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # 6.3. Kiểm tra danh sách DEVICES và LOCATIONS.
    for list_name in ("DEVICES", "LOCATIONS"):

        words = getattr(module, list_name)

        if not isinstance(words, list) or not words:
            report.error(
                f"seed_config.py: {list_name} phải là list không rỗng"
            )
            continue

        seen = set()

        for word in words:

            if not isinstance(word, str) or not word.strip():
                report.error(
                    f"seed_config.py: {list_name} "
                    "có phần tử không hợp lệ"
                )
                continue

            key = normalize_text(word)

            if key in seen:
                report.error(
                    f"seed_config.py: {list_name} bị trùng: {word!r}"
                )

            seen.add(key)

            if not unicodedata.is_normalized("NFC", word):
                report.warn(
                    f"seed_config.py: {list_name} "
                    f"chưa NFC: {word!r}"
                )

    # 6.4. Xây dựng catalog theo template_group.
    catalog = {}

    for intent, group, template in module.TEMPLATES:

        if group in catalog:
            report.error(
                f"seed_config.py: template_group trùng: {group}"
            )
            continue

        fields = [
            field
            for _, field, _, _ in Formatter().parse(template)
            if field is not None
        ]

        # Số Device TAG chính bằng số lần xuất hiện
        # của {device} và các placeholder Location.
        count_device = sum(
            field == "device"
            or field == "l"
            or bool(re.fullmatch(r"l[1-9]\d*", field))
            for field in fields
        )

        # Đếm số Schedule entity theo từng loại.
        expected_time = collections.Counter(
            SCHEDULE_MARKER.findall(template)
        )

        catalog[group] = (
            intent,
            count_device,
            expected_time
        )

    locations = {
        normalize_text(value)
        for value in module.LOCATIONS
        if isinstance(value, str)
    }

    return catalog, locations


# ============================================================
# 7. KIỂM TRA TỪNG DANH SÁCH ENTITY
# ============================================================

def check_entities(
    obj: dict,
    text: str,
    key: str,
    valid_types: set[str],
    where: str,
    report: Report
) -> list[tuple[int, int, str]] | None:
    """Kiểm tra type, nội dung, offset của từng entity."""

    entities = obj.get(key)

    if not isinstance(entities, list):
        report.error(f"{where}: {key} phải là list")
        return None

    intervals = []
    valid = True

    for index, entity in enumerate(entities):

        prefix = f"{where}: {key}[{index}]"

        # 7.1. Kiểm tra object.
        if not isinstance(entity, dict):
            report.error(f"{prefix}: entity phải là object")
            valid = False
            continue

        # 7.2. Kiểm tra loại entity.
        entity_type = entity.get("type")

        if (
            not isinstance(entity_type, str)
            or entity_type not in valid_types
        ):
            report.error(
                f"{prefix}: type không hợp lệ: {entity_type!r}"
            )
            valid = False

        # 7.3. Kiểm tra text entity.
        value = entity.get("text")

        if not isinstance(value, str) or not value.strip():
            report.error(f"{prefix}: text entity không hợp lệ")
            valid = False

        # 7.4. Kiểm tra offset.
        start = entity.get("start")
        end = entity.get("end")

        if (
            type(start) is not int
            or type(end) is not int
            or not 0 <= start < end <= len(text)
        ):
            report.error(
                f"{prefix}: span [start,end) sai: "
                f"{start!r}, {end!r}"
            )
            valid = False
            continue

        # 7.5. Kiểm tra nội dung thực tế.
        surface = text[start:end]

        if surface != value:
            report.error(
                f"{prefix}: text entity {value!r} "
                f"!= text[{start}:{end}]={surface!r}"
            )
            valid = False

        # 7.6. Không cho phép entity chứa whitespace ở rìa.
        if not surface.strip() or surface != surface.strip():
            report.error(
                f"{prefix}: entity chứa khoảng trắng ở rìa"
            )
            valid = False

        intervals.append((start, end, key))

    return intervals if valid else None


# ============================================================
# 8. KIỂM TRA CHỒNG LẤN CẢ HAI HEAD
# ============================================================

def check_overlap(
    intervals: list[tuple[int, int, str]],
    where: str,
    report: Report
) -> None:
    """Không cho phép hai entity bất kỳ chồng lấn."""

    intervals.sort()

    if not intervals:
        return

    latest = intervals[0]

    for span in intervals[1:]:

        if span[0] < latest[1]:
            report.error(
                f"{where}: span chồng lấn: {latest} và {span}"
            )

        if span[1] > latest[1]:
            latest = span


# ============================================================
# 9. KIỂM TRA NGỮ NGHĨA BẰNG HEURISTIC
# ============================================================

def semantic_warnings(
    obj: dict,
    known_locations: set[str],
    where: str,
    report: Report
) -> None:
    """Cảnh báo mâu thuẫn vị trí, không tự sửa dữ liệu."""

    locations = {
        normalize_text(entity["text"])
        for entity in obj["device_entities"]
        if normalize_text(entity["text"]) in known_locations
    }

    # 9.1. Phát hiện hai tầng khác nhau.
    floors = sorted(
        value
        for value in locations
        if FLOOR_PATTERN.fullmatch(value)
    )

    if len(floors) > 1:
        report.warn(
            f"{where}: nhiều tầng khác nhau "
            f"trong cùng một thiết bị: {floors}"
        )

    # 9.2. Phát hiện các phòng có thể mâu thuẫn.
    rooms = sorted(
        value
        for value in locations
        if value.startswith(ROOM_PREFIXES)
    )

    # "phòng ngủ" và "phòng ngủ chính" có thể là
    # một tên chung và một tên cụ thể.
    contradicting = [
        (a, b)
        for i, a in enumerate(rooms)
        for b in rooms[i + 1:]
        if a not in b and b not in a
    ]

    if contradicting:
        report.warn(
            f"{where}: các phòng có thể mâu thuẫn: "
            f"{contradicting[:3]}"
        )


# ============================================================
# 10. VALIDATE MỘT MẪU DATASET
# ============================================================

def validate_row(
    obj: object,
    where: str,
    intents: set[str],
    time_types: set[str],
    catalog: dict | None,
    locations: set[str],
    report: Report
) -> bool:
    """Kiểm tra schema, nhãn, span và template_group."""

    errors_before = report.counts["ERROR"]

    # 10.1. Mỗi mẫu bắt buộc là dictionary.
    if not isinstance(obj, dict):
        report.error(
            f"{where}: mỗi dòng phải là JSON object"
        )
        return False

    # 10.2. ID.
    identity = obj.get("id")

    if not isinstance(identity, str) or not identity.strip():
        report.error(
            f"{where}: id phải là chuỗi không rỗng"
        )

    # 10.3. Intent.
    value = obj.get("intent")

    if not isinstance(value, str) or value not in intents:
        report.error(
            f"{where}: intent không hợp lệ: {value!r}"
        )

    # 10.4. Template group.
    group = obj.get("template_group")

    if not isinstance(group, str) or not group.strip():
        report.error(
            f"{where}: template_group phải là chuỗi không rỗng"
        )

    elif catalog is not None:

        if group not in catalog:
            report.error(
                f"{where}: template_group không có trong "
                f"seed_config: {group!r}"
            )

        else:
            expected_intent, _, _ = catalog[group]

            if value != expected_intent:
                report.error(
                    f"{where}: intent {value!r} "
                    f"khác intent template {expected_intent!r}"
                )

    # 10.5. Text.
    text = obj.get("text")

    if not isinstance(text, str) or not text.strip():
        report.error(
            f"{where}: text phải là chuỗi không rỗng"
        )
        return False

    if not unicodedata.is_normalized("NFC", text):
        report.error(
            f"{where}: text chưa chuẩn hóa Unicode NFC"
        )

    # 10.6. Kiểm tra hai danh sách entity.
    devices = check_entities(
        obj, text, "device_entities", {"TAG"}, where, report
    )

    schedules = check_entities(
        obj, text, "schedule_entities", time_types, where, report
    )

    if devices is not None and schedules is not None:

        # 10.7. Kiểm tra chồng lấn cả hai head.
        check_overlap(
            devices + schedules, where, report
        )

        # 10.8. Đối chiếu với template gốc.
        if (
            catalog is not None
            and isinstance(group, str)
            and group in catalog
        ):
            _, expected_device_count, expected_schedules = (
                catalog[group]
            )

            actual_schedules = collections.Counter(
                entity["type"]
                for entity in obj["schedule_entities"]
            )

            if len(devices) != expected_device_count:
                report.error(
                    f"{where}: số Device TAG = {len(devices)}, "
                    f"template cần {expected_device_count}"
                )

            if actual_schedules != expected_schedules:
                report.error(
                    f"{where}: Schedule {dict(actual_schedules)} "
                    f"khác template {dict(expected_schedules)}"
                )

        # 10.9. Chỉ kiểm tra ngữ nghĩa khi chưa có lỗi.
        if report.counts["ERROR"] == errors_before:
            semantic_warnings(
                obj, locations, where, report
            )

    return report.counts["ERROR"] == errors_before


# ============================================================
# 11. ĐỌC VÀ VALIDATE JSONL THEO TỪNG DÒNG
# ============================================================

def validate_file(
    path: Path,
    name: str,
    conn: sqlite3.Connection,
    report: Report,
    intents: set[str],
    time_types: set[str],
    catalog: dict | None,
    locations: set[str],
    strict_groups: bool
) -> Stats:
    """Streaming JSONL, kiểm tra trùng bằng SQLite."""

    stats = Stats(name)
    nonempty = 0

    with path.open("r", encoding="utf-8") as file:

        for number, line in enumerate(file, 1):

            # Bỏ qua dòng trắng.
            if not line.strip():
                continue

            nonempty += 1
            where = f"{path}:{number}"

            # 11.1. Đọc JSON.
            try:
                obj = json.loads(line)

            except json.JSONDecodeError as exc:
                report.error(
                    f"{where}: JSON không hợp lệ ({exc.msg})"
                )
                continue

            # 11.2. Validate từng mẫu.
            good = validate_row(
                obj,
                where,
                intents,
                time_types,
                catalog,
                locations,
                report
            )

            if not isinstance(obj, dict):
                continue

            # 11.3. Kiểm tra ID trùng.
            identity = obj.get("id")

            if isinstance(identity, str) and identity.strip():

                found = conn.execute(
                    "INSERT OR IGNORE INTO ids VALUES (?, ?)",
                    (identity, where)
                )

                if found.rowcount == 0:

                    first = conn.execute(
                        "SELECT source FROM ids WHERE id=?",
                        (identity,)
                    ).fetchone()[0]

                    report.error(
                        f"{where}: id {identity!r} trùng với {first}"
                    )
                    good = False

            # 11.4. Kiểm tra câu trùng cả trong và giữa các file.
            text = obj.get("text")

            if isinstance(text, str) and text.strip():

                key = normalize_text(text)

                found = conn.execute(
                    "INSERT OR IGNORE INTO texts VALUES (?, ?, ?)",
                    (key, where, name)
                )

                if found.rowcount == 0:

                    first, original_split = conn.execute(
                        "SELECT source, split FROM texts WHERE text=?",
                        (key,)
                    ).fetchone()

                    report.error(
                        f"{where}: câu trùng với "
                        f"{first} ({original_split})"
                    )
                    good = False

            # 11.5. Phát hiện template_group xuất hiện
            # ở nhiều tập dữ liệu.
            group = obj.get("template_group")

            if isinstance(group, str) and group.strip():

                found = conn.execute(
                    "INSERT OR IGNORE INTO groups VALUES (?, ?)",
                    (group, name)
                )

                if found.rowcount == 0:

                    first_split = conn.execute(
                        "SELECT split FROM groups WHERE name=?",
                        (group,)
                    ).fetchone()[0]

                    if first_split != name:

                        # Chỉ thông báo một lần cho mỗi
                        # cặp group và tập dữ liệu.
                        once = conn.execute(
                            "INSERT OR IGNORE INTO group_alerts "
                            "VALUES (?, ?)",
                            (group, name)
                        )

                        if once.rowcount:

                            message = (
                                f"template_group {group!r} "
                                f"xuất hiện trong cả {first_split} "
                                f"và {name} (nguy cơ template leakage)"
                            )

                            if strict_groups:
                                report.error(message)
                            else:
                                report.warn(message)

            # 11.6. Thống kê mẫu hợp lệ.
            if good:
                stats.update(obj)

    # 11.7. Dataset không được rỗng.
    if nonempty == 0:
        report.error(f"{path}: dataset rỗng")

    print(
        f"Đã đọc {name}: {nonempty:,} dòng có dữ liệu; "
        f"{stats.rows:,} mẫu hợp lệ"
    )

    return stats


# ============================================================
# 12. MAIN
# ============================================================

def main() -> int:

    parser = argparse.ArgumentParser(
        description="Kiểm tra dataset SmartHomePhoBERT"
    )

    # Chế độ kiểm tra một file hoặc nhiều split.
    sources = parser.add_mutually_exclusive_group()

    sources.add_argument(
        "--input",
        type=Path,
        help="Kiểm tra một file JSONL"
    )

    sources.add_argument(
        "--train",
        type=Path,
        help="File train (dùng thêm --validation/--test)"
    )

    parser.add_argument("--validation", type=Path)
    parser.add_argument("--test", type=Path)

    parser.add_argument(
        "--labels",
        type=Path,
        default=LABEL_FILE
    )

    parser.add_argument(
        "--seed-config",
        type=Path,
        default=SEED_FILE
    )

    parser.add_argument(
        "--no-template-check",
        action="store_true",
        help=(
            "Dành cho dữ liệu gán nhãn thủ công, "
            "không cần có template trong seed_config"
        )
    )

    parser.add_argument(
        "--strict-groups",
        action="store_true",
        help="Coi trùng template_group giữa các tập là lỗi"
    )

    parser.add_argument(
        "--warnings-as-errors",
        action="store_true"
    )

    parser.add_argument(
        "--max-messages",
        type=int,
        default=60
    )

    args = parser.parse_args()

    # 12.1. Kiểm tra các tham số.
    if args.max_messages < 0:
        parser.error("--max-messages phải >= 0")

    if (
        args.train is None
        and (args.validation is not None or args.test is not None)
    ):
        parser.error(
            "--validation và --test cần đi kèm --train"
        )

    # 12.2. Xác định các file cần kiểm tra.
    if args.train:

        paths = [
            ("train", args.train),
            ("validation", args.validation),
            ("test", args.test)
        ]

    else:
        paths = [
            ("input", args.input or DATA_FILE)
        ]

    paths = [
        (name, path)
        for name, path in paths
        if path is not None
    ]

    if len({p.resolve() for _, p in paths}) != len(paths):
        parser.error(
            "Các tập train/validation/test "
            "phải là những file khác nhau"
        )

    report = Report(args.max_messages)

    try:
        # 12.3. Đọc labels.json.
        intents, time_types = load_labels(args.labels)

        # 12.4. Đọc template catalog.
        if args.no_template_check:
            catalog, locations = None, set()
        else:
            catalog, locations = load_seed_catalog(
                args.seed_config,
                report
            )

        # 12.5. SQLite tạm dùng để chống trùng.
        # Database sẽ tự xóa khi kết thúc chương trình.
        with tempfile.TemporaryDirectory(
            prefix="validate_dataset_"
        ) as tmp:

            with sqlite3.connect(
                Path(tmp) / "seen.sqlite"
            ) as conn:

                conn.execute(
                    "CREATE TABLE ids ("
                    "id TEXT PRIMARY KEY, source TEXT)"
                )

                conn.execute(
                    "CREATE TABLE texts ("
                    "text TEXT PRIMARY KEY, "
                    "source TEXT, split TEXT)"
                )

                conn.execute(
                    "CREATE TABLE groups ("
                    "name TEXT PRIMARY KEY, split TEXT)"
                )

                conn.execute(
                    "CREATE TABLE group_alerts ("
                    "name TEXT, split TEXT, "
                    "PRIMARY KEY (name,split))"
                )

                # 12.6. Validate từng file.
                stats = [
                    validate_file(
                        path,
                        name,
                        conn,
                        report,
                        intents,
                        time_types,
                        catalog,
                        locations,
                        args.strict_groups
                    )
                    for name, path in paths
                ]

                conn.commit()

    except (
        OSError,
        UnicodeError,
        ValueError,
        SyntaxError,
        tokenize.TokenError,
        json.JSONDecodeError,
        sqlite3.Error
    ) as exc:

        print(
            f"FAILED: không thể đọc hoặc xử lý đầu vào: {exc}",
            file=sys.stderr
        )
        return 1

    # 12.7. In thống kê.
    for stat in stats:
        stat.show()

    # 12.8. In lỗi và cảnh báo.
    print(
        f"\nTổng lỗi: {report.counts['ERROR']}; "
        f"cảnh báo: {report.counts['WARN']}"
    )

    for message in report.messages:
        print(" -", message)

    omitted = (
        sum(report.counts.values())
        - len(report.messages)
    )

    if omitted:
        print(
            f"... còn {omitted:,} thông báo không in "
            "(dùng --max-messages để thay đổi)"
        )

    # 12.9. Quyết định PASS / FAILED.
    if (
        report.counts["ERROR"]
        or (
            args.warnings_as_errors
            and report.counts["WARN"]
        )
    ):
        print("FAILED: dữ liệu cần sửa trước khi train")
        return 1

    print(
        "PASS: schema, offset, BIO, template và "
        "trùng lặp đã vượt qua kiểm tra tự động"
    )

    print(
        "Lưu ý: PASS không đảm bảo các câu đã đúng "
        "ngữ nghĩa; vẫn cần kiểm tra thủ công."
    )

    return 0


# ============================================================
# 13. CHẠY CHƯƠNG TRÌNH
# ============================================================

if __name__ == "__main__":
    sys.exit(main())
