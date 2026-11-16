
using System.ComponentModel.DataAnnotations;

namespace DeviceRegistry.Api.DTOs;

public class UpsertScheduleRequestDto
{
    [Required]
    public string Action { get; set; } = string.Empty;

    [Range(0, int.MaxValue)]
    public int? ScheduledDelay { get; set; }

    [Range(1, int.MaxValue)]
    public int? Duration { get; set; }

    [Range(1, long.MaxValue)]
    public long? ScheduledStartAt { get; set; }

    [Range(1, long.MaxValue)]
    public long? ScheduledEndAt { get; set; }
}

public class ScheduleResponseDto
{
    public int Id { get; set; }
    public int DeviceId { get; set; }

    public string Action { get; set; } = string.Empty;

    public int? ScheduledDelay { get; set; }
    public int? Duration { get; set; }
    public long? ScheduledStartAt { get; set; }
    public long? ScheduledEndAt { get; set; }

    public long ExpiresAt { get; set; }
    public bool IsExpired { get; set; }

    public DateTime CreatedAt { get; set; }
    public DateTime UpdatedAt { get; set; }
}
