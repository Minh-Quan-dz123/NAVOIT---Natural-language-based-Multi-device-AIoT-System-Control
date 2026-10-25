
using System.ComponentModel.DataAnnotations;

namespace DeviceRegistry.Api.DTOs;

// 1. CREATE DEVICE REQUEST

public class CreateDeviceRequestDto
{
    // Loại thiết bị bắt buộc phải tồn tại trong DeviceTypes.
    [Range(1, int.MaxValue)]
    public int DeviceTypeId { get; set; }

    // Có thể null nếu Device chưa được gắn với MCU.
    public int? MicrocontrollerId { get; set; }

    // Có thể null nếu chưa xác định chân GPIO.
    // Giá trị GPIO hợp lệ cụ thể phụ thuộc loại board.
    [Range(0, int.MaxValue)]
    public int? Gpio { get; set; }

    // Tên thiết bị do người dùng đặt.
    [MaxLength(150)]
    public string? DeviceName { get; set; }

    // Mô tả dùng để NLP trích xuất tag.
    [MaxLength(2000)]
    public string? Description { get; set; }

    // Không có UserId:
    // Controller lấy UserId từ JWT.

    // Không có CurrentStatus:
    // Trạng thái phải được cập nhật từ vi điều khiển.
}

// 2. UPDATE DEVICE REQUEST
public class UpdateDeviceRequestDto
{
    // Nullable để PATCH từng trường.
    // null nghĩa là không thay đổi trường đó.
    // Chuỗi "" có thể dùng để xóa tên hoặc mô tả.

    [MaxLength(150)]
    public string? DeviceName { get; set; }

    [MaxLength(2000)]
    public string? Description { get; set; }

    [Range(1, int.MaxValue)]
    public int? DeviceTypeId { get; set; }

    // Không cho đổi MicrocontrollerId hoặc Gpio tại đây.
    // Việc thay đổi phần cứng cần API binding riêng.
}

// 3. DEVICE RESPONSE

public class DeviceResponseDto
{
    public int Id { get; set; }

    public string? DeviceName { get; set; }

    public string? Description { get; set; }

    public int DeviceTypeId { get; set; }

    public string DeviceTypeName { get; set; } = string.Empty;

    // Có thể null khi Device chưa gắn phần cứng.
    public int? MicrocontrollerId { get; set; }

    public string? MicrocontrollerType { get; set; }

    public string? MacAddress { get; set; }

    public int? Gpio { get; set; }

    // Trạng thái gần nhất được báo cáo.
    public string CurrentStatus { get; set; } = "UNKNOWN";

    public DateTime? StatusUpdatedAt { get; set; }

    // Trạng thái đồng bộ với vi điều khiển.
    public string SyncStatus { get; set; } = "unassigned";

    public DateTime CreatedAt { get; set; }
}
