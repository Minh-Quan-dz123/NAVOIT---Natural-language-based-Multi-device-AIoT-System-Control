
using System.ComponentModel.DataAnnotations;

namespace DeviceRegistry.Api.DTOs;

// 1. UPDATE DEVICE BINDING

public class UpdateDeviceBindingRequestDto
{
    // User sở hữu Device.
    // API này chỉ dành cho NLP Server đã được xác thực.
    [Range(1, int.MaxValue)]
    public int UserId { get; set; }

    // Cả hai null: bỏ liên kết MCU/GPIO.
    // Cả hai có giá trị: chuyển sang liên kết mới.
    public int? MicrocontrollerId { get; set; }

    public int? Gpio { get; set; }
}

// 2. REPORT DEVICE STATUS

public class ReportDeviceStatusRequestDto
{
    [Range(1, int.MaxValue)]
    public int UserId { get; set; }

    // Thông tin dùng để kiểm tra response
    // có đúng vị trí phần cứng hiện tại không.
    [Range(1, int.MaxValue)]
    public int MicrocontrollerId { get; set; }

    [Range(0, int.MaxValue)]
    public int Gpio { get; set; }

    // synced, out_of_sync hoặc error.
    [Required]
    public string SyncStatus { get; set; } = string.Empty;

    // ON, OFF hoặc UNKNOWN.
    // null: Không thay đổi CurrentStatus.
    public string? CurrentStatus { get; set; }
}

// 3. REFRESH DEVICE RESPONSE

// Tương ứng REFRESH_DEVICE_RESPONSE của ESP32.
public class RefreshDevicesRequestDto
{
    [Range(1, int.MaxValue)]
    public int UserId { get; set; }

    [Required]
    public string HardwareId { get; set; } = string.Empty;

    [Range(0, int.MaxValue)]
    public int DeviceCount { get; set; }

    [Required]
    public List<int> Gpios { get; set; } = new();

    [Required]
    public List<string> DeviceTypes { get; set; } = new();

    [Required]
    public List<string> DeviceNames { get; set; } = new();

    [Required]
    public List<string> DeviceStatus { get; set; } = new();
}

// 4. REGISTER SCHEDULE COMMAND

public class RegisterScheduleCommandRequestDto
{
    [Range(1, int.MaxValue)]
    public int UserId { get; set; }

    [Required]
    public string CommandId { get; set; } = string.Empty;
}

// 5. REPORT SCHEDULE ACK
public class ScheduleAckRequestDto
{
    [Range(1, int.MaxValue)]
    public int UserId { get; set; }

    [Required]
    public string CommandId { get; set; } = string.Empty;

    // true : Firmware xác nhận thành công.
    // false: Firmware xác nhận thất bại.
    //
    // Nullable để phân biệt false với không gửi trường này.
    [Required]
    public bool? Accepted { get; set; }
}
