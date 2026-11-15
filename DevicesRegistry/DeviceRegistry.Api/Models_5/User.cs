namespace DeviceRegistry.Api.Models;

public class User
{
    // TODO, 
    // 1. id
    // 2. username
    // 3. password
    // 4. Phone
    // 5. CreateAt
    // 6. role
    // quan hệ: 1 User -> n esp32
    // 1 User -> n Device

    // Primary key
    public int Id { get; set; }

    // User information
    public string Username { get; set; } = string.Empty;

    // Store the password hash
    public string Password { get; set; } = string.Empty;

    // Số điện thoại (không bắt buộc
    public string? Phone { get; set; }

    // Phân quyền tài khoản
    // User: người dùng thông thường
    // Admin: quản trị viên
    public string Role { get; set; } = "User";


    // Thời gian tạo tài khoản (UTC)
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

    // 1 User -> N Microcontroller
    public ICollection<Microcontroller> Microcontrollers { get; set; }
        = new List<Microcontroller>();

    // 1 User -> N Device
    public ICollection<Device> Devices { get; set; }
        = new List<Device>();
}