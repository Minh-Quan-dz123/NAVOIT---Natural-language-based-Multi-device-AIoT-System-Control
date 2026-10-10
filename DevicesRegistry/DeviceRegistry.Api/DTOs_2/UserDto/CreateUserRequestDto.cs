using System.ComponentModel.DataAnnotations;


namespace DeviceRegistry.Api.DTOs;
public class CreateUserRequestDto
{
    // TODO:
    // Username
    // Password
    // Phone [10 số]
    public string Username { get; set; } = string.Empty;

    [Required]
    [MinLength(8, ErrorMessage = "Password phải có ít nhất 8 ký tự.")]
    public string Password { get; set; } = string.Empty;

    [System.ComponentModel.DataAnnotations.RegularExpression(
        @"^\d{10}$",
        ErrorMessage = "Phone phải gồm đúng 10 chữ số."
    )]
    public string? Phone { get; set; }

}