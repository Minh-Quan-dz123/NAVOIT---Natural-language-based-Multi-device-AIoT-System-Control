using System.ComponentModel.DataAnnotations;

namespace DeviceRegistry.Api.DTOs;
public class UpdateUserRequestDto
{
    // null nghĩa là không cập nhật trường đó
    [MinLength(1, ErrorMessage = "Username không được để trống.")]
    public string? Username { get; set; }

    [RegularExpression(
        @"^\d{10}$",
        ErrorMessage = "Phone phải gồm đúng 10 chữ số."
    )]
    public string? Phone { get; set; }

}