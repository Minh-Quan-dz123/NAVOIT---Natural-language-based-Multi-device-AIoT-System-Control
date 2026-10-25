namespace DeviceRegistry.Api.Models;

public class TagGroup
{
    // 1. Id
    // 2. CreatedAt
    // 1 TagGroup - n Tag
    // 1 TagGroup - n DeviceTagGroup
    // có chỉ có Id để hỗ trợ nhóm, chứ ko có value

    // 1. PRIMARY KEY
    public int Id { get; set; }

    // 2. FOREIGN KEY
    public int UserId { get; set; }

    // 3. INFORMATION
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

    // 4. NAVIGATION PROPERTIES

    // 1 TagGroup -> N Tag
    public ICollection<Tag> Tags { get; set; }
        = new List<Tag>();

    // 1 TagGroup -> N DeviceTagGroup
    public ICollection<DeviceTagGroup> DeviceTagGroups { get; set; }
        = new List<DeviceTagGroup>();
}