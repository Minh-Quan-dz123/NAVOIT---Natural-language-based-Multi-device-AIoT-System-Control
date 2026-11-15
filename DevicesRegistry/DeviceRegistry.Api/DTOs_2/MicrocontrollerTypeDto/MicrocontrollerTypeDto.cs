
using System.ComponentModel.DataAnnotations;

namespace DeviceRegistry.Api.DTOs;

// DTO tạo loại vi điều khiển
public class CreateMicrocontrollerTypeRequestDto
{
    [Required]
    [MaxLength(50)]
    public string TypeName { get; set; } = string.Empty;
}

// DTO cập nhật loại vi điều khiển
public class UpdateMicrocontrollerTypeRequestDto
{
    [Required]
    [MaxLength(50)]
    public string TypeName { get; set; } = string.Empty;
}

// DTO trả dữ liệu về Frontend
public class MicrocontrollerTypeResponseDto
{
    public int Id { get; set; }

    public string TypeName { get; set; } = string.Empty;
}
