# File này thực hiện:
#   1. Tải PhoBERT Tokenizer đã pretrained.
#   2. Khởi tạo mô hình SmartHomePhoBERT với số nhãn giả định.
#   3. Chuẩn hóa Unicode NFC cho câu đầu vào.
#   4. Tokenization để chuyển văn bản thành Tensor.
#   5. Đưa dữ liệu qua mô hình để thực hiện inference.
#   6. Kiểm tra kích thước output của 3 Classification Head.
#   7. Kiểm tra Encoder đã được đóng băng hay chưa.

import time
import torch
import unicodedata
from transformers import AutoTokenizer
# AutoTokenizer là một class có nhiệm vụ tự động lựa chọn và khởi 
# tạo tokenizer phù hợp với mô hình pretrained.

from src.nlp.model import SmartHomePhoBERT

MODEL_NAME = "vinai/phobert-base-v2"

# 1. TẢI tokenizer
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, use_fast=False)

# 2. TẠO MÔ HÌNH VỚI NHÃN TẠM THỜI ĐỂ TEST
model = SmartHomePhoBERT(
    num_intents=4,
    num_tag_labels=3,
    num_time_labels=5,
    model_name=MODEL_NAME,
    freeze_encoder=True
)

# 3. CHUYỂN MODEL SANG CHẾ ĐỘ INFERENCE
model.eval()

# 4. Văn bản đã được word segmentation thủ cộng.
test_text = "Bật đèn phòng_khách sau 10 phút"
print(" (1) Is NFC:", unicodedata.is_normalized("NFC", test_text)) # Kiểm tra Unicode lần 1

test_text = unicodedata.normalize("NFC", test_text) # Chuẩn hóa Unicode sang NFC

print(" (2) Is NFC:", unicodedata.is_normalized("NFC", test_text)) # Kiểm tra Unicode lần 1


# 5. Tokenization
inputs = tokenizer(test_text, return_tensors="pt", truncation=True, max_length = 64)

# inputs có dạng
# {
#     "input_ids": tensor([[0, 123, 456, 789, 2]]),
#     "attention_mask": tensor([[1, 1, 1, 1, 1]])
#      ...
# }

# return_tensors="pt", pt là viết tắt của PyTorch. Nó yêu cầu tokenizer trả về các torch.Tensor.
# Nếu không có tham số này, kết quả thường là các list Python thay vì Tensor.

# truncation=True
# Cho phép cắt bớt token nếu chuỗi vượt quá số lượng cho phép.

# 6. FORWARD VÀ ĐO THỜI GIAN INFERENCE

# Ghi lại thời điểm bắt đầu
start_time = time.perf_counter()

# Thực hiện inference
with torch.inference_mode():
    outputs = model(input_ids=inputs["input_ids"], attention_mask=inputs["attention_mask"])

# cú pháp with something(): cho phép tạm thời thiết lập một môi 
# trường thực thi cho các dòng nằm bên trong khối with.


# Ghi lại thời điểm kết thúc
end_time = time.perf_counter()

# Tính thời gian inference
inference_time = end_time - start_time


# 7. IN KẾT QUẢ
print("\n========== MODEL TEST ==========")

# 7.1. Văn bản đầu vào
original_text = "Bật đèn phòng_khách sau 10 phút"
print("\n[1] INPUT TEXT")
print("Original text :", original_text)
print("Normalized    :", test_text)
print("NFC before    :", unicodedata.is_normalized("NFC", original_text))
print("NFC after     :", unicodedata.is_normalized("NFC", test_text))

# 7.2. Tokenizer
print("\n[2] TOKENIZATION")
print("Input IDs     :", inputs["input_ids"])
print("Attention Mask:", inputs["attention_mask"])
print("Tokens        :", tokenizer.convert_ids_to_tokens(
    inputs["input_ids"][0].tolist()
))
print("Input Shape   :", inputs["input_ids"].shape)

# 7.3. Model outputs
print("\n[3] MODEL OUTPUTS")

print("Intent Logits Shape   :", outputs["intent_logits"].shape)
print("Tag Logits Shape      :", outputs["tag_logits"].shape)
print("Schedule Logits Shape :", outputs["time_logits"].shape)

# 7.4. Kiểm tra đóng băng Encoder
encoder_trainable = sum(
    p.numel()
    for p in model.encoder.parameters()
    if p.requires_grad
)

print("\n[4] ENCODER STATUS")
print("Encoder Frozen      :", encoder_trainable == 0)
print("Trainable Parameters:", encoder_trainable)

print("\n[5] INFERENCE TIME")
print(f"Inference Time: {inference_time:.6f} seconds")
print(f"Inference Time: {inference_time * 1000:.3f} ms")


print("\n========== TEST COMPLETED ==========")
