
namespace DeviceRegistry.Api.DTOs;

public class TagGroupResponseDto
{
    public int TagGroupId { get; set; }

    // Danh sách các Tag đồng nghĩa trong nhóm.
    public List<string> Tags { get; set; } = new();
}
