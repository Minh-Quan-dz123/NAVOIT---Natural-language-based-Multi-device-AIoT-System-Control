
using System.ComponentModel.DataAnnotations;

namespace DeviceRegistry.Api.Models;

public class MicrocontrollerType
{
    // Khóa chính
    public int Id { get; set; }

    // Tên loại vi điều khiển
    // Ví dụ: esp32, esp8266, stm32
    [Required]
    [MaxLength(50)]
    public string TypeName { get; set; } = string.Empty;
}
