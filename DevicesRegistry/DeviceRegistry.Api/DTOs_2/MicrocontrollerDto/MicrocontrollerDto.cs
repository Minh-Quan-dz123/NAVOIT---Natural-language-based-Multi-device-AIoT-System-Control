
using System.ComponentModel.DataAnnotations;

namespace DeviceRegistry.Api.DTOs;

// 1. CREATE MICROCONTROLLER
// DTO nhận thông tin đăng ký Microcontroller.
// UserId không có trong DTO vì lấy từ JWT.
public class CreateMicrocontrollerRequestDto
{
    [Required(ErrorMessage = "Type không được để trống.")]
    public string Type { get; set; } = string.Empty;

    [Required(ErrorMessage = "MacAddress không được để trống.")]
    public string MacAddress { get; set; } = string.Empty;
}

// 2. UPDATE MICROCONTROLLER
// Các thuộc tính nullable để hỗ trợ PATCH.
// Không gửi thuộc tính nào thì giữ nguyên giá trị cũ.
public class UpdateMicrocontrollerRequestDto
{
    public string? Type { get; set; }

    public string? MacAddress { get; set; }
}

// 3. MICROCONTROLLER RESPONSE
// Chỉ trả về các dữ liệu cần thiết.
// Không trả trực tiếp Entity để tránh serialize
// các navigation property không cần thiết.
public class MicrocontrollerResponseDto
{
    public int Id { get; set; }
    public string Type { get; set; } = string.Empty;
    public string MacAddress { get; set; } = string.Empty;
    public string ConnectionStatus { get; set; } = "unknown";
    public DateTime? LastSeenAt { get; set; }
    public DateTime CreatedAt { get; set; }

    // Số Device đang liên kết với MCU.
    public int DeviceCount { get; set; }
}

// 4. MICROCONTROLLER DEVICE RESPONSE

// DTO dùng cho API:
// GET /api/microcontroller/{id}/devices
public class MicrocontrollerDeviceDto
{
    public int Id { get; set; }
    public string? DeviceName { get; set; }
    public int? Gpio { get; set; }
    public int DeviceTypeId { get; set; }
    public string CurrentStatus { get; set; } = "UNKNOWN";
    public string SyncStatus { get; set; } = "unassigned";
}
