"""Nguồn dữ liệu và mẫu câu phục vụ sinh dataset PhoBERT.
Có thể bổ sung DEVICES, LOCATIONS, ACTIONS và các lệnh add() tại đây.
Không cần sửa build_seed_dataset.py khi thêm template mới.

Quy ước placeholder:
    {device}  : một tên thiết bị; được bọc thành [[D:...]]
    {action}  : một động từ phù hợp intent; KHÔNG gán nhãn entity
    {l1}...{lN}: các Location khác nhau, số lượng theo template (không hardcode N)
    [[S:TYPE:giá trị]]: Schedule marker như mã nguồn ban đầu

Chú ý: Danh sách Location là phẳng theo thiết kế hiện tại. Các tổ hợp chọn ngẫu nhiên
có thể không tự nhiên hoặc mâu thuẫn vị trí; nên duyệt lại dữ liệu trước training.
"""

import re
import unicodedata

# Danh sách riêng của các thiết bị; KHÔNG ghép cặp cố định với Location.
DEVICES: list[str] = [
    # Đèn
    "đèn",
    "bóng đèn",
    "đèn ngủ",
    "đèn học",
    "đèn cầu thang",
    "đèn trần",

    # Quạt
    "quạt",
    "quạt trần",
    "quạt thông gió",
    "quạt đứng",
    "quạt hơi nước",

    # Điều hòa
    "điều hòa",
    "máy lạnh",

    # Máy bơm
    "máy bơm",
    "máy bơm nước",

    # Thiết bị khác
    "máy lọc không khí",
    "máy lọc nước",
    "bình nóng lạnh",
    "bình nước nóng",

]

# Danh sách Location độc lập. Có thể thêm tùy ý, không phải luôn chứa 5 phần tử.
LOCATIONS: list[str] = [
    # Phòng
    "phòng khách",
    "phòng ngủ",
    "phòng ngủ chính",
    "phòng con gái",
    "phòng con trai",
    "phòng tắm",
    "phòng vệ sinh",
    "phòng học",
    "phòng làm việc",
    "phòng ăn",
    "nhà bếp",
    "phòng bếp",
    "bếp",

    # Tầng
    "tầng 1",
    "tầng 2",
    "tầng 3",
    "tầng 4",
    "tầng 6",
    "tầng trệt",
    "tầng trên",
    "tầng dưới",
    "tầng hầm",

    # Khu vực tinh linh trong nhà
    "hành lang",
    "cầu thang",
    "ban công",
    "bàn làm việc",
    "cửa sổ",
    "góc phòng",
    "trước cửa",
    "trần nhà",

    # Khu vực ngoài nhà
    "sân",
    "sân trước",
    "sân sau",
    "sân vườn",
    "vườn",
    "sân thượng",
    "gara",
    "nhà xe",
    "phía sau nhà",
    "hiên nhà",
    "cổng",
    "cổng chính",
    "cửa trước",
    "cửa sau",

    "khu sinh hoạt",
    "khu giặt phơi",
]

# Các động từ thay thế theo đúng intent
ACTIONS: dict[str, list[str]] = {
    "TURN_ON": ["bật", "mở", "kích hoạt", "khởi động"],
    "TURN_OFF": ["tắt", "ngắt", "đóng", "dừng"],
}

# Số biến thể; 2 câu khi có device, 1 khi không có.
DEVICE_VARIANTS_PER_TEMPLATE = 2
NO_DEVICE_VARIANTS_PER_TEMPLATE = 1
RANDOM_SEED = 20261030  # Để tái tạo kết quả ở các lần chạy.

TEMPLATES: list[tuple[str, str, str]] = [] 


def add(intent: str, family: str, *templates: str) -> None:
    """Lưu các mẫu câu cùng intent, đánh số nhóm như phiên bản ban đầu."""
    for idx, template in enumerate(templates, 1):

        # Chuẩn hóa Unicode NFC
        template = unicodedata.normalize("NFC", template)
        template = re.sub(r"\s*([,.?!])\s*", r" \1 ", template)
        template = " ".join(template.split())
        TEMPLATES.append((intent, f"{family}_{idx:02d}", template))


# ======= 13 NHÓM TEMPLATE GỐC: =======

# 1. ĐIỀU KHIỂN NGAY
add("TURN_ON", "on_now",
    "Bật {device} {l1} .",
    "Mở {device} ở {l1} giúp tôi .",
    "Cho {device} tại {l1} chạy đi .",
    "Bật giúp mình {device} bên {l1} nhé .",
    "Làm ơn mở {device} ở {l1} .",
    "Kích hoạt {device} khu vực {l1} .",
)
add("TURN_OFF", "off_now",
    "Tắt {device} {l1} .",
    "Tắt hộ mình {device} ở {l1} .",
    "Cho {device} tại {l1} ngừng hoạt động .",
    "Làm ơn tắt {device} bên {l1} .",
    "Ngắt {device} ở {l1} đi .",
    "Dừng hoạt động của {device} khu vực {l1} .",
)

# 2. DURATION
add("TURN_ON", "on_duration",
    "Bật {device} {l1} trong [[S:DURATION:30 phút]] .",
    "Mở {device} ở {l1} khoảng [[S:DURATION:2 giờ]]",
    "Cho {device} ở {l1} hoạt động [[S:DURATION:15 phút]] rồi tự tắt .",
    "Bật {device} khu vực {l1} và giữ trong [[S:DURATION:10 giây]] .",
    "Cho {device} bên {l1} chạy [[S:DURATION:1 tiếng]] thôi .",
)
add("TURN_OFF", "off_duration",
    "Tắt {device} {l1} trong [[S:DURATION:20 phút]] rồi bật lại .",
    "Ngừng {device} ở {l1} khoảng [[S:DURATION:1 giờ]] .",
    "Cho {device} khu vực {l1} nghỉ [[S:DURATION:5 phút]] .",
    "Tắt {device} tại {l1} [[S:DURATION:30 giây]] rồi mở lại .",
    "Để {device} ở {l1} tạm ngừng hoạt động trong [[S:DURATION:45 phút]] rồi bật lại .",
)

# 3. SCHEDULED_DELAY
add("TURN_ON", "on_delay",
    "Sau [[S:SCHEDULED_DELAY:10 phút]] hãy bật {device} {l1} .",
    "[[S:SCHEDULED_DELAY:5 phút]] nữa bật {device} ở {l1} .",
    "Bật {device} bên {l1} sau [[S:SCHEDULED_DELAY:2 giờ]] .",
    "Đợi [[S:SCHEDULED_DELAY:30 giây]] rồi mở {device} tại {l1}",
    "Hẹn [[S:SCHEDULED_DELAY:15 phút]] nữa cho {device} ở {l1} chạy",
)
add("TURN_OFF", "off_delay",
    "Sau [[S:SCHEDULED_DELAY:10 phút]] tắt {device} {l1}",
    "[[S:SCHEDULED_DELAY:1 tiếng]] nữa ngắt {device} tại {l1}",
    "Hẹn tắt {device} ở {l1} sau [[S:SCHEDULED_DELAY:45 phút]]",
    "Đợi [[S:SCHEDULED_DELAY:20 giây]] rồi dừng {device} bên {l1}",
    "Hẹn [[S:SCHEDULED_DELAY:25 phút]] nữa tắt {device} tại {l1} .",
)

# 4. SCHEDULED_START_AT
add("TURN_ON", "on_start",
    "Lúc [[S:SCHEDULED_START_AT:21 giờ 20]] bật {device} {l1}",
    "Bật {device} ở {l1} vào [[S:SCHEDULED_START_AT:7 giờ sáng mai]]",
    "Hẹn [[S:SCHEDULED_START_AT:8 giờ tối nay]] mở {device} khu vực {l1}",
    "Đến [[S:SCHEDULED_START_AT:18 giờ 30 ngày mai]] thì cho {device} ở {l1} chạy",
    "Bật {device} tại {l1} lúc [[S:SCHEDULED_START_AT:6 giờ sáng]]",
)
add("TURN_OFF", "off_start",
    "Lúc [[S:SCHEDULED_START_AT:23 giờ]] tắt {device} {l1}",
    "Hẹn tắt {device} ở {l1} vào [[S:SCHEDULED_START_AT:9 giờ tối]]",
    "Đúng [[S:SCHEDULED_START_AT:6 giờ sáng mai]] ngắt {device} khu vực {l1}",
    "Tắt {device} tại {l1} lúc [[S:SCHEDULED_START_AT:20 giờ 15]]",
    "Đúng [[S:SCHEDULED_START_AT:19 giờ 30]] hãy tắt {device} ở {l1} .",
)

# 5. SCHEDULED_END_AT
add("TURN_ON", "on_end",
    "Bật {device} {l1} cho đến [[S:SCHEDULED_END_AT:23 giờ]]",
    "Mở {device} ở {l1} tới [[S:SCHEDULED_END_AT:6 giờ sáng mai]]",
    "Cho {device} khu vực {l1} hoạt động đến [[S:SCHEDULED_END_AT:9 giờ tối]]",
    "Bật {device} tại {l1} và tắt vào [[S:SCHEDULED_END_AT:22 giờ 30]]",
)
add("TURN_OFF", "off_end",
    "Tắt {device} {l1} tới [[S:SCHEDULED_END_AT:7 giờ sáng mai]]",
    "Cho {device} tại {l1} nghỉ đến [[S:SCHEDULED_END_AT:19 giờ]]",
    "Ngắt {device} ở {l1} cho đến [[S:SCHEDULED_END_AT:8 giờ sáng mai]] .",
    "Giữ {device} tại {l1} ở trạng thái tắt tới [[S:SCHEDULED_END_AT:21 giờ]] .",
)

# 6. DELAY + DURATION
add("TURN_ON", "on_delay_duration",
    "[[S:SCHEDULED_DELAY:10 phút]] nữa bật {device} {l1} trong [[S:DURATION:30 phút]]",
    "Sau [[S:SCHEDULED_DELAY:5 phút]] mở {device} ở {l1} khoảng [[S:DURATION:1 giờ]]",
    "Đợi [[S:SCHEDULED_DELAY:20 giây]] rồi cho {device} tại {l1} chạy [[S:DURATION:40 giây]]",
    "Hẹn bật {device} ở {l1} sau [[S:SCHEDULED_DELAY:2 giờ]] trong [[S:DURATION:15 phút]]",
)
add("TURN_OFF", "off_delay_duration",
    "Sau [[S:SCHEDULED_DELAY:5 phút]] tắt {device} {l1} trong [[S:DURATION:10 phút]]",
    "[[S:SCHEDULED_DELAY:1 giờ]] nữa cho {device} tại {l1} ngừng [[S:DURATION:20 phút]]",
    "Đợi [[S:SCHEDULED_DELAY:15 phút]] rồi tắt {device} ở {l1} trong [[S:DURATION:30 phút]] .",
    "Hẹn sau [[S:SCHEDULED_DELAY:1 giờ]] ngắt {device} tại {l1} trong [[S:DURATION:20 phút]] .",
)

# 7. START_AT + DURATION
add("TURN_ON", "on_start_duration",
    "[[S:SCHEDULED_START_AT:22 giờ 20]] bật {device} {l1} trong [[S:DURATION:8 giờ]]",
    "Lúc [[S:SCHEDULED_START_AT:7 giờ sáng mai]] mở {device} tại {l1} khoảng [[S:DURATION:30 phút]]",
    "Cho {device} ở {l1} chạy [[S:DURATION:45 phút]] từ [[S:SCHEDULED_START_AT:18 giờ]]",
    "Bật {device} khu vực {l1} vào [[S:SCHEDULED_START_AT:20 giờ tối mai]] trong [[S:DURATION:1 tiếng]]",
)

# 8. START_AT + END_AT
add("TURN_ON", "on_start_end",
    "[[S:SCHEDULED_START_AT:21 giờ 20]] bật {device} {l1} đến [[S:SCHEDULED_END_AT:6 giờ sáng mai]]",
    "Mở {device} ở {l1} lúc [[S:SCHEDULED_START_AT:19 giờ]] và tắt lúc [[S:SCHEDULED_END_AT:22 giờ]]",
    "Từ [[S:SCHEDULED_START_AT:8 giờ sáng]] đến [[S:SCHEDULED_END_AT:9 giờ sáng]] bật {device} ở {l1}",
    "Cho {device} tại {l1} chạy từ [[S:SCHEDULED_START_AT:15 giờ]] tới [[S:SCHEDULED_END_AT:17 giờ]]",
)
add("TURN_OFF", "off_start_end",
    "Tắt {device} ở {l1} từ [[S:SCHEDULED_START_AT:12 giờ]] đến [[S:SCHEDULED_END_AT:13 giờ]]",
    "Cho {device} khu vực {l1} ngừng hoạt động lúc [[S:SCHEDULED_START_AT:14 giờ]] đến [[S:SCHEDULED_END_AT:15 giờ]]",
    "Giữ {device} tại {l1} ở trạng thái tắt từ [[S:SCHEDULED_START_AT:8 giờ]] đến [[S:SCHEDULED_END_AT:10 giờ]] .",
    "Ngắt {device} ở {l1} từ [[S:SCHEDULED_START_AT:23 giờ]] tới [[S:SCHEDULED_END_AT:6 giờ sáng mai]] .",
)

# 9. DELAY + END_AT
add("TURN_ON", "on_delay_end",
    "[[S:SCHEDULED_DELAY:10 phút]] nữa bật {device} {l1} đến [[S:SCHEDULED_END_AT:9 giờ sáng mai]]",
    "Sau [[S:SCHEDULED_DELAY:5 phút]] mở {device} ở {l1} cho tới [[S:SCHEDULED_END_AT:22 giờ]]",
    "Hẹn bật {device} tại {l1} sau [[S:SCHEDULED_DELAY:30 phút]], dừng ở [[S:SCHEDULED_END_AT:23 giờ]]",
)

# 10. HỦY LỊCH
add("CANCEL_SCHEDULE", "cancel",
    "Hủy lịch của {device} {l1}",
    "Bỏ hẹn giờ cho {device} ở {l1} .",
    "Hủy lịch bật {device} bên {l1}",
    "Không dùng lịch tắt {device} tại {l1} nữa, hủy lịch đi .",
    "Xóa lịch điều khiển {device} khu vực {l1}",
    "Ngưng lịch hẹn của {device} ở {l1}",
)

# 11. TRUY VẤN TRẠNG THÁI
add("QUERY_STATUS", "query",
    "{device} {l1} đang bật hay tắt ?",
    "Kiểm tra trạng thái {device} ở {l1}",
    "Cho tôi biết {device} tại {l1} có đang chạy không .",
    "{device} bên {l1} hiện hoạt động không ?",
    "Bây giờ {device} ở {l1} đang thế nào ?",
    "Xem {device} khu vực {l1} đã tắt chưa",
    "{device} tại {l1} có đang mở không nhỉ",
)

# 12. PHỦ ĐỊNH
add("NO_ACTION", "negated",
    "Đừng bật {device} {l1}",
    "Không cần tắt {device} ở {l1} đâu .",
    "Đừng mở {device} tại {l1} nhé .",
    "Tạm thời chưa bật {device} bên {l1}",
    "Không tắt {device} khu vực {l1} vào lúc [[S:SCHEDULED_START_AT:22 giờ]] .",
    "Đừng hẹn bật {device} ở {l1} sau [[S:SCHEDULED_DELAY:10 phút]]",
)

# 13. KHÔNG XÁC ĐỊNH
add("UNKNOWN", "unknown",
    "Xin chào",
    "Thời tiết hôm nay thế nào ?",
    "Kể một câu chuyện đi",
    "Bật đi",
    "Tắt cái đó giúp tôi",
    "Làm gì đó cho phòng sáng hơn .",
    "Mở nhạc thư giãn đi",
    "Bạn tên là gì ?",
    "Bật {device} {l1} rồi tắt một thiết bị khác .",
    "Tôi chưa quyết định có bật {device} ở {l1} hay không .",
)

# ======= TEMPLATE: 1 Device + N Location (và Schedule nếu có) =======
# Có thể thêm một lệnh add() mới với {l6}, {l7}... mà không sửa thuật toán main().
# Action chỉ được lấy từ ACTIONS[intent] khi trong template có {action}.

add("TURN_ON", "multi_on",
    "{action} {device} ở {l1}",
    "{action} {device} ở {l1}, {l2}, {l3}, {l4}",
    "Hãy {action} {device} ở {l1}, {l2}, {l3}, {l4}, {l5}",
    "Cho mình {action} {device} trong {l1} của {l2} .",
)
add("TURN_OFF", "multi_off",
    "{action} {device} tại {l1} nhé",
    "Làm ơn {action} {device} trong {l1} ở {l2}",
    "Hãy {action} {device} ở {l1}, {l2}, {l3}",
    "{action} {device} ở {l1}, {l2}, {l3}, {l4}",
    "Phiền bạn {action} {device} tại {l1}, {l2}, {l3}, {l4}, {l5}",
)
add("TURN_ON", "multi_on_delay",
    "Sau [[S:SCHEDULED_DELAY:10 phút]] hãy {action} {device} tại {l1} trên {l2}",
    "[[S:SCHEDULED_DELAY:5 phút]] nữa {action} {device} tại {l1}, {l2}, {l3}",
    "Hẹn {action} {device} ở {l1}, {l2}, {l3}, {l4} sau [[S:SCHEDULED_DELAY:30 phút]]",
)
add("TURN_OFF", "multi_off_duration",
    "{action} {device} ở {l1}, {l2} trong [[S:DURATION:20 phút]] rồi bật lại",
    "Hãy {action} {device} tại {l1}, {l2}, {l3} trong [[S:DURATION:5 phút]]",
)
add("TURN_ON", "multi_on_start_duration",
    "Lúc [[S:SCHEDULED_START_AT:21 giờ]] hãy {action} {device} tại {l1} ở {l2} trong [[S:DURATION:30 phút]]",
    "Từ [[S:SCHEDULED_START_AT:20 giờ]] {action} {device} ở {l1}, {l2}, {l3} trong [[S:DURATION:2 giờ]]",
)
add("TURN_ON", "multi_on_start_end",
    "Từ [[S:SCHEDULED_START_AT:19 giờ]] đến [[S:SCHEDULED_END_AT:22 giờ]] hãy {action} {device} tại {l1}, {l2}",
    "[[S:SCHEDULED_START_AT:21 giờ]] {action} {device} ở {l1}, {l2}, {l3}, {l4} đến [[S:SCHEDULED_END_AT:23 giờ]]",
)
add("TURN_ON", "multi_on_delay_duration",
    "Sau [[S:SCHEDULED_DELAY:10 phút]] {action} {device} ở {l1}, {l2}, {l3} trong [[S:DURATION:30 phút]]",
    "Hẹn {action} {device} ở {l1}, {l2}, {l3}, {l4}, {l5} sau [[S:SCHEDULED_DELAY:1 giờ]] trong [[S:DURATION:15 phút]]",
)
add("CANCEL_SCHEDULE", "multi_cancel",
    "Hủy lịch của {device} ở {l1}, {l2}",
    "Xóa lịch điều khiển {device} tại {l1}, {l2}, {l3}",
)
add("QUERY_STATUS", "multi_query",
    "{device} ở {l1}, {l2} có đang hoạt động không?",
    "Cho tôi biết trạng thái {device} tại {l1}, {l2}, {l3}",
)
add("NO_ACTION", "multi_negated",
    "Đừng bật {device} ở {l1}, {l2} .",
    "Không cần tắt {device} tại {l1}, {l2}, {l3} sau [[S:SCHEDULED_DELAY:5 phút]] .",
)



# 14. CÂU CHỈ CÓ DEVICE (0 LOCATION)
# Không có {l1}, {l2}... nên chạy bằng --n 0.
# {action} lấy từ ACTIONS theo intent; chỉ {device} có nhãn TAG.
# Các giá trị Schedule dùng kiểu văn bản Speech-to-Text ("giờ", không dùng "h").
# Đặt family riêng cho từng template để split theo nhóm nhất quán.

# 14.1. Bật/tắt ngay, không nêu vị trí.
add("TURN_ON", "on_no_location_now",
    "{action} {device}",
    "Hãy {action} {device} giúp tôi",
    "{action} {device} đi",
    "Làm ơn {action} {device}",
    "Bật {device} lên",
    "Bật giúp tôi {device} nhé",
)
add("TURN_OFF", "off_no_location_now",
    "{action} {device}",
    "Hãy {action} {device} giúp tôi",
    "{action} {device} đi",
    "Làm ơn {action} {device}",
    "Tắt {device} đi nhé",
    "Tắt giúp mình {device}",
)

# 14.2. Điều khiển trong một khoảng thời gian.
add("TURN_ON", "on_no_location_duration",
    "Bật {device} trong [[S:DURATION:30 phút]]",
    "Cho {device} hoạt động trong [[S:DURATION:2 giờ]]",
    "Mở {device} khoảng [[S:DURATION:15 phút]] rồi tự tắt",
)
add("TURN_OFF", "off_no_location_duration",
    "Tắt {device} trong [[S:DURATION:10 phút]] rồi bật lại",
    "Cho {device} ngừng hoạt động trong [[S:DURATION:1 giờ]]",
)

# 14.3. Điều khiển sau một khoảng trễ.
add("TURN_ON", "on_no_location_delay",
    "Sau [[S:SCHEDULED_DELAY:10 phút]] hãy {action} {device}",
    "[[S:SCHEDULED_DELAY:5 phút]] nữa bật {device}",
    "Hẹn bật {device} sau [[S:SCHEDULED_DELAY:30 phút]]",
)
add("TURN_OFF", "off_no_location_delay",
    "Sau [[S:SCHEDULED_DELAY:10 phút]] hãy {action} {device}",
    "[[S:SCHEDULED_DELAY:15 phút]] nữa tắt {device}",
    "Hẹn tắt {device} sau [[S:SCHEDULED_DELAY:1 giờ]]",
)

# 14.4. Điều khiển tại một mốc giờ cụ thể (dạng STT).
add("TURN_ON", "on_no_location_start",
    "Lúc [[S:SCHEDULED_START_AT:6 giờ]] bật {device}",
    "Hẹn [[S:SCHEDULED_START_AT:8 giờ 30]] mở {device}",
    "Bật {device} vào [[S:SCHEDULED_START_AT:7 giờ sáng mai]]",
)
add("TURN_OFF", "off_no_location_start",
    "Lúc [[S:SCHEDULED_START_AT:22 giờ]] tắt {device}",
    "Hẹn tắt {device} vào [[S:SCHEDULED_START_AT:8 giờ 30 tối nay]]",
    "Tắt {device} lúc [[S:SCHEDULED_START_AT:6 giờ sáng mai]]",
)

# 14.5. Duy trì trạng thái đến mốc thời gian cụ thể.
add("TURN_ON", "on_no_location_end",
    "Bật {device} cho đến [[S:SCHEDULED_END_AT:23 giờ]]",
    "Mở {device} tới [[S:SCHEDULED_END_AT:6 giờ sáng mai]]",
)
add("TURN_OFF", "off_no_location_end",
    "Tắt {device} đến [[S:SCHEDULED_END_AT:7 giờ sáng mai]]",
    "Cho {device} nghỉ tới [[S:SCHEDULED_END_AT:19 giờ]]",
)

# 14.6. Hai tham số thời gian, vẫn không có Location.
add("TURN_ON", "on_no_location_delay_duration",
    "Sau [[S:SCHEDULED_DELAY:10 phút]] bật {device} trong [[S:DURATION:30 phút]]",
    "Hẹn mở {device} sau [[S:SCHEDULED_DELAY:1 giờ]] trong [[S:DURATION:15 phút]]",
)
add("TURN_OFF", "off_no_location_delay_duration",
    "Sau [[S:SCHEDULED_DELAY:5 phút]] tắt {device} trong [[S:DURATION:10 phút]]",
)
add("TURN_ON", "on_no_location_start_duration",
    "Lúc [[S:SCHEDULED_START_AT:8 giờ 30]] bật {device} trong [[S:DURATION:2 giờ]]",
    "Cho {device} chạy trong [[S:DURATION:30 phút]] từ [[S:SCHEDULED_START_AT:6 giờ sáng mai]]",
)
add("TURN_ON", "on_no_location_start_end",
    "Bật {device} từ [[S:SCHEDULED_START_AT:18 giờ]] đến [[S:SCHEDULED_END_AT:22 giờ]]",
    "Lúc [[S:SCHEDULED_START_AT:8 giờ 30]] mở {device} tới [[S:SCHEDULED_END_AT:9 giờ 30]]",
)
add("TURN_OFF", "off_no_location_start_end",
    "Tắt {device} từ [[S:SCHEDULED_START_AT:12 giờ]] đến [[S:SCHEDULED_END_AT:13 giờ]]",
)
add("TURN_ON", "on_no_location_delay_end",
    "Sau [[S:SCHEDULED_DELAY:10 phút]] bật {device} đến [[S:SCHEDULED_END_AT:9 giờ sáng mai]]",
)

# 14.7. Các intent còn lại, có Device nhưng không có Location.
add("CANCEL_SCHEDULE", "cancel_no_location",
    "Hủy lịch của {device}",
    "Bỏ hẹn giờ cho {device}",
    "Xóa lịch điều khiển {device}",
)
add("QUERY_STATUS", "query_no_location",
    "{device} đang bật hay tắt?",
    "Kiểm tra trạng thái {device}",
    "{device} có đang hoạt động không?",
    "Cho tôi biết {device} có đang chạy không",
)
add("NO_ACTION", "negated_no_location",
    "Đừng bật {device}",
    "Không cần tắt {device} đâu",
    "Tạm thời chưa bật {device}",
    "Đừng hẹn bật {device} sau [[S:SCHEDULED_DELAY:10 phút]]",
    "Không tắt {device} vào lúc [[S:SCHEDULED_START_AT:22 giờ]]",
)
