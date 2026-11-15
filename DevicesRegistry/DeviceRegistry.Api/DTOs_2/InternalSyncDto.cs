
using System.ComponentModel.DataAnnotations;

namespace DeviceRegistry.Api.DTOs;

// 1. UPDATE DEVICE BINDING
public class UpdateDeviceBindingRequestDto
{
    [Range(1, int.MaxValue)]
    public int UserId { get; set; }

    public int? MicrocontrollerId { get; set; }

    public int? Gpio { get; set; }
}

// 2. REPORT DEVICE STATUS
public class ReportDeviceStatusRequestDto
{
    [Range(1, int.MaxValue)]
    public int UserId { get; set; }

    [Range(1, int.MaxValue)]
    public int MicrocontrollerId { get; set; }

    [Range(0, int.MaxValue)]
    public int Gpio { get; set; }

    [Required]
    public string SyncStatus { get; set; } = string.Empty;

    public string? CurrentStatus { get; set; }
}

// 3. REFRESH DEVICES
public class RefreshDevicesRequestDto
{
    [Range(1, int.MaxValue)]
    public int UserId { get; set; }

    [Required]
    public string HardwareId { get; set; } = string.Empty;

    [Range(0, int.MaxValue)]
    public int DeviceCount { get; set; }

    [Required]
    public List<int> Gpios { get; set; } = new();

    [Required]
    public List<string> DeviceTypes { get; set; } = new();

    [Required]
    public List<string> DeviceNames { get; set; } = new();

    [Required]
    public List<string> DeviceStatus { get; set; } = new();
}
