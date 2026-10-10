using DeviceRegistry.Api.DTOs;
namespace DeviceRegistry.Api.Services;

public class ManageTagsService
{
    // TODO:
    // Inject AppDbContext
    // 1. tạo tag mới
    public async Task<object?> CreateTag(CreateTagRequestDto request)
    {
        // từ user_id->device_id: tạo tag mới với tag group tới trở vào device_id
        // nếu tag đã tồn tại rồi thì thôi
        
        return null;
    }
    public async Task<object?> UpdateAlias(UpdateAliasRequestDto request)
    {
        // 1. từ old tag  lấy ra group tag id
        // 2. kiểm tra có new tag nào đã tồn tại ko, ko thì thêm tag mới và tạo liên kết tới cùng 1 tag group của old tag
        return null;
    }
}