namespace DeviceRegistry.Api.Models;

public class DeviceType
{
    // 1. id
    // 2. TypeName
    // 3. List trạng thái 

    // Primary key
    public int Id { get; set; }

    // Device type information, Example: LED, FAN, DOOR
    public string TypeName { get; set; } = string.Empty;

    // List trạng thái ứng với Type này
    // Example: ["ON", "OFF"] or ["OPEN", "CLOSED"]
    public string AllowedStatuses { get; set; } = "[]";

    // 1 DeviceType -> N Device
    public ICollection<Device> Devices { get; set; } = new List<Device>();
}