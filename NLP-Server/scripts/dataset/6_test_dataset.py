# Unit Test                     	    Mục đích
# test_original_data_passes	        Dataset gốc hợp lệ
# test_detects_bad_offset	        Phát hiện vị trí entity bị sai
# test_detects_duplicate_sentence	Phát hiện câu bị trùng
# test_split_groups_disjoint	    Kiểm tra việc chia Train/Validation/Test
# test_label_count	                Kiểm tra số nhãn của 3 head là 6, 3, 9



"""
UNIT TEST CHO GIAI ĐOẠN 2 - DATASET.

Kiểm tra:
    1. Dataset gốc hợp lệ.
    2. Phát hiện lỗi offset.
    3. Phát hiện câu trùng.
    4. Kiểm tra việc chia dataset.
    5. Kiểm tra số lượng nhãn.

Chạy:
    python scripts/6_test_dataset.py
"""

import copy
import json
import unittest

from validate_dataset import ROOT, load_jsonl, validate


# ============================================================
# CLASS: TestStage2
# ============================================================

class TestStage2(unittest.TestCase):

    # ========================================================
    # 1. CHUẨN BỊ DỮ LIỆU CHO CÁC BÀI TEST
    # ========================================================

    @classmethod
    def setUpClass(cls):

        # Đọc cấu hình nhãn.
        cls.labels = json.loads(
            (ROOT / "config/labels.json").read_text(
                encoding="utf-8"
            )
        )

        # Đọc bộ dataset gốc.
        cls.rows = load_jsonl(
            ROOT / "data/raw/smarthome_seed.jsonl"
        )

    # ========================================================
    # 2. KIỂM TRA DATASET GỐC HỢP LỆ
    # ========================================================

    def test_original_data_passes(self):

        errors = validate(
            self.rows,
            self.labels
        )

        # Dataset hợp lệ phải không có lỗi.
        self.assertEqual(errors, [])

    # ========================================================
    # 3. KIỂM TRA KHẢ NĂNG PHÁT HIỆN OFFSET SAI
    # ========================================================

    def test_detects_bad_offset(self):

        # Sao chép câu đầu tiên.
        modified = copy.deepcopy(self.rows[:1])

        # Cố tình sửa sai vị trí bắt đầu của entity.
        modified[0]["device_entities"][0]["start"] += 1

        # Kiểm tra dữ liệu đã sửa.
        errors = validate(
            modified,
            self.labels
        )

        # Validator phải phát hiện lỗi entity.
        self.assertTrue(
            any(
                "text entity" in error
                for error in errors
            ),
            errors
        )

    # ========================================================
    # 4. KIỂM TRA KHẢ NĂNG PHÁT HIỆN CÂU TRÙNG
    # ========================================================

    def test_detects_duplicate_sentence(self):

        # Tạo hai bản sao của cùng một câu.
        modified = [
            copy.deepcopy(self.rows[0]),
            copy.deepcopy(self.rows[0])
        ]

        # Đổi ID để chỉ kiểm tra lỗi trùng nội dung.
        modified[1]["id"] = "new_id"

        errors = validate(
            modified,
            self.labels
        )

        # Validator phải phát hiện câu trùng.
        self.assertTrue(
            any(
                "câu trùng" in error
                for error in errors
            ),
            errors
        )

    # ========================================================
    # 5. KIỂM TRA CHIA TRAIN / VALIDATION / TEST
    # ========================================================

    def test_split_groups_disjoint(self):

        groups = []
        counts = []

        # Duyệt ba tập dữ liệu.
        for name in ["train", "validation", "test"]:

            # Đọc dataset.
            rows = load_jsonl(
                ROOT / f"data/splits/{name}.jsonl"
            )

            # Kiểm tra mỗi tập có hợp lệ không.
            self.assertEqual(
                validate(rows, self.labels),
                []
            )

            # Lưu tập hợp template_group.
            groups.append({
                row["template_group"]
                for row in rows
            })

            # Lưu số lượng câu.
            counts.append(len(rows))

        # Tổng số câu của ba tập phải bằng dataset gốc.
        self.assertEqual(
            sum(counts),
            len(self.rows)
        )

        # Không được có template_group trùng
        # giữa hai tập bất kỳ.
        for i in range(3):
            for j in range(i + 1, 3):

                self.assertFalse(
                    groups[i] & groups[j]
                )

    # ========================================================
    # 6. KIỂM TRA SỐ LƯỢNG NHÃN
    # ========================================================

    def test_label_count(self):

        # Đọc file ánh xạ nhãn.
        maps = json.loads(
            (ROOT / "config/label_maps.json").read_text(
                encoding="utf-8"
            )
        )

        # Đếm số lượng nhãn của từng nhiệm vụ.
        counts = tuple(
            len(maps[f"{name}2id"])
            for name in ["intent", "tag", "time"]
        )

        # Phải có đúng 6, 3, 9 nhãn.
        self.assertEqual(
            counts,
            (6, 3, 9)
        )


# ============================================================
# 7. CHẠY UNIT TEST
# ============================================================

if __name__ == "__main__":
    unittest.main(verbosity=2)
