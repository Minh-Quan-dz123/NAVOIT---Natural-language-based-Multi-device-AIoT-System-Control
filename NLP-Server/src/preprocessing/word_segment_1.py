"""
Nhiệm vụ:
(Model đã được lưu tại D:/vncorenlp)

ví dụ : Input1 = "Bật đèn phòng khách sau 10 phút"

=> B1: phân đoạn từ: 
    input1 => output1 = "Bật đèn phòng_khách sau 10 phút"

=> B2: tách thành danh sách từ bằng split()
    input2 = output1 => Output2 ["Bật", "đèn", "phòng_khách",...]

=> B3: xác định offsets dạng :     Token           Start    End     Original

- token: ["Bật"] => [0, 3]  : Bật
- token: ["đèn"] => [4, 7]  : đèn
- token: ["phòng_khách"] => [8, 19]: phòng khách
"""

import unicodedata
import py_vncorenlp
from dataclasses import dataclass
from pathlib import Path

# 1 ĐỊNH NGHĨA CẤU TRÚC DỮ LIỆU
# @dataclass: Tự động tạo __init__, __repr__, __eq__.
# frozen=True: Không cho phép sửa các thuộc tính sau khi khởi tạo.

@dataclass(frozen=True) # ko bắt buộc dùng cái này
class SegmentedWord:
    value: str # phòng_khách
    start: int # 8
    end: int   # 19

@dataclass(frozen=True)
class SegmentedText:
    original: str # "Bật đèn phòng khách sau 10 phút", # sau khi được chuẩn hóa dấu cách
    segmented: str # "Bật đèn phòng_khách sau 10 phút",
    words: list[SegmentedWord] # Danh sách từ và offset của chúng

# 2. Class chính
class WordSegmenter:

    # 1. hàm khởi tạo {model_dir, model}
    def __init__(self, model_dir: str = "D:/vncorenlp"):

        # 1. gán model
        self.model_dir = Path(model_dir).resolve()

        # 2. kiểm tra jar đã tồn tại chưa
        jar_file = self.model_dir/"VnCoreNLP-1.2.jar"
        # "/" là cú pháp ghép path của toán tử có trong thư viện path
        if not jar_file.is_file():
            raise FileNotFoundError(f"ko tìm thấy VnCoreNLP file tại: {jar_file}")

        # 3 khởi tạo mô hình từ các file trên ổ đĩa
        # annotators = ["wseg"]: chỉ kích hoạt word segmentation
        # save_dir: vị trí chứa file JAR và thư mục model
        # lệnh này load model và RAM, ko download từ mạng
        self.model = py_vncorenlp.VnCoreNLP(annotators=["wseg"], save_dir=str(self.model_dir))

    # 2. Phân đoạn từ
    def segment(self, text:str) -> SegmentedText:
        # B2.1 Kiểm tra đầu vào 
        # kiểm tra kiểu dữ liệu của một biến 
        if not isinstance(text, str) :
            raise ValueError("Text phải là kiểu dữ liệu chuỗi")
        elif not text.strip():
            raise ValueError("Text ko được rỗng")

        # chuẩn hóa NFC 
        text = unicodedata.normalize("NFC", text)
        if not unicodedata.is_normalized("NFC", text):
            raise ValueError("Text chưa được chuẩn hóa NFC. ")


        # B2.2. Đưa vào VnCoreNLP để thêm "_"
        sentences = self.model.word_segment(text)
        # Kết quả là list[str], mỗi phần tử là một CÂU, chứ ko phải 1 từ

        # B2.3. tách kết quả thành danh sách
        # split(): Tách kết quả thành danh sách từng từ
        tokens = []
        for sentence_i in sentences:
            for token in sentence_i.split():
                tokens.append(token)

        if not tokens:
            raise ValueError("VnCoreNLP ko trả về token")

        # B2.4.tính offset theo 1 dấu cách
        words: list[SegmentedWord] = []
        cursor = 0 # vị trí bắt đầu tìm kiếm tiếp theo\
        segmented_text:str = ""
        original_chuanhoa: str = ""
        for token_i in tokens:

            segmented_text += token_i + " "
            original_chuanhoa += token_i.replace("_", " ")+ " "

            cursor_then = cursor + len(token_i)

            words.append(SegmentedWord(
                value=token_i,
                start=cursor,
                end=cursor_then
                ))
            
            cursor = cursor_then+1
            # câu gốc sau khi đã được chuẩn hóa
        
        # Xóa khoảng trắng ở cuối
        segmented_text = segmented_text.rstrip()
        original_chuanhoa = original_chuanhoa.rstrip()

        # B2.5 trả kết quả
        return SegmentedText(
            original = original_chuanhoa,
            segmented=segmented_text,
            words=words
        )

# 3. CHẠY KIỂM THỬ ĐỘC LẬP
if __name__ == "__main__":
    # khởi tạo model 1 lần
    segmenter = WordSegmenter()

    # test
    test_texts = [
        "Ông Nguyễn Khắc   Chúc đang làm việc tại Đại  học Hà Nội .",
        "Bật đèn phòng  khách sau 10 phút !",
        "Hãy bật điều hòa trong, phòng ngủ và tắt quạt trần?",
        "hãy tính 5!."
    ]

    for text in test_texts:
        result = segmenter.segment(text)

        print("\n" + "=" * 75)
        print("WORD SEGMENTATION RESULT")
        print("=" * 75)

        print(f"\nOriginal  : {result.original}")
        print(f"Segmented : {result.segmented}")

        print("\n" + "-" * 75)
        print(f"{'STT':<5} {'TOKEN':<25} {'START':<8} {'END':<8} ORIGINAL")
        print("-" * 75)

        for i, word in enumerate(result.words, start=1):
            original = result.original[word.start:word.end]

            print(
                f"{i:<5} "
                f"{word.value:<25} "
                f"{word.start:<8} "
                f"{word.end:<8} "
                f"{original}"
            )

        print("-" * 75)
        print(f"Total words: {len(result.words)}")


