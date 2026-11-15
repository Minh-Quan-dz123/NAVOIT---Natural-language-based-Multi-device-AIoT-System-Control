using System.ComponentModel.DataAnnotations;


namespace DeviceRegistry.Api.DTOs;
public class CreateUserRequestDto
{
    // TODO:
    // Username
    // Password
    // Phone [10 số]
    [Required(ErrorMessage = "Username không được để trống.")]
    public string Username { get; set; } = string.Empty;

    [Required(ErrorMessage = "Password không được để trống.")]
    [MinLength(8, ErrorMessage = "Password phải có ít nhất 8 ký tự.")]
    public string Password { get; set; } = string.Empty;

    [RegularExpression(
        @"^[0-9]{10}$",
        ErrorMessage = "Phone phải gồm đúng 10 chữ số."
    )]
    public string? Phone { get; set; }

}