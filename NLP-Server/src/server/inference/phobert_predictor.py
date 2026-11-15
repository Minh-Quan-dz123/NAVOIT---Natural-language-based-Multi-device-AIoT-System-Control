from src.server.schemas import ParsedCommand


class PhoBERTPredictor:

    def __init__(self, checkpoint_path: str, vncorenlp_dir: str):
        self.checkpoint_path = checkpoint_path
        self.vncorenlp_dir = vncorenlp_dir

        self.model = None
        self.segmenter = None
        self.tokenizer = None
        self.label_maps = None

        # Load model một lần khi NLP Server khởi động.
        self.load_model()

    # 1. LOAD MODEL VÀ CÔNG CỤ TIỀN XỬ LÝ
    def load_model(self):

        # Các class đã có trong project:
        #
        # from src.nlp.model import SmartHomePhoBERT
        # from src.preprocessing.word_segment_1 import WordSegmenter
        # from src.preprocessing.phobert_tokenizer import PhoBERTTokenizer
        #
        # Sau khi có checkpoint:
        #
        # 1. Đọc dataset/config/label_maps.json
        # 2. Khởi tạo WordSegmenter
        # 3. Khởi tạo PhoBERTTokenizer
        # 4. Khởi tạo SmartHomePhoBERT
        # 5. Load trọng số đã fine-tune
        # 6. Chuyển model sang eval()
        #
        # Chưa thực hiện vì checkpoint chưa sẵn sàng.

        raise NotImplementedError(
            "PhoBERTPredictor chưa được tích hợp checkpoint. "
            "Hãy sử dụng MockPredictor để kiểm thử khung Server."
        )

    # 2. DỰ ĐOÁN CÂU LỆNH
    def predict(self, text: str) -> ParsedCommand:

        # Pipeline suy luận sẽ là:
        #
        # text
        #   ↓
        # WordSegmenter.segment(text)
        #   ↓
        # PhoBERTTokenizer.encode(...)
        #   ↓
        # SmartHomePhoBERT.forward(...)
        #   ↓
        # intent_logits, tag_logits, time_logits
        #   ↓
        # Chuyển logits thành nhãn
        #   ↓
        # BIO Decoder
        #   ↓
        # ParsedCommand

        raise NotImplementedError( "Chưa triển khai inference PhoBERT.")
