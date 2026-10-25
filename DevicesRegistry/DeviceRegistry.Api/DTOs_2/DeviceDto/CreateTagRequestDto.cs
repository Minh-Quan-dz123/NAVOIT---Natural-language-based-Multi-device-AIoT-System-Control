
using System.ComponentModel.DataAnnotations;

namespace DeviceRegistry.Api.DTOs;

public class CreateTagRequestDto
{
    // ==========================================
    // LIST TAGS
    // ==========================================

    // Danh sách tag đã được NLP trích xuất
    // và người dùng xác nhận.
    //
    // Ví dụ:
    // [
    //     "đèn học",
    //     "phòng con gái",
    //     "tầng 2"
    // ]
    //
    // PUT /api/device/{deviceId}/tags
    //
    // Không nhận UserId vì lấy từ JWT.
    // Không nhận DeviceId vì lấy từ URL.
    //
    // [] nghĩa là bỏ tất cả liên kết TagGroup
    // của Device, không xóa TagGroup khỏi database.

    [Required]
    [MaxLength(20)]
    public List<string> Tags { get; set; } = new();
}
