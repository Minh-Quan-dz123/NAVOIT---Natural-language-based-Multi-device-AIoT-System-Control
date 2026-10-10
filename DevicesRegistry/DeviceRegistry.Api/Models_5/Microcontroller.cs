namespace DeviceRegistry.Api.Models;
public class Microcontroller
{
    // TODO, 
    // 1. id
    // 2. UserId
    // 3. MacAddress
    // 4. Type (esp32, esp8266)
    // 5. CreateAt
    
    // 1 User -> n Esp32
    // 1 Esp32 -> nhiều Device

    // Primary key
    public int Id { get; set; }
    // Foreign key
    public int UserId { get; set; }

    // Microcontroller information
    public string MacAddress { get; set; } = string.Empty;

    // Examples: ESP32, ESP8266
    public string Type { get; set; } = string.Empty;

    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

    // Navigation properties
    public User User { get; set; } = null!;

    // 1 Microcontroller -> N Device
    public ICollection<Device> Devices { get; set; }
        = new List<Device>();
}