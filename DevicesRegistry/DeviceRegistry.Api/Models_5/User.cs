namespace DeviceRegistry.Api.Models;

public class User
{
    // TODO, 
    // 1. id
    // 2. username
    // 3. password
    // 4. Phone
    // 5. CreateAt
    // quan hệ: 1 User -> n esp32
    // 1 User -> n Device

    // Primary key
    public int Id { get; set; }

    // User information
    public string Username { get; set; } = string.Empty;

    // Store the password hash, not the plaintext password
    public string Password { get; set; } = string.Empty;

    public string? Phone { get; set; }

    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

    // 1 User -> N Microcontroller
    public ICollection<Microcontroller> Microcontrollers { get; set; }
        = new List<Microcontroller>();

    // 1 User -> N Device
    public ICollection<Device> Devices { get; set; }
        = new List<Device>();
}