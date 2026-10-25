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

    // 1. PRIMARY KEY
    public int Id { get; set; }

    // 2. FOREIGN KEYS
    public int UserId { get; set; } // 1 device luôn thuộc về 1 user
    // public int ScheduleId { get; set; } // xóa
    public int? MicrocontrollerId { get; set; } // "?" nghĩa là có thể null

    public int DeviceTypeId { get; set; } // Một Device phải thuộc một DeviceType.

    // 3. DEVICE INFORMATION
    public string? DeviceName { get; set; }
    public int? Gpio { get; set; }

    // Mô tả ban đầu để NLP trích xuất các tag.
    // Ví dụ: "Đèn học trong phòng con gái ở tầng 2".
    public string? Description { get; set; }
    public DateTime CreateAt { get; set; } = DateTime.UtcNow;

    // 4. DEVICE STATUS
    // Trạng thái gần nhất được vi điều khiển báo cáo.
    // Ví dụ: ON, OFF, UNKNOWN.
    //
    // Không tự động thay đổi giá trị này chỉ vì
    // server vừa gửi một MQTT command.
    public string CurrentStatus { get; set; } = "UNKNOWN";

    // Thời điểm nhận trạng thái gần nhất từ vi điều khiển.
    // null nghĩa là chưa nhận được báo cáo trạng thái.
    public DateTime? StatusUpdatedAt { get; set; }

    // Trạng thái đồng bộ cấu hình Device với phần cứng:
    //
    // unassigned  : Chưa gắn Microcontroller.
    // pending     : Đang chờ xác nhận từ Microcontroller.
    // synced      : Đã xác nhận đồng bộ.
    // out_of_sync : Cấu hình server và phần cứng không khớp.
    // error       : Đồng bộ thất bại.
    //
    // Đây là trạng thái đồng bộ cấu hình,
    // không phải trạng thái kết nối mạng của Microcontroller.
    public string SyncStatus { get; set; } = "unassigned";


    // 5. NAVIGATION PROPERTIES
    public Microcontroller? Microcontroller { get; set; } = null!;
    public User User { get; set; } = null!; // N Device -> 1 User.
    public Schedule? Schedule { get; set; } = null!;
    public DeviceType DeviceType { get; set; } = null!;


    // 1 Device -> N DeviceTagGroup
    public ICollection<DeviceTagGroup> DeviceTagGroups { get; set; } = new List<DeviceTagGroup>();



}