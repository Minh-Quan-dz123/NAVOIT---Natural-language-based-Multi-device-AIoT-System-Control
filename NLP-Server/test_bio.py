from transformers import AutoTokenizer

tokenizer = AutoTokenizer.from_pretrained(
    "vinai/phobert-base",
    use_fast=False,
)

text = "Bật đèn phòng_khách sau 10 phút"

inputs = tokenizer(
    text,
    return_tensors="pt",
    return_token_type_ids=False,
)

tokens = tokenizer.convert_ids_to_tokens(
    inputs["input_ids"][0].tolist()
)

# Nhãn ví dụ, gán thủ công
tag_labels = [
    -100,  # <s>
    0,     # Bật -> O
    1,     # đèn -> B-DEVICE_TYPE
    3,     # phòng_@@ -> B-LOCATION
    -100,  # khách -> bỏ qua subword tiếp theo
    0,     # sau -> O
    0,     # 10 -> O
    0,     # phút -> O
    -100,  # </s>
]

id2tag = {
    0: "O",
    1: "B-DEVICE_TYPE",
    2: "I-DEVICE_TYPE",
    3: "B-LOCATION",
    4: "I-LOCATION",
    5: "B-FLOOR",
    6: "I-FLOOR",
}

assert len(tokens) == len(tag_labels)

for token, label_id in zip(tokens, tag_labels):
    label = (
        "IGNORE"
        if label_id == -100
        else id2tag[label_id]
    )

    print(f"{token:<15} -> {label}")