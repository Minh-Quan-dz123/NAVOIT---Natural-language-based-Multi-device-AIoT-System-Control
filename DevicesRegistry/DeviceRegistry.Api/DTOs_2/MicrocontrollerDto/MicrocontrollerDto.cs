
using System;
using System.ComponentModel.DataAnnotations;

namespace DeviceRegistry.Api.DTOs;

// 1. Admin tạo MCU mới
public class CreateMicrocontrollerRequestDto
{
    [Required(ErrorMessage = "Type không được để trống.")]
    [MaxLength(50)]
    public string Type { get; set; } = string.Empty;

    [Required(ErrorMessage = "MacAddress không được để trống.")]
    public string MacAddress { get; set; } = string.Empty;

    // Không bắt buộc nhập chủ sở hữu.
    // null: MCU chưa được cấp cho User nào.
    // Có giá trị: MCU được cấp cho User tương ứng.
    [Range(1, int.MaxValue, ErrorMessage = "UserId không hợp lệ.")]
    public int? UserId { get; set; }
}


// 2. Admin cập nhật thông tin MCU
public class UpdateMicrocontrollerRequestDto
{
    // null nghĩa là giữ nguyên giá trị cũ.
    public string? Type { get; set; }

    // null nghĩa là giữ nguyên giá trị cũ.
    public string? MacAddress { get; set; }
}


// 3. Admin cấp quyền hoặc chuyển nhượng MCU
public class TransferMicrocontrollerRequestDto
{
    [Range(1, int.MaxValue, ErrorMessage = "UserId không hợp lệ.")]
    public int UserId { get; set; }
}


// 4. Dữ liệu trả về cho Frontend
public class MicrocontrollerResponseDto
{
    public int Id { get; set; }

    public string Type { get; set; } = string.Empty;

    public string MacAddress { get; set; } = string.Empty;

    // null nếu MCU chưa có chủ sở hữu.
    public int? UserId { get; set; }

    // null nếu MCU chưa có chủ sở hữu.
    public string? OwnerUsername { get; set; }

    public string ConnectionStatus { get; set; } = "unknown";

    public DateTime? LastSeenAt { get; set; }

    public DateTime CreatedAt { get; set; }

    // Số Device đang liên kết với MCU.
    public int DeviceCount { get; set; }
}


// 5. MICROCONTROLLER DEVICE RESPONSE
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
