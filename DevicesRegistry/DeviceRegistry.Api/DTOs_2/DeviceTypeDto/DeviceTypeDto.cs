
using System.ComponentModel.DataAnnotations;

namespace DeviceRegistry.Api.DTOs;

// 1. CREATE DEVICE TYPE REQUEST
public class CreateDeviceTypeRequestDto
{
    // Tên loại thiết bị.
    // Ví dụ: light, fan, door.
    [Required]
    [MaxLength(50)]
    public string TypeName { get; set; } = string.Empty;

    // Danh sách các trạng thái được khai báo cho loại này.
    // Ví dụ: ["ON", "OFF"].
    //
    // Client gửi JSON array, không cần tự chuyển
    // danh sách thành chuỗi JSON.
    [Required]
    [MinLength(1)]
    public List<string> AllowedStatuses { get; set; } = new();
}

// 2. UPDATE DEVICE TYPE REQUEST

public class UpdateDeviceTypeRequestDto
{
    // Nullable để PATCH từng trường.
    //
    // null: Không cập nhật trường này.
    // Có giá trị: Cập nhật trường tương ứng.
    [MaxLength(50)]
    public string? TypeName { get; set; }

    public List<string>? AllowedStatuses { get; set; }
}

// 3. DEVICE TYPE RESPONSE
public class DeviceTypeResponseDto
{
    public int Id { get; set; }

    public string TypeName { get; set; } = string.Empty;

    // Trả về danh sách thay vì chuỗi JSON.
    public List<string> AllowedStatuses { get; set; } = new();

    // Số Device đang sử dụng DeviceType này.
    public int DeviceCount { get; set; }
}
