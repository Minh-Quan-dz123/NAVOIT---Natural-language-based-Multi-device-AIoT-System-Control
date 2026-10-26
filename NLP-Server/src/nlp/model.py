# ============================================================
# CLASS: SmartHomePhoBERT
# MÔ HÌNH NLP ĐA NHIỆM CHO HỆ THỐNG NHÀ THÔNG MINH
#
# 1. MỤC ĐÍCH
# Xây dựng mô hình NLP đa nhiệm dựa trên PhoBERT-base-v2
# để phân tích câu lệnh tiếng Việt điều khiển nhà thông minh.
#
# Mô hình thực hiện đồng thời 3 nhiệm vụ:
#   1. Intent Classification:
#      Phân loại ý định của câu (TURN_ON, TURN_OFF, QUERY,...).

#   2. Device Tagging:
#      Gán nhãn từng token để trích xuất thiết bị, vị trí, tầng,...
#
#   3. Schedule Tagging:
#      Gán nhãn từng token để nhận diện thông tin thời gian
#      như duration, delay, schedule_start_at,...
#
#
# 2. KIẾN TRÚC MÔ HÌNH
# ------------------------------------------------------------
# Input: input_ids + attention_mask
#                  |
#           PhoBERT Encoder
#                  |
#        Hidden States [B, L, H]
#                  |
#          +-------+-------+
#          |       |       |
#       Intent   Device  Schedule
#        Head     Head     Head
#          |       |       |
#        [B,I]   [B,L,T] [B,L,S]
#
# Trong đó:
#   B = Batch size (số câu trong batch).
#   L = Số token mỗi câu sau padding/truncation.
#   H = Hidden size (768 đối với PhoBERT-base-v2).
#   I = Số nhãn Intent.
#   T = Số nhãn Device Tag.
#   S = Số nhãn Schedule Tag.
#
# Ba Classification Head hoạt động độc lập và sử dụng chung
# các vector biểu diễn ngữ cảnh do PhoBERT Encoder tạo ra.
#
#
# 3. CLASS SmartHomePhoBERT(nn.Module)
# ------------------------------------------------------------
# Lớp kế thừa nn.Module của PyTorch, định nghĩa kiến trúc
# mô hình, các tầng neural và quá trình forward.
#
#
# 4. CÁC THUỘC TÍNH CỦA CLASS
# ------------------------------------------------------------
#
# self.encoder:
#   PhoBERT Encoder được tải từ mô hình pretrained.
#   Chuyển input_ids thành các vector biểu diễn ngữ cảnh.
#   Output chính: [B, L, H].
#
# self.dropout:
#   Tầng Dropout với xác suất p = 0.1.
#   Ngẫu nhiên loại bỏ một số phần tử kích hoạt khi training
#   nhằm giảm overfitting.
#
# self.intent_head:
#   Tầng Linear(H, I).
#   Nhận vector của token đầu tiên (<s>) để phân loại Intent.
#   Output: [B, I].
#
# self.tag_head:
#   Tầng Linear(H, T).
#   Phân loại Device Tag cho từng token.
#   Output: [B, L, T].
#
# self.time_head:
#   Tầng Linear(H, S).
#   Phân loại Schedule Tag cho từng token.
#   Output: [B, L, S].
#
# self.freeze_encoder:
#   Biến boolean xác định có đóng băng Encoder hay không.
#   True: Không cập nhật trọng số Encoder khi huấn luyện.
#   False: Cho phép cập nhật trọng số Encoder.
#
#
# 5. CÁC PHƯƠNG THỨC CỦA CLASS
# ------------------------------------------------------------
#
# 5.1. __init__(
#          num_intents,
#          num_tag_labels,
#          num_time_labels,
#          model_name="vinai/phobert-base-v2",
#          freeze_encoder=True
#      )
#
#   Chức năng:
#     - Khởi tạo PhoBERT Encoder từ pretrained model.
#     - Lấy hidden_size từ cấu hình Encoder.
#     - Khởi tạo Dropout và 3 Classification Head.
#     - Đóng băng Encoder nếu freeze_encoder=True.
#
#   Output:
#     Không trả về giá trị; khởi tạo các thuộc tính của model.
#
# 5.2. train(mode: bool = True)
#   Chức năng:
#     - Ghi đè phương thức train() kế thừa từ nn.Module.
#     - Chuyển mô hình sang training mode nếu mode=True.
#     - Chuyển mô hình sang evaluation mode nếu mode=False.
#     - Nếu Encoder bị đóng băng thì luôn giữ Encoder
#       ở evaluation mode để vô hiệu hóa Dropout bên trong.
#
#   Input:
#     mode: Boolean, mặc định True.
#
#   Output:
#     self (đối tượng mô hình hiện tại).
#
#
# 5.3. forward(input_ids, attention_mask)
#
#   Chức năng:
#     Định nghĩa quá trình lan truyền tiến của mô hình.
#
#   Input:
#     input_ids: Tensor [B, L] chứa ID của các token.
#     attention_mask: Tensor [B, L] đánh dấu token/padding.
#
#   Các bước xử lý:
#     B1. Đưa input qua PhoBERT Encoder.
#     B2. Lấy last_hidden_state có shape [B, L, H].
#     B3. Trích xuất vector token đầu tiên [B, H].
#     B4. Đưa vector này qua Dropout và Intent Head.
#     B5. Đưa toàn bộ hidden states qua Dropout và Tag Head.
#     B6. Đưa toàn bộ hidden states qua Dropout và Time Head.
#     B7. Trả về kết quả của cả 3 Head.
#
#   Output:
#     Dictionary gồm:
#       "intent_logits": Tensor [B, I].
#       "tag_logits":    Tensor [B, L, T].
#       "time_logits":   Tensor [B, L, S].
#
#
# ============================================================

# 1 IMPORT THƯ VIỆN

# torch.nn là module của PyTorch, cung cấp những thành phần dùng để xây dựng
# mạng neural ví dụ như: 

# Thành phần	            Chức năng
# nn.Module	            Lớp cơ sở để định nghĩa mô hình hoặc tầng neural
# nn.Linear	            Tầng biến đổi tuyến tính
# nn.Dropout	        Tắt ngẫu nhiên một phần tử kích hoạt khi training
# nn.CrossEntropyLoss	Hàm loss thường dùng cho phân loại
# nn.Embedding	        Ánh xạ ID thành vector embedding

# AutoModel thuộc thư viện Hugging Face Transformers
# nó cho phép tự động tải kiến trúc mô hình phù hợp với cấu hình pretrained

import torch.nn as nn
from transformers import AutoModel


# 2. KHAI BÁO LỚP SmartHomePhoBERT
class SmartHomePhoBERT(nn.Module):

    # Hàm khởi tạo
    def __init__(
        self,
        num_intents: int,
        num_tag_labels: int,
        num_time_labels: int,
        model_name: str = "vinai/phobert-base-v2",
        freeze_encoder: bool = True
    ):
        super().__init__()

        # 2.1. Tải PhoBERT Encoder v2 đã Pre-train
        self.encoder = AutoModel.from_pretrained(model_name, add_pooling_layer=False)
        # Nó tải cả kiến trúc và trọng số pretrained vào RAM
        # add_pooling_layer=False là gì?
            # Trong các mô hình kiểu BERT/RoBERTa, pooling layer tùy chọn có thể lấy 
            # vector của token đầu tiên rồi thực hiện thêm phép biến đổi, chẳng hạn Linear kết hợp Tanh.

        # 2.2. lấy Hidden_size
        # self.encoder.config chứa những thông số cấu hình của pretrained model.
        # .hidden_size có thể trả về hidden_size = 768
        hidden_size = self.encoder.config.hidden_size

        # 2.3. Tạo Dropout
        self.dropout = nn.Dropout(0.1)

        # 3. TẠO BA CLASSIFICATION HEAD
        # Intent Head, Tags Head và Schedule Head
        self.intent_head = nn.Linear(hidden_size, num_intents)
        self.tag_head =nn.Linear(hidden_size, num_tag_labels)
        self.time_head = nn.Linear(hidden_size, num_time_labels)

        # 7. Đóng băng Encoder nếu được yêu cầu.
        self.freeze_encoder = freeze_encoder

        if self.freeze_encoder:
            self.encoder.requires_grad_(False)
            # self.encoder: Mô hình PhoBERT Encoder đã pretrained.
            # requires_grad_(): Phương thức của PyTorch dùng để thay đổi 
            # thuộc tính requires_grad của các tham số trong module.
            # False: Không yêu cầu tính gradient cho các tham số đó.


    # 4. Custom phương thức train của lớp cha
    def train(self, mode: bool = True):
        super().train(mode) # Nếu mode=True, toàn bộ mô hình sẽ được chuyển sang training mode trước.

        # giữ Encoder ở eval mode khi bị đóng băng
        if self.freeze_encoder:
            self.encoder.eval()

        # Trong PyTorch, Evaluation Mode (eval) là chế độ đánh giá hoặc suy luận của mô hình, trong đó một số layer như Dropout và BatchNorm thay đổi cách hoạt động.

        # PyTorch có 2 chế độ hoạt động chính:
        # 1. Training Mode — chế độ huấn luyện.
        # 2. Evaluation Mode — chế độ đánh giá/suy luận.

        # Nếu Encoder bị đóng băng, chuyển riêng Encoder về evaluation mode, chủ yếu để vô hiệu hóa Dropout trong Encoder.
        # Việc này giúp các hidden states từ Encoder ổn định hơn giữa các lần forward trên cùng một input.
        return self

    
    # 5. HÀM FORWARD
    def forward(self, input_ids, attention_mask):
        # 5.1. cho input đi qua PhoBERT Encoder
        outputs = self.encoder(input_ids = input_ids, attention_mask = attention_mask)

        # [batch_size, seq_len, hidden_size]
        hidden_states = outputs.last_hidden_state

        # outputs là object chứa kết quả do Encoder trả về. 
        # last_hidden_state là tensor chứa các vector tại tầng Transformer cuối cùng.

        # NHÁNH 1. Biểu diễn token đầu cho Intent Head.
        cls_vector = hidden_states[:, 0, :] 
        # ":" đầu tiên	Lấy tất cả các câu trong batch
	    # Chỉ lấy token ở vị trí 0 của mỗi câu
        # ":" cuối cùng	Lấy toàn bộ 768 giá trị trong vector

        # cho đi qua Intent Head
        intent_logits = self.intent_head(self.dropout(cls_vector))

        # NHÁNH 2. Dự đoán Tags Theo từng token
        tag_logits = self.tag_head(self.dropout(hidden_states))

        # NHÁNH 3. Dự đoán Schedule theo từng token
        time_logits = self.time_head(self.dropout(hidden_states))

        # cuối cùng trả về output của cả 3 head
        return {
            "intent_logits": intent_logits,
            "tag_logits": tag_logits,
            "time_logits": time_logits
        }


