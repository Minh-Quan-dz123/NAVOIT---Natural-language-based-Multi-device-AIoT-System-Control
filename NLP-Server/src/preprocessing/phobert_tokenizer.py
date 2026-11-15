# file này nhận kết quả segmentedText từ VnCoreNLP rồi chuyển
# thành dữ liệu để PhoBERT xử lý
# TokenizedText:
# input_ids: các ID đưa vào PhoBERT
# attention_mask: vị trí các token hợp lệ
# tokens: Danh sách token sau BPE, gồm special tokens
# word_ids: Cho biết token thuộc từ thứ mấy
# words: Danh sách từ kèm vị trí bắt đầu, kết thúc

from dataclasses import dataclass
from transformers import AutoTokenizer
# AutoTokenizer là một class giúp tự động xác định và tải tokenizer 
# phù hợp với mô hình mà mày chọn.

from src.preprocessing.word_segment_1 import (SegmentedText, SegmentedWord)

# 1. ĐỊNH NGHĨA CẤU TRÚC OUTPUT
@dataclass(frozen=True)
class TokenizedText:
    original: str   # Văn bản được tái tạo bởi WordSegmenter.
    segmented: str  # bật đền phòng_khách
    words: list[SegmentedWord]

    tokens: list[str] # Danh sách token, bao gồm <s> và </s>
    input_ids: list[int] # id của token đó trong vocabulary
    attention_mask: list[int] # 1 = token hợp lệ, 0 = padding
    word_ids: list[int | None]  # Mỗi subword thuộc word nào, None = special token (<s>, </s>).

# 2. CLASS PHOBERT TOKENIZER
class PhoBERTTokenizer:
    # 2.1. khởi tạo tokenizer
    def __init__(self, model_name: str = "vinai/phobert-base-v2", max_length: int = 256):
        # Kiểm tra giới hạn độ dài
        if not isinstance(max_length, int) or not 3 <= max_length <= 256:
            raise ValueError("max_length phải là số nguyên từ 3 đến 256")

        self.model_name = model_name
        self.max_length = max_length

        # load tokenizer pretrained từ hugging face
        # use_fast=False: sử dụng PhoBERT slow tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=False)

        # kiểm tra special tokens
        if(self.tokenizer.cls_token_id is None
           or self.tokenizer.sep_token_id is None):
            raise ValueError("Tokenizer phải có CLS và SEP token")

    # hàm chuyển segmented text thành tokenized text
    def encode(self, segmented_text: SegmentedText) -> TokenizedText:
            # Input: SegmentedText(original, segmented, words)

            # B1. kiểm tra input
            if not isinstance(segmented_text, SegmentedText):
                raise TypeError("encode() yêu cầu đối tượng SegmentedText nhá")

            if not segmented_text.words:
                raise ValueError("Danh sách words rỗng")

            # kiểm tra segmented và original có giống ban đầu ko
            # Tái tạo lại segmented và original từ danh sách words
            reconstructed_segmented = " ".join(word.value for word in segmented_text.words)
            reconstructed_original = " ".join(word.value.replace("_", " ") for word in segmented_text.words)

            if segmented_text.segmented != reconstructed_segmented:
                raise ValueError("segmented ko khớp với words")
            if segmented_text.original != reconstructed_original:
                raise ValueError("original ko khớp với words")

            # kiểm tra xem vị trí bắt đầu (start) và kết thúc (end) của từng từ trong câu 
            # gốc có chính xác hay không.
            for index, word in enumerate(segmented_text.words):
                if(word.start < 0 or word.end <= word.start or word.end > len(segmented_text.original)):
                    raise ValueError(f"word {index} có offset ngoài phạm vi")

                if word.value.replace("_", " ") != segmented_text.original[word.start:word.end]:
                    raise ValueError(f"word {index} có offset sai: " 
                                     f"{word.value.replace('_', ' ')} != {segmented_text.original[word.start:word.end]}")

            # B2 sau đủ loại kiểm tra input thì đến bước BPE TOKENIZATION
            # BPE (Byte Pair Encoding) là thuật toán dùng để chia văn bản thành các đơn vị nhỏ gọi là subword. 
            # Đây là thuật toán tokenization được PhoBERT sử dụng.

            # Danh sách subword của toàn bộ câu
            subwords: list[str] = []
            subword_word_ids: list[int] = [] # ánh xạ mỗi subword về chỉ số word cha
            for word_index, word in enumerate(segmented_text.words):

                # 1 word có thể tạo ra nhiều subword
                pieces = self.tokenizer.tokenize(word.value)

                if not pieces:
                    raise ValueError(f"Word {word_index} ko tạo ra subword")

                # thêm các subword
                subwords.extend(pieces)

                # Ghi lại word cha của từng subword.
                # Ví dụ:
                # word_index = 2
                # pieces = ["abc@@", "xyz"]
                # => thêm [2, 2].
                subword_word_ids.extend([word_index]*len(pieces))

            # Sau khi for xong, kiểm tra việc tách từng word có giống tokenize toàn bộ câu hay ko
            full_sentence_tokens = self.tokenizer.tokenize(segmented_text.segmented)
            if subwords != full_sentence_tokens:
                raise ValueError("Tokenization từng word khác tokenization toàn cầu")

            # B3. chuyển subword thành input ids (id trong vocabulary)
            subword_ids = self.tokenizer.convert_tokens_to_ids(subwords)

            # PhoBERT: <s> + subword ids + </s>
            input_ids = self.tokenizer.build_inputs_with_special_tokens(subword_ids)

            # B4. tạo word ids
            word_ids: list[int | None] = [None, *subword_word_ids, None]

            # kiểm tra ánh xạ có đủ vị trí chưa
            if len(input_ids) != len(word_ids):
                raise ValueError("số input_ids và word_ids ko khớp")
            # kiểm tra max length
            if len(input_ids) > self.max_length:
                raise ValueError(
                f"Độ dài {len(input_ids)} vượt "
                f"max_length={self.max_length}. "
                "Không tự động truncation để tránh mất entity."
            )

            # B5 tạo attention mask
            attention_mask = [1]*len(input_ids)

            tokens = self.tokenizer.convert_ids_to_tokens(input_ids)

            return TokenizedText(
                original=segmented_text.original,
                segmented=segmented_text.segmented,
                words=segmented_text.words,
                tokens=tokens,
                input_ids=input_ids,
                attention_mask=attention_mask,
                word_ids=word_ids
            )


# 4. Kiểm thử độc lập
if __name__ == "__main__":
    from src.preprocessing.word_segment_1 import WordSegmenter
    # Khởi tạo hai tokenizer/segmenter một lần.
    segmenter = WordSegmenter(model_dir="D:/vncorenlp")
    phobert = PhoBERTTokenizer()

    test_texts = [
        "Bật đèn phòng khách sau 10 phút",
        "Ông Tạ Minh Quân tới Hà Nội chơi",
        "Tắt quạt trong phòng ngủ lúc 22 giờ.",
    ]

    for text in test_texts:

        print("\n" + "=" * 75)

        # B1. Phân đoạn từ.
        segmented = segmenter.segment(text)

        # B2. PhoBERT tokenization.
        result = phobert.encode(segmented)

        # B3. Đối chiếu với encode toàn câu của Hugging Face.
        expected_ids = phobert.tokenizer.encode(
            segmented.segmented,
            add_special_tokens=True
        )

        assert result.input_ids == expected_ids, (
            "input_ids không khớp với tokenizer.encode()"
        )

        assert (
            len(result.tokens)
            == len(result.input_ids)
            == len(result.word_ids)
            == len(result.attention_mask)
        ), "Độ dài các mảng không khớp"

        # B4. In thông tin.
        print("Original :", result.original)
        print("Segmented:", result.segmented)

        print("\nInput IDs:", result.input_ids)
        print("Attention:", result.attention_mask)
        print("Word IDs :", result.word_ids)

        print("\n" + "-" * 75)
        print(
            f"{'TOKEN':<20} "
            f"{'WORD_ID':<10} "
            f"{'WORD_SPAN':<15} "
            f"{'ORIGINAL'}"
        )
        print("-" * 75)

        for token, word_id in zip(
            result.tokens,
            result.word_ids
        ):

            if word_id is None:
                span = "SPECIAL"
                original_word = "-"
            else:
                word = result.words[word_id]
                span = f"[{word.start}, {word.end})"

                original_word = result.original[
                    word.start:word.end
                ]

            print(
                f"{token:<20} "
                f"{str(word_id):<10} "
                f"{span:<15} "
                f"{original_word}"
            )

        print("-" * 75)
        print("Total tokens:", len(result.input_ids))
        print("PASS: Tokenization và word mapping hợp lệ")

    print("\n========== TOKENIZER TEST COMPLETED ==========")

