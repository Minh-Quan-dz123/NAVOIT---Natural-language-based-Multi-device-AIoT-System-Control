namespace DeviceRegistry.Api.Models;

public class Tag
{
    // TODO:
    // 1. Id
    // 2. value (là text)
    // 3. CreatedAt
    // 4. TagGroupId
    // n Tag (tag đồng nghĩa) -> 1 TagGroup
    // n TagGroup -> n Device
    
    // Primary key
    public int Id { get; set; }

    // Tag information
    public string Value { get; set; } = string.Empty;

    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

    // Foreign key
    public int TagGroupId { get; set; }

    // Navigation property
    public TagGroup TagGroup { get; set; } = null!;
}