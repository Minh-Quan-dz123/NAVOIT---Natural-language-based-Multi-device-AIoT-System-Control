
from typing import Literal

from pydantic import BaseModel, Field


# 1. CÁC LOẠI INTENT
IntentType = Literal[
    "TURN_ON",
    "TURN_OFF",
    "CANCEL_SCHEDULE",
    "QUERY_STATUS",
    "NO_ACTION",
    "UNKNOWN",
]


# 2. CÁC LOẠI THÔNG TIN THỜI GIAN
TimeType = Literal[
    "DURATION",
    "SCHEDULED_DELAY",
    "SCHEDULED_START_AT",
    "SCHEDULED_END_AT",
]


# 3. REQUEST TỪ FRONTEND
class NaturalCommandRequest(BaseModel):
    text: str = Field(
        min_length=1,
        max_length=500
    )


# 4. ENTITY THỜI GIAN
class TimeEntity(BaseModel):
    type: TimeType
    text: str


# 5. KẾT QUẢ PHÂN TÍCH CÂU LỆNH
class ParsedCommand(BaseModel):
    # Câu lệnh đầu vào
    text: str

    # Intent được dự đoán
    intent: IntentType

    # Những Tag trích xuất từ câu lệnh
    deviceTags: list[str] = Field(default_factory=list)

    # Thông tin thời gian nếu có
    timeEntities: list[TimeEntity] = Field(default_factory=list)

    # Nguồn dự đoán: mock hay model thật
    predictor: Literal["mock", "phobert"]
