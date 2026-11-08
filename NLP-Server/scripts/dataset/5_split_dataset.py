
"""
FILE: scripts/5_split_dataset.py

MỤC ĐÍCH:
    Chia dataset đã được validate thành 3 tập:
        Train       : 70%
        Validation  : 15%
        Test        : 15%

PHƯƠNG PHÁP:
    Greedy Group Split + Random Restarts.

QUY TRÌNH:
    1. Đọc dataset nguồn.
    2. Gom các câu theo template_group.
    3. Xáo trộn thứ tự các group.
    4. Lần lượt phân bổ từng group bằng Greedy.
    5. Lặp lại với 100 lần xáo trộn khác nhau.
    6. Chọn phương án có tổng sai lệch nhỏ nhất.
    7. Ghi kết quả ra 3 file JSONL.

RÀNG BUỘC:
    - Không chia nhỏ một template_group.
    - Cả 3 tập phải có dữ liệu.
    - Train phải có tất cả loại Intent.
    - Train phải có Device TAG nếu dataset có TAG.
    - Train phải có tất cả loại Schedule entity.

CHẠY:
    python scripts/5_split_dataset.py

    Hoặc:
    python scripts/5_split_dataset.py --trials 100 --seed 42
"""

from __future__ import annotations


# ============================================================
# 1. IMPORT THƯ VIỆN
# ============================================================

# argparse:
# Thư viện chuẩn Python để nhận tham số từ Terminal.
# Ví dụ: python script.py --seed 42
import argparse

# Counter:
# Dictionary chuyên dùng để đếm số lần xuất hiện.
#
# defaultdict:
# Dictionary tự tạo giá trị mặc định cho key mới.
#
# Cả hai đều thuộc thư viện chuẩn collections.
from collections import Counter, defaultdict

import json

# random:
# Thư viện chuẩn dùng để sinh số giả ngẫu nhiên.
# Ta dùng random.Random(seed) để tái lập kết quả.
import random

# Path:
# Class thuộc pathlib, dùng để thao tác đường dẫn.
# Có thể nối đường dẫn bằng toán tử /.
from pathlib import Path


# 2. CẤU HÌNH
ROOT = Path(__file__).resolve().parents[1]


# File dataset nguồn đã được validate.
DATA_FILE = ROOT / "data" / "raw" / "smarthome_seed.jsonl"


# Thư mục lưu kết quả sau khi chia.
OUT = ROOT / "data" / "splits"


# Tên của ba tập dữ liệu.
SPLITS = ("train", "validation", "test")


# Tỷ lệ chia mong muốn.
RATIOS = {
    "train": 0.70,
    "validation": 0.15,
    "test": 0.15,
}

# Seed giúp kết quả random có thể tái lập.
SEED = 42

# Số lần thử các phương án chia khác nhau.
TRIALS = 100

# 3. ĐỌC DATASET JSONL
def load_jsonl(path: Path) -> list[dict]:
    """
    MỤC ĐÍCH:
        Đọc file JSONL thành danh sách các mẫu dữ liệu.

    INPUT:
        path: đường dẫn file JSONL.

    OUTPUT:
        list[dict]: danh sách các mẫu.

    LƯU Ý:
        Không kiểm tra lại schema hoặc offset.
        Dữ liệu đã được validate ở bước trước.
    """

    # Danh sách chứa các câu được đọc.
    examples = []

    # with:
    # Context manager giúp tự động đóng file
    # khi kết thúc khối lệnh.
    with path.open("r", encoding="utf-8") as stream:

        # Đọc lần lượt từng dòng.
        for line in stream:

            # strip():
            # Xóa khoảng trắng ở hai đầu chuỗi. Nếu dòng không rỗng thì xử lý.
            if line.strip():
                examples.append(json.loads(line))

    # Không cho phép dataset rỗng.
    if not examples:
        raise ValueError(f"Dataset rỗng: {path}")

    return examples


# 4. GOM CÂU THEO TEMPLATE_GROUP
def group_examples(examples: list[dict]) -> dict[str, list[dict]]:
    """
    MỤC ĐÍCH:
        Gom tất cả câu có cùng template_group.

    Ví dụ:
        ex_001 -> on_now_01
        ex_002 -> on_now_01
        ex_003 -> off_now_01

    Kết quả:
        {
            "on_now_01": [ex_001, ex_002],
            "off_now_01": [ex_003]
        }

    Mỗi group sẽ được phân bổ nguyên vẹn
    vào một trong ba tập Train/Validation/Test.
    """

    # defaultdict(list):
    # Khi truy cập một key chưa tồn tại,
    # Python sẽ tự tạo list rỗng [] cho key đó.
    grouped = defaultdict(list)

    # Duyệt qua tất cả mẫu dữ liệu.
    for row in examples:

        # Lấy tên group của câu hiện tại.
        group_name = row["template_group"]

        # Thêm một phần tử vào cuối list.
        grouped[group_name].append(row)

    # dict():
    # Chuyển defaultdict về dictionary thông thường.
    return dict(grouped)


# 5. LẤY CÁC LOẠI NHÃN CÓ TRONG DATASET
def label_coverage(examples: list[dict]) -> tuple[set[str], set[str], bool]:
    """
    MỤC ĐÍCH:
        Xác định các loại nhãn có trong dataset.

    Trả về:
        1. Tập Intent.
        2. Tập loại Schedule entity.
        3. Dataset có Device TAG hay không.

    Ví dụ:
        (
            {"TURN_ON", "TURN_OFF"},
            {"DURATION", "SCHEDULED_DELAY"},
            True
        )

    Hàm này chỉ phục vụ kiểm tra Train có đủ
    loại nhãn cần học, KHÔNG cân bằng tần suất nhãn.
    """

    # Set comprehension:
    # {expression for item in iterable}
    #
    # Tạo tập hợp chứa các phần tử duy nhất.
    # Các Intent trùng nhau sẽ tự bị loại.
    intents = {
        row["intent"]
        for row in examples
    }

    # Lấy toàn bộ loại Schedule entity.
    #
    # Đây là vòng for lồng nhau:
    # Duyệt từng câu, sau đó duyệt từng entity.
    schedule_types = {
        entity["type"]
        for row in examples
        for entity in row["schedule_entities"]
    }

    # any():
    # Trả về True nếu ít nhất một phần tử là True.
    #
    # List rỗng [] được xem là False.
    # List có phần tử được xem là True.
    #
    # Do đó, dòng này kiểm tra dataset có
    # ít nhất một câu chứa Device TAG hay không.
    has_device = any(
        row["device_entities"]
        for row in examples
    )

    return intents, schedule_types, has_device


# 6. TÍNH TỔNG SAI LỆCH SO VỚI TỶ LỆ MỤC TIÊU
def total_error(parts: dict[str, list[dict]],targets: dict[str, float]) -> float:
    """
    MỤC ĐÍCH:
        Tính tổng sai lệch số câu của ba tập
        so với số câu mục tiêu.

    CÔNG THỨC: E = |Train - TargetTrain| + |Validation - TargetValidation| + |Test - TargetTest|

    Ví dụ:
        Mục tiêu: 125 / 27 / 26
        Thực tế:  110 / 25 / 30

        E = |110-125| + |25-27| + |30-26|
          = 15 + 2 + 4
          = 21

    E càng nhỏ thì phương án càng tốt
    về mặt số lượng câu.
    """
    return sum(
        abs(len(parts[split]) - targets[split])
        for split in SPLITS
    )


# 7. GREEDY: CHIA DATASET MỘT LẦN
def greedy_once(
    items: list[tuple[str, list[dict]]],
    targets: dict[str, float],
    rng: random.Random,
) -> dict[str, list[dict]]:
    """
    MỤC ĐÍCH:
        Chia toàn bộ template_group thành ba tập
        bằng thuật toán Greedy.

    NGUYÊN TẮC:
        Với mỗi group:
            1. Giả sử thêm vào Train.
            2. Giả sử thêm vào Validation.
            3. Giả sử thêm vào Test.
            4. Tính tổng sai lệch ở mỗi phương án.
            5. Chọn tập có sai lệch nhỏ nhất.
            6. Đưa toàn bộ group vào tập đó.

    INPUT:
        items:
            Danh sách các cặp:
                (template_group, danh_sách_câu)

        targets:
            Số câu mục tiêu của mỗi tập.

        rng:
            Bộ sinh ngẫu nhiên, dùng xử lý hòa điểm.

    OUTPUT:
        Dictionary chứa ba tập dữ liệu.
    """

    # 7.1. Tạo ba tập rỗng.
    #
    # Dictionary comprehension:
    # {key: value for key in iterable}
    #
    # Mỗi split có một list riêng.
    parts = {
        split: []
        for split in SPLITS
    }

    # 7.2. Duyệt các group theo thứ tự đã xáo trộn.
    for group_name, rows in items:

        # Số câu thuộc group hiện tại.
        group_size = len(rows)

        # ----------------------------------------------------
        # 7.3. HÀM TÍNH SAI LỆCH GIẢ ĐỊNH
        # ----------------------------------------------------
        def error_if_added(candidate: str) -> float:
            """
            Giả sử đưa group hiện tại vào tập candidate.

            Chỉ tính toán sai lệch, KHÔNG thay đổi
            dữ liệu thật trong parts.

            Ví dụ candidate = "train":
                Train tăng thêm group_size.
                Validation giữ nguyên.
                Test giữ nguyên.
            """

            return sum(
                abs(
                    # Số câu đang có trong tập.
                    len(parts[split])

                    # Nếu đang xét đúng tập candidate
                    # thì cộng thêm số câu của group.
                    #
                    # A if condition else B:
                    # Biểu thức điều kiện trong Python.
                    + (
                        group_size
                        if split == candidate
                        else 0
                    )

                    # Trừ đi số câu mục tiêu.
                    - targets[split]
                )

                for split in SPLITS
            )

        # ----------------------------------------------------
        # 7.4. THỬ CẢ BA TẬP
        # ----------------------------------------------------
        # Tạo dictionary:
        # {
        #     "train": error_if_added("train"),
        #     "validation": error_if_added("validation"),
        #     "test": error_if_added("test")
        # }
        errors = {
            split: error_if_added(split)
            for split in SPLITS
        }

        # min():
        # Lấy giá trị nhỏ nhất trong các sai lệch.
        smallest = min(errors.values())

        # ----------------------------------------------------
        # 7.5. XỬ LÝ TRƯỜNG HỢP CÓ NHIỀU TẬP HÒA ĐIỂM
        # ----------------------------------------------------
        # Một số phương án có thể cho sai lệch bằng nhau.
        #
        # 1e-9:
        # Dung sai rất nhỏ khi so sánh số thực.
        #
        # Ta lấy tất cả tập có điểm gần bằng
        # sai lệch nhỏ nhất.
        tied_splits = [
            split
            for split in SPLITS
            if abs(errors[split] - smallest) < 1e-9
        ]

        # rng.choice():
        # Chọn ngẫu nhiên một phần tử từ list.
        #
        # Nếu chỉ có một tập tốt nhất,
        # nó sẽ được chọn.
        #
        # Nếu nhiều tập hòa điểm,
        # random giúp tạo thêm phương án khác nhau.
        chosen = rng.choice(tied_splits)

        # ----------------------------------------------------
        # 7.6. THÊM NGUYÊN GROUP VÀO TẬP ĐƯỢC CHỌN
        # ----------------------------------------------------

        # extend(rows):
        # Thêm từng phần tử trong rows vào list.
        #
        # Khác với append(rows):
        # append sẽ thêm nguyên list như một phần tử.
        parts[chosen].extend(rows)

    # Trả về ba tập sau khi chia toàn bộ group.
    return parts


# 8. KIỂM TRA MỘT PHƯƠNG ÁN CHIA CÓ CHẤP NHẬN ĐƯỢC KHÔNG
def acceptable(
    parts: dict[str, list[dict]],
    required: tuple[set[str], set[str], bool],
) -> bool:
    """
    MỤC ĐÍCH:
        Kiểm tra các điều kiện bắt buộc sau khi chia.

    Điều kiện:
        1. Train không rỗng.
        2. Validation không rỗng.
        3. Test không rỗng.
        4. Train chứa toàn bộ loại Intent.
        5. Train chứa toàn bộ loại Schedule.
        6. Train có TAG nếu dataset có Device TAG.

    OUTPUT:
        True: phương án hợp lệ.
        False: phương án không hợp lệ.
    """

    # Nếu bất kỳ tập nào rỗng thì loại.
    if any(not parts[split] for split in SPLITS):
        return False

    # Lấy những loại nhãn thực tế trong Train.
    train_intents, train_times, train_has_device = (label_coverage(parts["train"]))

    # Tuple unpacking:
    # Gán lần lượt các phần tử của tuple
    # vào ba biến riêng biệt.
    all_intents, all_times, has_device = required

    # issubset():
    # Phương thức của set.
    #
    # A.issubset(B) trả True nếu mọi phần tử
    # trong A đều nằm trong B.
    #
    # Ví dụ:
    # {"A", "B"}.issubset({"A", "B", "C"})
    # -> True

    return (
        all_intents.issubset(train_intents)
        and all_times.issubset(train_times)
        and (not has_device or train_has_device)
    )


# 9. RANDOM RESTARTS: THỬ NHIỀU PHƯƠNG ÁN
def find_best_split(
    examples: list[dict],
    grouped: dict[str, list[dict]],
    trials: int,
    seed: int,
) -> tuple[dict[str, list[dict]], float, int]:
    """
    MỤC ĐÍCH:
        Thực hiện Greedy nhiều lần với các thứ tự
        template_group khác nhau.

    QUY TRÌNH:
        1. Tính số câu mục tiêu.
        2. Khởi tạo bộ sinh ngẫu nhiên.
        3. Xáo trộn thứ tự group.
        4. Chia bằng Greedy.
        5. Loại phương án vi phạm ràng buộc.
        6. Tính tổng sai lệch cuối cùng.
        7. Giữ phương án có sai lệch nhỏ nhất.
        8. Lặp lại đủ trials lần.

    OUTPUT:
        best_parts:
            Ba tập của phương án tốt nhất.

        best_error:
            Tổng sai lệch nhỏ nhất.

        valid_trials:
            Số phương án đáp ứng ràng buộc.
    """

    # 9.1. Tạo bộ sinh số ngẫu nhiên.
    #
    # random.Random(seed):
    # Khởi tạo bộ sinh số giả ngẫu nhiên độc lập.
    #
    # Cùng seed, cùng dữ liệu và thuật toán
    # sẽ tạo cùng chuỗi lựa chọn ngẫu nhiên.
    rng = random.Random(seed)

    # 9.2. Tính số câu mục tiêu.
    #
    # Ví dụ dataset = 178:
    #
    # Train      = 178 * 0.70 = 124.6
    # Validation = 178 * 0.15 = 26.7
    # Test       = 178 * 0.15 = 26.7
    #
    # Giữ số thực để tính độ lệch chính xác.
    targets = {
        split: len(examples) * RATIOS[split]
        for split in SPLITS
    }

    # 9.3. Lấy những loại nhãn cần có trong Train.
    required = label_coverage(examples)

    # 9.4. Khởi tạo biến lưu phương án tốt nhất.
    best_parts = None

    # float("inf"):
    # Biểu diễn số dương vô cực.
    #
    # Bất kỳ sai lệch hữu hạn nào cũng nhỏ hơn inf.
    best_error = float("inf")

    # Đếm số lượt chia hợp lệ.
    valid_trials = 0

    # --------------------------------------------------------
    # 9.5. THỰC HIỆN NHIỀU LẦN GREEDY
    # --------------------------------------------------------

    for _ in range(trials):

        # _:
        # Tên biến quy ước khi không sử dụng
        # giá trị của biến lặp.

        # dict.items():
        # Trả về các cặp (key, value).
        #
        # list():
        # Chuyển sang list để có thể xáo trộn.
        items = list(grouped.items())

        # rng.shuffle():
        # Xáo trộn list ngay tại chỗ.
        #
        # Không làm thay đổi thứ tự các câu
        # bên trong từng template_group.
        rng.shuffle(items)

        # Chạy Greedy với thứ tự group mới.
        parts = greedy_once(items, targets, rng)

        # ----------------------------------------------------
        # 9.6. LOẠI NHỮNG PHƯƠNG ÁN KHÔNG HỢP LỆ
        # ----------------------------------------------------
        if not acceptable(parts, required):

            # continue:
            # Bỏ qua phần còn lại của lượt lặp
            # và chuyển sang lượt tiếp theo.
            continue

        valid_trials += 1

        # ----------------------------------------------------
        # 9.7. TÍNH TỔNG SAI LỆCH SAU KHI CHIA
        # ----------------------------------------------------
        error = total_error(parts, targets)

        # ----------------------------------------------------
        # 9.8. CẬP NHẬT PHƯƠNG ÁN TỐT NHẤT
        # ----------------------------------------------------
        if error < best_error:

            best_error = error
            best_parts = parts

    # --------------------------------------------------------
    # 9.9. KIỂM TRA CÓ TÌM ĐƯỢC PHƯƠNG ÁN HỢP LỆ KHÔNG
    # --------------------------------------------------------
    if best_parts is None:
        raise ValueError(
            "Không tìm được phương án chia hợp lệ. "
            "Hãy thử tăng --trials hoặc kiểm tra "
            "phân bố nhãn theo template_group."
        )

    return best_parts, best_error, valid_trials


# 10. KIỂM TRA KẾT QUẢ SAU KHI CHIA

def check_split(
    examples: list[dict],
    parts: dict[str, list[dict]]
) -> None:
    """
    MỤC ĐÍCH:
        Đảm bảo quá trình chia không:
            - Làm mất câu.
            - Nhân đôi câu.
            - Đưa cùng template_group vào nhiều tập.

    Đây là kiểm tra tính toàn vẹn của phép chia,
    không phải validate lại dataset nguồn.
    """

    # 10.1. Đếm ID trong dataset nguồn.
    #
    # Counter(iterable):
    # Trả dictionary đếm số lần xuất hiện mỗi giá trị.
    original_ids = Counter(
        row["id"]
        for row in examples
    )

    # 10.2. Đếm ID trong cả ba tập sau chia.
    output_ids = Counter(
        row["id"]
        for split in SPLITS
        for row in parts[split]
    )

    # So sánh hai Counter.
    #
    # Nếu một ID bị mất hoặc xuất hiện thêm,
    # hai Counter sẽ khác nhau.
    if original_ids != output_ids:
        raise RuntimeError(
            "Lỗi chia: mất câu hoặc nhân đôi ID."
        )

    # 10.3. Kiểm tra template_group không chồng lấn.
    seen_groups = set()

    for split in SPLITS:

        # Lấy toàn bộ tên group trong tập.
        groups_here = {
            row["template_group"]
            for row in parts[split]
        }

        # Toán tử & giữa hai set:
        # Tính giao của hai tập hợp.
        #
        # Nếu giao khác rỗng, có group trùng.
        if seen_groups & groups_here:
            raise RuntimeError(
                "Lỗi chia: template_group nằm ở nhiều tập."
            )

        # set.update():
        # Thêm toàn bộ phần tử của tập khác.
        seen_groups.update(groups_here)


# 11. GHI BA TẬP DỮ LIỆU VÀ THỐNG KÊ
def write_splits(
    parts: dict[str, list[dict]],
    output: Path
) -> None:
    """
    MỤC ĐÍCH:
        Ghi ba file:
            train.jsonl
            validation.jsonl
            test.jsonl

    Đồng thời in:
        - Số câu và tỷ lệ thực tế.
        - Số template_group.
        - Phân phối Intent.
        - Phân phối Schedule.
        - Phân phối số Device TAG trong mỗi câu.
    """

    # mkdir():
    # Tạo thư mục.
    #
    # parents=True:
    # Tạo cả các thư mục cha nếu cần.
    #
    # exist_ok=True:
    # Không báo lỗi nếu thư mục đã tồn tại.
    output.mkdir(parents=True, exist_ok=True)

    # Tổng số câu trong cả ba tập.
    total = sum(
        len(parts[split])
        for split in SPLITS
    )

    # --------------------------------------------------------
    # 11.1. DUYỆT BA TẬP
    # --------------------------------------------------------

    for split in SPLITS:

        # sorted():
        # Tạo list mới đã được sắp xếp.
        #
        # key=lambda row: row["id"]:
        # Dùng ID làm khóa sắp xếp.
        #
        # lambda:
        # Cú pháp định nghĩa hàm ngắn gọn.
        #
        # Tương đương:
        # def get_id(row):
        #     return row["id"]
        rows = sorted(
            parts[split],
            key=lambda row: row["id"]
        )

        # Xác định đường dẫn file đích.
        destination = output / f"{split}.jsonl"

        # ----------------------------------------------------
        # 11.2. GHI JSONL
        # ----------------------------------------------------

        with destination.open(
            "w",
            encoding="utf-8",
            newline="\n"
        ) as stream:

            for row in rows:

                # json.dumps():
                # Chuyển Python object thành JSON string.
                #
                # ensure_ascii=False:
                # Giữ nguyên ký tự tiếng Việt.
                #
                # + "\n":
                # Mỗi JSON object được ghi trên một dòng.
                stream.write(
                    json.dumps(
                        row,
                        ensure_ascii=False
                    ) + "\n"
                )

        # ----------------------------------------------------
        # 11.3. THỐNG KÊ INTENT
        # ----------------------------------------------------

        intent_counts = Counter(
            row["intent"]
            for row in rows
        )

        # ----------------------------------------------------
        # 11.4. THỐNG KÊ SCHEDULE
        # ----------------------------------------------------

        time_counts = Counter(
            entity["type"]
            for row in rows
            for entity in row["schedule_entities"]
        )

        # ----------------------------------------------------
        # 11.5. THỐNG KÊ SỐ DEVICE TAG TRÊN MỖI CÂU
        # ----------------------------------------------------

        # Ví dụ:
        # {
        #     1: 50,  # 50 câu có 1 TAG
        #     2: 30,  # 30 câu có 2 TAG
        #     3: 15   # 15 câu có 3 TAG
        # }
        device_counts = Counter(
            len(row["device_entities"])
            for row in rows
        )

        # ----------------------------------------------------
        # 11.6. ĐẾM SỐ TEMPLATE_GROUP
        # ----------------------------------------------------

        group_count = len({
            row["template_group"]
            for row in rows
        })

        # ----------------------------------------------------
        # 11.7. IN KẾT QUẢ
        # ----------------------------------------------------

        # :.2%:
        # Định dạng số thực dưới dạng phần trăm,
        # lấy 2 chữ số sau dấu phẩy.
        print(
            f"\n{split.upper()}: "
            f"{len(rows)} câu "
            f"({len(rows) / total:.2%}), "
            f"{group_count} group"
        )

        print(
            "  Intent:",
            dict(sorted(intent_counts.items()))
        )

        print(
            "  Schedule:",
            dict(sorted(time_counts.items()))
        )

        print(
            "  Số TAG/câu:",
            dict(sorted(device_counts.items()))
        )

        print(f"  File: {destination}")


# 12. HÀM MAIN
def main() -> None:
    """
    MỤC ĐÍCH:
        Điều phối toàn bộ chương trình.

    THỨ TỰ:
        1. Nhận tham số dòng lệnh.
        2. Đọc dataset nguồn.
        3. Gom câu theo template_group.
        4. Tìm phương án tốt nhất.
        5. Kiểm tra kết quả.
        6. Ghi ba file JSONL.
        7. In thống kê.
    """

    # --------------------------------------------------------
    # 12.1. KHỞI TẠO ARGUMENT PARSER
    # --------------------------------------------------------
    parser = argparse.ArgumentParser(description="Greedy Group Split cho SmartHomePhoBERT")

    # File dataset đầu vào.
    parser.add_argument(
        "--input",
        type=Path,
        default=DATA_FILE
    )

    # Thư mục lưu kết quả.
    parser.add_argument(
        "--output",
        type=Path,
        default=OUT
    )

    # Số lượt thử.
    parser.add_argument(
        "--trials",
        type=int,
        default=TRIALS
    )

    # Seed ngẫu nhiên.
    parser.add_argument(
        "--seed",
        type=int,
        default=SEED
    )

    # parse_args():
    # Đọc các tham số được truyền từ Terminal.
    args = parser.parse_args()

    # Số lượt thử phải là số nguyên dương.
    if args.trials < 1:
        parser.error("--trials phải >= 1")

    # --------------------------------------------------------
    # 12.2. ĐỌC DATASET
    # --------------------------------------------------------
    examples = load_jsonl(args.input)

    # --------------------------------------------------------
    # 12.3. GOM THEO TEMPLATE_GROUP
    # --------------------------------------------------------
    grouped = group_examples(examples)

    # Cần tối thiểu 3 group để chia thành
    # 3 tập không rỗng.
    if len(grouped) < 3:
        raise ValueError(
            "Cần ít nhất 3 template_group "
            "để tạo 3 tập không rỗng."
        )

    # --------------------------------------------------------
    # 12.4. TÌM PHƯƠNG ÁN TỐT NHẤT
    # --------------------------------------------------------
    parts, best_error, valid_trials = find_best_split(
        examples,
        grouped,
        args.trials,
        args.seed
    )

    # --------------------------------------------------------
    # 12.5. KIỂM TRA TÍNH TOÀN VẸN
    # --------------------------------------------------------
    check_split(examples, parts)

    # --------------------------------------------------------
    # 12.6. IN THÔNG TIN TỔNG QUÁT
    # --------------------------------------------------------
    print(
        f"Dataset: {len(examples)} câu, "
        f"{len(grouped)} template_group"
    )

    print(
        f"Số lượt chia hợp lệ: "
        f"{valid_trials}/{args.trials}"
    )

    print(
        f"Tổng sai lệch nhỏ nhất: "
        f"{best_error:.2f} câu"
    )

    # --------------------------------------------------------
    # 12.7. GHI BA TẬP DỮ LIỆU
    # --------------------------------------------------------
    write_splits(parts, args.output)

    print("\nPASS: Không mất câu, không trùng template_group.")

    print("PASS: Train có đủ các loại nhãn cần học.")


if __name__ == "__main__":
    main()
