namespace DeviceRegistry.Api.DTOs;

public class AuthResponseDto
{
    public string AccessToken { get; set; } = string.Empty;

    public DateTime ExpiresAt { get; set; }

    public int UserId { get; set; }

    public string Username { get; set; } = string.Empty;
}