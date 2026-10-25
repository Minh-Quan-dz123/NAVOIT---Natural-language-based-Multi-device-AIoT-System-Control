
namespace DeviceRegistry.Api.DTOs;

// ==========================================
// 1. DEVICE CATALOG RESPONSE
// ==========================================

public class DeviceCatalogDto
{
    // ID Device trong database.
    public int DeviceId { get; set; }

    public string? DeviceName { get; set; }

    public string DeviceType { get; set; } = string.Empty;

    // Thông tin định tuyến tới vi điều khiển.
    // Nullable vì Device có thể chưa gắn MCU.
    public int? MicrocontrollerId { get; set; }

    public string? MicrocontrollerType { get; set; }

    public string? MacAddress { get; set; }

    public int? Gpio { get; set; }

    // Trạng thái thiết bị gần nhất.
    public string CurrentStatus { get; set; } = "UNKNOWN";

    // Trạng thái đồng bộ cấu hình.
    public string SyncStatus { get; set; } = "unassigned";

    // Mỗi phần tử là một nhóm tag đồng nghĩa.
    //
    // Ví dụ:
    // [
    //   ["đèn học"],
    //   ["phòng con gái", "phòng của con gái"],
    //   ["tầng 2"]
    // ]
    public List<List<string>> TagGroups { get; set; } = new();
}
