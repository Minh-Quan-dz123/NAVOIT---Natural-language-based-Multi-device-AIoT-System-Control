import json
from pathlib import Path
from src.preprocessing.phobert_tokenizer import TokenizedText

# cấu hình
IGNORE_INDEX = -100 # giá trị đc Pytorch CrossEntropyLoss bỏ qua

# Thư mục gốc NLP-Server
# File hiện tại: src/preprocessing/label_alignment.py
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# đường dẫn file ánh xạ nhãn
LABEL_MAPS_PATH = (PROJECT_ROOT/"dataset"/"config"/"label_maps.json")

# 1 hàm load label map
def load_label_maps(path: Path=LABEL_MAPS_PATH) -> dict:
    # Đọc các ánh xạ nhãn từ label_maps.json.
    # Ví dụ:
    #     tag2id = {
    #         "O": 0,
    #         "B-TAG": 1,
    #         "I-TAG": 2
    #     }
    with path.open("r", encoding="utf-8") as f:
        maps = json.load(f)

    # Kiểm tra hai bộ nhãn cần cho Label Alignment.
    for key in ("tag2id", "time2id"):
        if key not in maps or "O" not in maps[key]:
            raise ValueError(f"label_maps.json thiếu {key} hoặc nhãn O")
    return maps

# 2. kiểm tra entity offset
def validate_entity_offsets(sample: dict, tokenized: TokenizedText) -> None:
    # Kiểm tra:
    # 1. sample["text"] có khớp original sau VnCoreNLP?
    # 2. start/end có nằm trong phạm vi text?
    # 3. text[start:end] có bằng entity["text"]?

    sample_id = sample.get("id", "unknown")
    text = sample["text"]

    # kiểm tra chuỗi dataset và original
    if text != tokenized.original:
        raise ValueError(
            f"[{sample_id}] Dataset text khác original sau VnCoreNLP!\n"
            f"Dataset : {text!r}\n"
            f"Original: {tokenized.original!r}\n"
            "Cần kiểm tra bước chuẩn hóa dữ liệu; "
            "không tự sửa offset."
        )
    # duyệt 2 danh sách entity
    for field in ("device_entities", "schedule_entities"):
        entities = sample[field]
        if not isinstance(entities, list):
            raise TypeError(f"[{sample_id}] {field} phải là list")

        for entity in entities:
            start = entity["start"]
            end = entity["end"]
            if ((type(start) is not int) or (type(end) is not int) or not (0 <= start < end <= len(text))):
                raise ValueError(f"[{sample_id}] Offset ngoài phạm vi: {entity}")

            # lấy nội dung thực tế từ original và so sánh với nội dung entity trong dataset
            actual = tokenized.original[start:end]
            if(actual != entity["text"]):
                raise ValueError(
                    f"[{sample_id}] Offset entity không khớp: "
                    f"{entity}\n"
                    f"original[{start}:{end}] = {actual!r}"
                )

# 3 Align entity -> word
# chuyển entity thành nhãn BIO cho từng word
# Ví dụ:
#         Words:  ["Bật", "đèn", "phòng", "khách"]
#         Entity: {"type": "TAG", "start": 8, "end": 19}
#         Output: ["O", "O", "B-TAG", "I-TAG"]
def align_bio_for_word(tokenized: TokenizedText, entities: list[dict], label2id: dict[str, int])->list[str]:
    labels = ["O"]*len(tokenized.words)

    for entity in entities:
        start = entity["start"]
        end = entity["end"]
        entity_type = entity["type"]

        # Kiểm tra loại nhãn có tồn tại trong label_maps không.
        if (
            f"B-{entity_type}" not in label2id
            or f"I-{entity_type}" not in label2id
        ):
            raise ValueError(f"Entity type không hợp lệ: {entity_type}")

        # tìm các word nằm hoàn toàn trong entity
        word_indices = [
            i for i, word in enumerate(tokenized.words)
            if word.start >= start and word.end <= end
        ]

        # Kiểm tra có word nào giao với entity nhưng
        # không nằm hoàn toàn trong entity không.
        for word in tokenized.words:
            intersects = word.start < end and start < word.end
            contained = word.start >= start and word.end <= end

            if intersects and not contained:
                raise ValueError(
                    f"Entity {entity['text']!r} cắt ngang "
                    f"word {word.value!r}"
                )

        if not word_indices:
            raise ValueError(f"Không tìm thấy word cho entity {entity['text']!r}")

        # Kiểm tra entity được bao phủ từ đầu tới cuối.
        if (
            tokenized.words[word_indices[0]].start != start
            or tokenized.words[word_indices[-1]].end != end
        ):
            raise ValueError(
                f"Ranh giới word không khớp entity: {entity}"
            )

        # gán nhãn BIO
        for j, i in enumerate(word_indices):

            # Không cho phép ghi đè nhãn của entity khác.
            if labels[i] != "O":
                raise ValueError(f"Hai entity chồng lấn tại word {i}")
                    
            if j == 0:
                labels[i] = f"B-{entity_type}"
            else:
                labels[i] = f"I-{entity_type}"
    return labels



def align_idBio_for_Subword(tokenized: TokenizedText, word_labels: list[str], label2id: dict[str, int])->list[int]:

    result = []

    # ghi nhớ word đã gặp
    saw = set()

    for word_id in tokenized.word_ids:
        # Special token hoặc subword phụ.
        if (word_id is None) or (word_id in saw):
            result.append(IGNORE_INDEX)
            continue
        # Kiểm tra word_id có nằm trong danh sách word không.
        if not 0 <= word_id < len(word_labels):
            raise ValueError(f"word_id không hợp lệ: {word_id}")

        # Subword đầu tiên của word
        label = word_labels[word_id]
        result.append(label2id[label])

        # đấu dấu word đã xử lý
        saw.add(word_id)
    return result


# 5 hàm align_labels(), trả về
# {
#     "tag_labels": [-100, 0, 1, 1, 2, 0, 0, 0, -100],
#     "time_labels": [-100, 0, 0, 0, 0, 0, 1, 2, -100]
# }
def align_labels(sample: dict, tokenized: TokenizedText, label_maps: dict)->dict[str, list[int]]:

    # B1. kiểm tra offset trước
    validate_entity_offsets(sample, tokenized)

    # B2. lấy bảng ánh xạ nhãn
    tag2id = label_maps["tag2id"]
    time2id = label_maps["time2id"]

    # B3. Entity => gắn BIO cho Word 
    tag_word_labels = align_bio_for_word(tokenized, sample["device_entities"], tag2id)
    time_word_labels = align_bio_for_word(tokenized, sample["schedule_entities"], time2id)

    # B4. từ Word được gán BIO -> gán id của BIO cho subword của word
    tag_labels = align_idBio_for_Subword(tokenized, tag_word_labels, tag2id)
    time_labels = align_idBio_for_Subword(tokenized, time_word_labels, time2id)

    return { "tag_labels": tag_labels, "time_labels": time_labels}


# 6. kiểm thử 
if __name__ == "__main__":
    from src.preprocessing.word_segment_1 import WordSegmenter
    from src.preprocessing.phobert_tokenizer import PhoBERTTokenizer

    # B1. load label maps.
    label_maps = load_label_maps()

    # B2. load tập train thực tế
    path = PROJECT_ROOT/"dataset"/"data"/"splits"/"train.jsonl"

    # đọc toàn bộ nội dung file và chia thành từng dòn
    lines = path.read_text(encoding="utf-8").splitlines()
    samples = []
    for line in lines:
        # Bỏ qua dòng rỗng hoặc chỉ chứa khoảng trắng
        if line.strip():
            sample = json.loads(line) # chuyển thành json
            samples.append(sample)

    # B3. khởi tạo 2 bộ tiền xử lý
    segmenter = WordSegmenter(model_dir="D:/vncorenlp")
    tokenizer = PhoBERTTokenizer()

    # Hai mẫu có thật trong train.jsonl.
    # ex_0001: Không có Schedule.
    # ex_0025: Có DURATION.
    for sample_id in ("ex_0001", "ex_0025"):
        sample = next(s for s in samples if s["id"] == sample_id)

        # B4 word segmentation
        segmented = segmenter.segment(sample["text"])

        # B5 PhoBERT Tokenization
        tokenized = tokenizer.encode(segmented)

        # B6. gán Label
        aligned = align_labels(sample, tokenized, label_maps)

        # B7. kiểm tra độ dài
        assert len(aligned["tag_labels"]) == len(tokenized.input_ids)
        assert len(aligned["time_labels"]) == len(tokenized.input_ids)

         # B8. In kết quả.
        print(f"\nSample: {sample_id} | {sample['text']}")

        print(
            f"{'TOKEN':<20} "
            f"{'WORD_ID':<10} "
            f"{'DEVICE':<18} "
            f"SCHEDULE"
        )

        for token, word_id, tag_id, time_id in zip(
            tokenized.tokens,
            tokenized.word_ids,
            aligned["tag_labels"],
            aligned["time_labels"]
        ):

            # Chuyển ID thành tên nhãn để dễ kiểm tra.
            tag = (
                "-100" if tag_id == IGNORE_INDEX
                else label_maps["id2tag"][str(tag_id)]
            )

            time = (
                "-100" if time_id == IGNORE_INDEX
                else label_maps["id2time"][str(time_id)]
            )

            print(
                f"{token:<20} "
                f"{str(word_id):<10} "
                f"{tag:<18} "
                f"{time}"
            )

        print("PASS: Label Alignment")


