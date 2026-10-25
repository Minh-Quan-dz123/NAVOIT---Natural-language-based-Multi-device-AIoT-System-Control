
using System.ComponentModel.DataAnnotations;

namespace DeviceRegistry.Api.DTOs;

public class UpdateAliasRequestDto
{
    // Tag đã tồn tại trong một TagGroup.
    //
    // Ví dụ: "phòng bếp".
    [Required]
    public string ExistingTag { get; set; } = string.Empty;

    // Tag đồng nghĩa cần thêm.
    //
    // Ví dụ: "nhà bếp".
    [Required]
    public string NewTag { get; set; } = string.Empty;

    // Không có UserId vì lấy từ JWT.
}
