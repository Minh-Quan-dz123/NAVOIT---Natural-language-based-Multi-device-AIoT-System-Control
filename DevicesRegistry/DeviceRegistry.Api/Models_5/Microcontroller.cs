
namespace DeviceRegistry.Api.Models;

public class Microcontroller
{
    // Khóa chính
    public int Id { get; set; }

    // Chủ sở hữu MCU.
    // null = chưa cấp quyền cho User nào.
    public int? UserId { get; set; }

    // Định danh phần cứng
    public string MacAddress { get; set; } = string.Empty;

    // Loại MCU: esp32, esp8266, stm32...
    public string Type { get; set; } = string.Empty;

    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

    // Trạng thái kết nối
    public string ConnectionStatus { get; set; } = "unknown";

    public DateTime? LastSeenAt { get; set; }

    // Navigation Properties

    // Có thể chưa có User sở hữu.
    public User? User { get; set; }

    // Một MCU có thể liên kết nhiều Device.
    public ICollection<Device> Devices { get; set; }
        = new List<Device>();
}
