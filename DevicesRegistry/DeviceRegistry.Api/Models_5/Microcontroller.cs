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

    // 1. PRIMARY KEY
    public int Id { get; set; }

    // 2. FOREIGN KEY
    public int UserId { get; set; }

     // 3. MICROCONTROLLER INFORMATION
    // Ví dụ: D8BFC0800FA0
    public string MacAddress { get; set; } = string.Empty;

    // Loại vi điều khiển: esp32, esp8266,...    
    public string Type { get; set; } = string.Empty;

    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

    // 4. CONNECTION STATUS
    // unknown: Chưa xác định trạng thái kết nối.
    // online : Vi điều khiển đang kết nối.
    // offline: Vi điều khiển mất kết nối.
    //
    // Trường này sẽ được cập nhật bởi cơ chế đồng bộ MQTT
    // trong các đợt triển khai sau.
    public string ConnectionStatus { get; set; } = "unknown";

    // Thời điểm nhận tín hiệu hợp lệ gần nhất từ MCU.
    // null khi chưa nhận được tín hiệu.
    public DateTime? LastSeenAt { get; set; }


    // 5. NAVIGATION PROPERTIES
    // N Microcontroller -> 1 User.
    public User User { get; set; } = null!;

    // 1 Microcontroller -> N Device
    public ICollection<Device> Devices { get; set; } = new List<Device>();
}