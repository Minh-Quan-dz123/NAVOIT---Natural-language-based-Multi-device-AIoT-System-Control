import json
from pathlib import Path
import torch
from torch.utils.data import Dataset
from src.preprocessing.word_segment_1 import WordSegmenter
from src.preprocessing.phobert_tokenizer import PhoBERTTokenizer
from src.preprocessing.label_alignment import (align_labels, load_label_maps,)

# dataset.py nằm tại src/data/dataset.py
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# thư mục chứa train, validation và test
SPLITS_DIR = PROJECT_ROOT/"dataset"/"data"/"splits"


# 1 CLASS DATASET
class SmartHomeDataset(Dataset):
    # 1 contructor
    def __init__(self, split: str, segmenter: WordSegmenter, tokenizer: PhoBERTTokenizer):
        # kiểm tra tập dữ liệu được chọn
        if split not in ("train", "validation", "test"):
            raise ValueError("split phải là train, validation hoặc tets")
        self.split = split

        # dùng lại đối tượng đã khởi tạo bên ngoài
        # ko load vncorenlp/phobert mỗi lần lấy mẫu
        self.segmenter = segmenter
        self.tokenizer = tokenizer
        self.label_maps = load_label_maps()
        self.file_path = SPLITS_DIR/f"{split}.jsonl"

        self.samples: list[dict] = []

        with self.file_path.open("r", encoding = "utf-8") as f:
            for line_number, line in enumerate(f, start = 1):
                if not line.strip():
                    continue # bỏ qua dòng trống

                try:
                    sample = json.loads(line)
                except json.JSONDecodeError as error:
                    raise ValueError(f"JSON không hợp lệ tại {self.file_path}, "
                        f"dòng {line_number}") from error

                if not isinstance(sample, dict):
                    raise ValueError( f"Dòng {line_number} phải là JSON object")
                
                self.samples.append(sample)

    # 2 hàm helper trả về số lượng mẫu
    def __len__(self)-> int:
        return len(self.samples)

    # 3. lấy 1 mẫu dữ liệu
    def __getitem__(self, index: int) -> dict[str, torch.Tensor]:
        sample = self.samples[index]

        # B1 chuyển intent thành ID
        intent = sample["intent"]
        intent2id = self.label_maps["intent2id"]

        if intent not in intent2id:
            raise ValueError(
                f"Mẫu {sample.get('id', index)} "
                f"có intent không hợp lệ: {intent}"
            )
        intent_id = intent2id[intent]

        # B2 word segmentation + phober tokenization + label aligment
        segmented = self.segmenter.segment(sample["text"])
        tokenized = self.tokenizer.encode(segmented)
        aligned = align_labels(sample, tokenized, self.label_maps)

        length = len(tokenized.input_ids)
        if not(
            len(tokenized.attention_mask) == length
            and len(aligned["tag_labels"]) == length
            and len(aligned["time_labels"]) == length
        ):
            raise ValueError(
                f"Mẫu {sample.get('id', index)} "
                "có độ dài token và nhãn không khớp"
            )

        # return về tensor
        return {
            "input_ids": torch.tensor(tokenized.input_ids, dtype=torch.long),
            "attention_mask": torch.tensor(tokenized.attention_mask, dtype=torch.long),
            "intent_label": torch.tensor(intent_id, dtype=torch.long),
            "tag_labels": torch.tensor(aligned["tag_labels"], dtype=torch.long),
            "time_labels": torch.tensor(aligned["time_labels"], dtype=torch.long)
        }

# test thử độc lập
if __name__ == "__main__":
    # B1. Khởi tạo WordSegmenter và PhoBERTTokenizer.
    segmenter = WordSegmenter(model_dir="D:/vncorenlp")
    tokenizer = PhoBERTTokenizer()

    # B2. Khởi tạo Dataset cho tập train.
    dataset = SmartHomeDataset(
        split="train",
        segmenter=segmenter,
        tokenizer=tokenizer
    )

    print("Số mẫu train:", len(dataset))

    # B3. Chỉ kiểm thử hai mẫu đã chạy Label Alignment.
    for sample_id in ("ex_0001", "ex_0025"):

        # Tìm vị trí của mẫu cần kiểm thử.
        index = next(
            i for i, sample in enumerate(dataset.samples)
            if sample["id"] == sample_id
        )

        # __getitem__ sẽ thực hiện toàn bộ preprocessing.
        item = dataset[index]

        print(
            f"\n{sample_id}: "
            f"{dataset.samples[index]['text']}"
        )

        print("input_ids      :", item["input_ids"].tolist())
        print("attention_mask :", item["attention_mask"].tolist())
        print("intent_label   :", item["intent_label"].item())
        print("tag_labels     :", item["tag_labels"].tolist())
        print("time_labels    :", item["time_labels"].tolist())

        print("PASS: Dataset sample hợp lệ")





