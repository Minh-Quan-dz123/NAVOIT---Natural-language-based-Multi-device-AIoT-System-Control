namespace DeviceRegistry.Api.Models;
public class Device
{
    // TODO
    // 1. id                (pk)
    // 2. MicrocontrollerId (fk)
    // 3. UserId            (fk)
    // 4. ScheduleId        (fk)
    // 5. DeviceName  (có thể null)
    // 6. DeviceTypeId      (fk)
    // 7. Gpio
    // 8. CreateAt, 
    // 9. DeviceCurrentStatus của Device
    // cần phải có cơ chế quản lý cái 9, hiện tại thiết kế chưa có


    // 1 Esp32 -> n Device
    // 1 User -> n Device
    // 1 Device -> 1 Schedule
    // 1 Device -> N DeviceTagGroup
    // n Device -> 1 DeviceType

    // Primary key
    public int Id { get; set; }

    // Foreign keys
    public int MicrocontrollerId { get; set; }
    public int UserId { get; set; }
    // public int ScheduleId { get; set; } // xóa
    public int DeviceTypeId { get; set; }

    // Device information
    public string? DeviceName { get; set; }
    public int Gpio { get; set; }
    public DateTime CreateAt { get; set; } = DateTime.UtcNow;

    // Current status of this device
      public string CurrentStatus { get; set; } = string.Empty;


    // liên kết tới object khác
    public Microcontroller Microcontroller { get; set; } = null!;
    public User User { get; set; } = null!;
    public Schedule Schedule { get; set; } = null!;
    public DeviceType DeviceType { get; set; } = null!;


    // 1 Device -> N DeviceTagGroup
    public ICollection<DeviceTagGroup> DeviceTagGroups { get; set; }
        = new List<DeviceTagGroup>();



}