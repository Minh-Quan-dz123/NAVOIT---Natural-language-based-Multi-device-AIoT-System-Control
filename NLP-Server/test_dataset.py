import torch
from transformers import AutoTokenizer

tokenizer = AutoTokenizer.from_pretrained(
    "vinai/phobert-base",
    use_fast=False
)

# 1. Định nghĩa nhãn
INTENTS = [
    "TURN_ON", "TURN_OFF", "CREATE_DEVICE",
    "DELETE_DEVICE", "CANCEL_SCHEDULE", "UNKNOWN"
]

TAGS = [
    "O",
    "B-DEVICE_TYPE", "I-DEVICE_TYPE",
    "B-LOCATION", "I-LOCATION",
    "B-FLOOR", "I-FLOOR"
]

TIMES = [
    "O",
    "B-DURATION", "I-DURATION",
    "B-DELAY", "I-DELAY",
    "B-START_AT", "I-START_AT",
    "B-END_AT", "I-END_AT"
]

intent2id = {v: i for i, v in enumerate(INTENTS)}
tag2id = {v: i for i, v in enumerate(TAGS)}
time2id = {v: i for i, v in enumerate(TIMES)}

# 2. Dữ liệu mẫu đã word segmentation
words = [
    "Bật", "đèn", "phòng_khách",
    "sau", "10", "phút"
]

intent = "TURN_ON"

word_tags = [
    "O", "B-DEVICE_TYPE", "B-LOCATION",
    "O", "O", "O"
]

word_times = [
    "O", "O", "O",
    "O", "B-DELAY", "I-DELAY"
]

# 3. Chuyển từ sang subword
tokens = ["<s>"]
tag_ids = [-100]
time_ids = [-100]

for word, tag, time in zip(words, word_tags, word_times):

    subwords = tokenizer.tokenize(word)

    tokens.extend(subwords)

    # Chỉ gán nhãn subword đầu tiên
    for index, subword in enumerate(subwords):

        if index == 0:
            tag_ids.append(tag2id[tag])
            time_ids.append(time2id[time])
        else:
            tag_ids.append(-100)
            time_ids.append(-100)

tokens.append("</s>")
tag_ids.append(-100)
time_ids.append(-100)

# 4. Chuyển thành tensor
input_ids = torch.tensor([
    tokenizer.convert_tokens_to_ids(tokens)
])

attention_mask = torch.ones_like(input_ids)

intent_label = torch.tensor([
    intent2id[intent]
])

tag_labels = torch.tensor([tag_ids])
time_labels = torch.tensor([time_ids])

# 5. In kết quả
print("Tokens:", tokens)

print("\n===== TENSOR SHAPES =====")
print("input_ids:", input_ids.shape)
print("attention_mask:", attention_mask.shape)
print("intent_label:", intent_label.shape)
print("tag_labels:", tag_labels.shape)
print("time_labels:", time_labels.shape)

print("\n===== LABEL ALIGNMENT =====")

for token, tag, time in zip(tokens, tag_ids, time_ids):
    tag_name = "IGNORE" if tag == -100 else TAGS[tag]
    time_name = "IGNORE" if time == -100 else TIMES[time]

    print(f"{token:<15} {tag_name:<20} {time_name}")