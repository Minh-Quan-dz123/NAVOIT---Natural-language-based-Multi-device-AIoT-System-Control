import torch
from torch.nn.utils.rnn import pad_sequence
from torch.utils.data import DataLoader

from src.data.dataset import SmartHomeDataset
from src.preprocessing.word_segment_1 import WordSegmenter
from src.preprocessing.phobert_tokenizer import PhoBERTTokenizer
from src.preprocessing.label_alignment import IGNORE_INDEX

# 1 gom các mẫu thành 1 batch và padding
def add_padding(samples: list[dict], pad_token_id: int) -> dict:

    # dùng hàm pad_sequence có sẵn trong thư viện để tự cân bằng padding 
    input_ids = pad_sequence([sample["input_ids"] for sample in samples],
                             batch_first=True,
                             padding_value=pad_token_id)

    # thêm attention_mask tương ứng vs padding
    attention_mask = pad_sequence([sample["attention_mask"] for sample in samples],
                                  batch_first=True,
                                  padding_value=0)
    # xử lý intent_label
    intent_label=torch.stack([sample["intent_label"] for sample in samples])

    # xử lý tag_labels và time_labels
    tag_labels = pad_sequence(
        [sample["tag_labels"] for sample in samples],
        batch_first=True,
        padding_value=IGNORE_INDEX
    )

    time_labels = pad_sequence(
        [sample["time_labels"] for sample in samples],
        batch_first=True,
        padding_value=IGNORE_INDEX
    )

    return {
        "input_ids": input_ids,
        "attention_mask": attention_mask,
        "intent_label": intent_label,
        "tag_labels": tag_labels,
        "time_labels": time_labels
    }


# 2 hàm tạo dataloader
def create_dataloader(dataset: SmartHomeDataset, batch_size: int = 8) -> DataLoader:
    # B1. các loại kiểm tra
    if not isinstance(batch_size, int) or batch_size <= 0:
        raise ValueError("batch_size phải là số nguyên dương")
    
    # B2. lấy tập train
    shuffle = dataset.split=="train"

    # B3. lấy pad_token_id từ PhoBERT Tokenizer
    pad_token_id = dataset.tokenizer.tokenizer.pad_token_id

    if pad_token_id is None:
                    raise ValueError("Tokenizer ko có pad_token_id")

    # B4. tạo dataloader
    return DataLoader(
        dataset=dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        num_workers=0,
        drop_last=False,
        collate_fn=lambda samples: add_padding(samples, pad_token_id),
    )

if __name__ == "__main__":
    # B1. Khởi tạo các đối tượng preprocessing
    segmenter = WordSegmenter(model_dir="D:/vncorenlp")
    tokenizer = PhoBERTTokenizer()

    # B2. tạo dataset train
    dataset = SmartHomeDataset(split="train", segmenter=segmenter, tokenizer=tokenizer)

    # B3. Tạo DataLoard train với batch_size = 8
    train_loader = create_dataloader(dataset, batch_size=8)

    print("số mẫu train", len(dataset))
    print("số batch train", len(train_loader))

    # B4. kiểm thử 2 mẫu
    test_ids = ("ex_0001", "ex_0025")
    test_samples = []

    for sample_id in test_ids:
        index = next(i for i, sample in enumerate(dataset.samples)
            if sample["id"] == sample_id)

        test_samples.append(dataset[index])


    # B5. tạo dataloader cho 2 mẫu đó
    pad_token_id = tokenizer.tokenizer.pad_token_id
    test_loader = DataLoader(
        dataset=test_samples,
        batch_size=2,
        shuffle=False,
        num_workers=0,
        collate_fn=lambda samples: add_padding(samples, pad_token_id)
    )

    # B6. Lấy batch đầu tiên.
    batch = next(iter(test_loader))

    # B7. In kích thước Tensor.
    print("\n========== BATCH SHAPES ==========")

    for key, value in batch.items():
        print(f"{key:<20}: {tuple(value.shape)}")

    # B8. In nội dung batch.
    print("\n========== BATCH CONTENT ==========")

    for key, value in batch.items():
        print(f"\n{key}:")
        print(value)

    # B9. Kiểm tra shape.
    assert batch["input_ids"].shape == (2, 9)
    assert batch["attention_mask"].shape == (2, 9)
    assert batch["intent_label"].shape == (2,)
    assert batch["tag_labels"].shape == (2, 9)
    assert batch["time_labels"].shape == (2, 9)

    # Kiểm tra padding.
    # Mẫu ex_0001 dài 6 token, cần thêm 3 pad tokens.
    assert torch.all(batch["attention_mask"][0, 6:] == 0)
    assert torch.all(batch["tag_labels"][0, 6:] == IGNORE_INDEX)
    assert torch.all(batch["time_labels"][0, 6:] == IGNORE_INDEX)

    print("\nPASS: DataLoader hoạt động đúng")
