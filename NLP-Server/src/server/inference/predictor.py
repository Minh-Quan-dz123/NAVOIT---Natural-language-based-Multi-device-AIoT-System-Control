from typing import Protocol
from src.server.schemas import ParsedCommand


class Predictor(Protocol):

    def predict(self, text: str) -> ParsedCommand:
        """
        Nhận câu lệnh tiếng Việt.

        Trả về ParsedCommand gồm:
        - Intent
        - Device Tags
        - Time Entities

        Mọi bộ dự đoán phải trả cùng cấu trúc.
        """
        ...
