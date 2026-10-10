namespace DeviceRegistry.Api.DTOs;

public class UserResponseDto
{
    public int Id { get; set; }

    public string Username { get; set; } = string.Empty;

    public string? Phone { get; set; }

    public DateTime CreatedAt { get; set; }
}