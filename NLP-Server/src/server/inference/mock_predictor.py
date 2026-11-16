
import re
import unicodedata

from src.server.schemas import ParsedCommand, TimeEntity


def extract_tags(text: str) -> list[str]:
    # Tách Device Tag và Location Tag
    parts = re.split( r"\s+(?:ở|trong|tại)\s+|\s*,\s*", text)
    return [part.strip() for part in parts if part.strip()]

class MockPredictor:

    def predict(self, text: str) -> ParsedCommand:
        normalized = unicodedata.normalize(
            "NFC", " ".join(text.strip().casefold().split())
        )

        def unknown():
            return ParsedCommand(
                text=text,
                intent="UNKNOWN",
                deviceTags=[],
                timeEntities=[],
                predictor="mock"
            )

        # 1. HỦY SCHEDULE
        match = re.fullmatch(
            r"(?:hủy|huỷ)\s+lịch"
            r"(?:\s+điều\s+khiển)?"
            r"(?:\s+của)?\s+(.+)",
            normalized
        )

        if match:
            return ParsedCommand(
                text=text,
                intent="CANCEL_SCHEDULE",
                deviceTags=extract_tags(match.group(1)),
                timeEntities=[],
                predictor="mock"
            )

        # 2. NHẬN DIỆN ON/OFF
        match = re.fullmatch( r"(bật|mở|tắt|đóng)\s+(.+)", normalized)

        if not match:
            return unknown()

        action, target = match.groups()

        intent = (
            "TURN_ON" if action in ("bật", "mở")
            else "TURN_OFF"
        )

        times = []

        # 3. SAU X PHÚT [TRONG Y PHÚT]
        match = re.search(
            r"\s+sau\s+(\d+)\s+(giây|phút|giờ)"
            r"(?:\s+trong\s+(\d+)\s+(giây|phút|giờ))?$",
            target
        )

        if match:
            times.append(TimeEntity(
                type="SCHEDULED_DELAY",
                text=f"{match.group(1)} {match.group(2)}"
            ))

            if match.group(3):
                times.append(TimeEntity(
                    type="DURATION",
                    text=f"{match.group(3)} {match.group(4)}"
                ))

            target = target[:match.start()].strip()

        else:
            # 4. [HÔM NAY/NGÀY MAI] LÚC HH:MM
            # Có thể kèm "trong X phút"
            match = re.search(
                r"\s+(?:(hôm nay|ngày mai)\s+)?"
                r"lúc\s+(\d{1,2}):(\d{2})"
                r"(?:\s+trong\s+(\d+)\s+(giây|phút|giờ))?$",
                target
            )

            if match:
                prefix = (
                    f"{match.group(1)} "
                    if match.group(1) else ""
                )

                times.append(TimeEntity(
                    type="SCHEDULED_START_AT",
                    text=(
                        f"{prefix}lúc "
                        f"{match.group(2)}:{match.group(3)}"
                    )
                ))

                if match.group(4):
                    times.append(TimeEntity(
                        type="DURATION",
                        text=f"{match.group(4)} {match.group(5)}"
                    ))

                target = target[:match.start()].strip()

            else:
                # 5. TRONG X PHÚT (bắt đầu ngay)
                match = re.search( r"\s+trong\s+(\d+)\s+(giây|phút|giờ)$",target)

                if match:
                    times.append(TimeEntity(
                        type="DURATION",
                        text=f"{match.group(1)} {match.group(2)}"
                    ))

                    target = target[:match.start()].strip()

        # 6. Không biến câu có thời gian chưa hiểu
        # thành lệnh ON/OFF tức thời.
        if re.search(
            r"\b(?:sau|lúc|hẹn|giây|phút|giờ|"
            r"ngày mai|hôm nay|đến)\b"
            r"|\btrong\s+\d+\b",
            target
        ):
            return unknown()

        tags = extract_tags(target)

        if not tags:
            return unknown()

        return ParsedCommand(
            text=text,
            intent=intent,
            deviceTags=tags,
            timeEntities=times,
            predictor="mock"
        )
