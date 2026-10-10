using System.ComponentModel.DataAnnotations;

namespace DeviceRegistry.Api.DTOs;

public class ChangePasswordRequestDto
{
    [Required]
    public string OldPassword { get; set; } = string.Empty;

    [Required]
    [MinLength(8, ErrorMessage = "Mật khẩu mới phải có ít nhất 8 ký tự.")]
    public string NewPassword { get; set; } = string.Empty;
}