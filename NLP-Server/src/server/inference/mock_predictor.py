from src.server.schemas import ParsedCommand, TimeEntity


class MockPredictor:

    def predict(self, text: str) -> ParsedCommand:

        # Chuẩn hóa đơn giản để so khớp câu mẫu.
        normalized = " ".join(text.strip().lower().split() )
            
       
        # VÍ DỤ 1: BẬT ĐÈN SAU 10 PHÚT
        if normalized == "bật đèn học sau 10 phút":
            return ParsedCommand(
                text=text,
                intent="TURN_ON",
                deviceTags=["đèn học"],
                timeEntities=[
                    TimeEntity(
                        type="SCHEDULED_DELAY",
                        text="10 phút"
                    )
                ],
                predictor="mock"
            )

        # VÍ DỤ 2: TẮT QUẠT
        if normalized == "tắt quạt":
            return ParsedCommand(
                text=text,
                intent="TURN_OFF",
                deviceTags=["quạt"],
                timeEntities=[],
                predictor="mock"
            )

        # CÂU KHÔNG CÓ TRONG DỮ LIỆU MOCK
        return ParsedCommand(
            text=text,
            intent="UNKNOWN",
            deviceTags=[],
            timeEntities=[],
            predictor="mock"
        )
