namespace DeviceRegistry.Api.Models;

public class DeviceTagGroup
{
    // 1. Id
    // 2. DeviceId (fk)
    // 3. TagGroupId (fk)
    // 4. CreatedAt
    // TODO:
    // n Tag -> 1 Tag Group
    // n Tag Group -> n Device

    // Primary key
    public int Id { get; set; }

    // Foreign keys
    public int DeviceId { get; set; }
    public int TagGroupId { get; set; }

    // Timestamp
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

    // Navigation properties
    public Device Device { get; set; } = null!;
    public TagGroup TagGroup { get; set; } = null!;
}