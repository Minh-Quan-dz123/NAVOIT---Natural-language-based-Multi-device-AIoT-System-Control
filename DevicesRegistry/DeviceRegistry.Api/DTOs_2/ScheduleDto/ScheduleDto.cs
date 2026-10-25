
using System.ComponentModel.DataAnnotations;

namespace DeviceRegistry.Api.DTOs;

// 1. CREATE / UPDATE SCHEDULE REQUEST
public class UpsertScheduleRequestDto
{
    // on hoặc off.
    [Required]
    public string Action { get; set; } = string.Empty;

    // Các giá trị tính bằng giây.
    //
    // Delay có thể bằng 0.
    // Duration phải lớn hơn 0 nếu được cung cấp.
    [Range(0, int.MaxValue)]
    public int? ScheduledDelay { get; set; }

    [Range(1, int.MaxValue)]
    public int? Duration { get; set; }

    // Unix timestamp UTC tính bằng giây.
    // Ví dụ: 1792750800
    //
    // Không nhận chuỗi thời gian ở hai trường này.
    [Range(1, long.MaxValue)]
    public long? ScheduledStartAt { get; set; }

    [Range(1, long.MaxValue)]
    public long? ScheduledEndAt { get; set; }

    // Không nhận DeviceId trong Body.
    // DeviceId lấy từ URL.
    //
    // Không nhận UserId vì lấy từ JWT.
    //
    // Không nhận SyncStatus hay CommandId.
    // Client không được tự xác nhận lịch đã đồng bộ.
}

// 2. SCHEDULE RESPONSE

public class ScheduleResponseDto
{
    public int Id { get; set; }

    public int DeviceId { get; set; }

    public string Action { get; set; } = string.Empty;

    public int? ScheduledDelay { get; set; }

    public int? Duration { get; set; }

    public long? ScheduledStartAt { get; set; }

    public long? ScheduledEndAt { get; set; }

    // Trạng thái đồng bộ lịch với ESP.
    public string SyncStatus { get; set; } = "pending";

    public string? CommandId { get; set; }

    public DateTime CreatedAt { get; set; }

    public DateTime UpdatedAt { get; set; }

    public DateTime? AcknowledgedAt { get; set; }
}
