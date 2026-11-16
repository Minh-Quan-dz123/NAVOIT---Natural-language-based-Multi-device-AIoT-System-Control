namespace DeviceRegistry.Api.Models;
public class Schedule
{
    // TODO         
    // id, DeviceId
    // Delay
    // Duration
    // Schedule_At_Start
    // Schedule_At_End
    // 1 Device - 1 Schedule

    // 1. PRIMARY KEY
    public int Id { get; set; }

    // 2. FOREIGN KEY :  Một Schedule luôn thuộc về một Device.
    public int DeviceId { get; set; }

    // 3. SCHEDULE INFORMATION
    
    // Hành động muốn thực hiện: on hoặc off.
    //
    // cancel_schedule không lưu làm Action.
    // Đó là yêu cầu hủy lịch hiện hành.
    public string Action { get; set; } = string.Empty;

    // Số giây chờ trước khi thực hiện.
    // null: không sử dụng scheduled_delay.
    public int? Delay { get; set; }

    // Số giây duy trì trạng thái.
    // null: không sử dụng duration.
    public int? Duration { get; set; }

    // Unix timestamp tính bằng giây.
    // null: không chỉ định thời điểm bắt đầu tuyệt đối.
    public long? ScheduledStartAt { get; set; }

    // Unix timestamp tính bằng giây.
    // null: không chỉ định thời điểm kết thúc tuyệt đối.
    public long? ScheduledEndAt { get; set; }

   public long ExpiresAt { get; set; }


    // 5. TIMESTAMPS
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    public DateTime UpdatedAt { get; set; } = DateTime.UtcNow;


    // 6. NAVIGATION PROPERTY
    public Device Device { get; set; } = null!;



}