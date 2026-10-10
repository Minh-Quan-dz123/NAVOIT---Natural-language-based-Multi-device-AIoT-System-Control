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

    // Primary key
    public int Id { get; set; }

    // Foreign key
    public int DeviceId { get; set; }

    // Schedule information
    public int Delay { get; set; }
    public int Duration { get; set; }

    public string Schedule_At_Start { get; set; } = string.Empty;
    public string Schedule_At_End { get; set; } = string.Empty;

    // Navigation property
    public Device Device { get; set; } = null!;
}