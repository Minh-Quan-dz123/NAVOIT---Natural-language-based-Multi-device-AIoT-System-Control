using DeviceRegistry.Api.DTOs;
using DeviceRegistry.Api.Data;
using DeviceRegistry.Api.Models;
using Microsoft.EntityFrameworkCore;


namespace DeviceRegistry.Api.Services;
public class DeviceService
{
    // TODO: Inject AppDbContext 
    private readonly AppDbContext _context;
    public DeviceService(AppDbContext context)
    {
        _context = context;
    }

    // 1. Async Task để làm nhiệm vụ tìm devices dựa trên các tags
    public async Task<object?> ResolveAsync(DeviceResolutionRequestDto request)
    {
        // 1. Lấy ra các Tags từ input 
        // 2. Từ từ Tag, tìm TagGroup trong user_id, ta được list các TagGroup
        // 3. mỗi TagGroup => list[D1, D2, D3]
        // 4. Tạo Map[D1, count] => duyệt theo TagGroup để Map[D_i]++
        // 5. tìm được Map[D_i] có count lớn nhất (có thể có nhiều D_i có cùng count lớn nhất)
        // 6. sau đó trả về DeviceResolutionReponse kể cả rỗng
    

        return null;
    }

    // 2.1. get all theo user
    public async Task<List<Device>> GetAllByUserIdAsync(int userId)
    {
        return await _context.Devices
            .Where(d => d.UserId == userId)
            .Include(d => d.DeviceType)
            .Include(d => d.Microcontroller)
            .Include(d => d.Schedule)
            .Include(d => d.DeviceTagGroups)
                .ThenInclude(dtg => dtg.TagGroup)
            .ToListAsync();
    }

    // 2.2. Lấy device theo deviceID
    public async Task<Device?> GetByIdAsync(int id, int userId)
    {
        return await _context.Devices
            .Include(d => d.DeviceType)
            .Include(d => d.Microcontroller)
            .Include(d => d.Schedule)
            .Include(d => d.DeviceTagGroups)
                .ThenInclude(dtg => dtg.TagGroup)
            .FirstOrDefaultAsync(d =>
                d.Id == id && d.UserId == userId);
    }

    // 3. thêm device cho user
    public async Task<Device> CreateAsync(Device device, int userId)
    {
        device.Id = 0;
        device.UserId = userId;
        device.CreateAt = DateTime.UtcNow;

        _context.Devices.Add(device);
        await _context.SaveChangesAsync();

        return device;
    }

    // 4. cập nhật device =========TODO ==================
    public async Task<Device?> UpdateAsync(int id, int userId, Device updatedDevice)
    {
        var device = await _context.Devices.FirstOrDefaultAsync(d =>d.Id == id && d.UserId == userId);

        if (device == null) return null;

        device.MicrocontrollerId = updatedDevice.MicrocontrollerId;
        device.DeviceName = updatedDevice.DeviceName;
        device.DeviceTypeId = updatedDevice.DeviceTypeId;
        device.Gpio = updatedDevice.Gpio;
        device.CurrentStatus = updatedDevice.CurrentStatus;

        await _context.SaveChangesAsync();

        return device;
    }

    // 5. Xóa device
    public async Task<bool> DeleteAsync(int id, int userId)
    {
        var device = await _context.Devices.FirstOrDefaultAsync(d =>d.Id == id && d.UserId == userId);

        if (device == null) return false;

        _context.Devices.Remove(device);
        await _context.SaveChangesAsync();

        return true;
    }

    // 6. Cập nhật trạng thái hiện tại của device =====TODO===========
    public async Task<Device?> UpdateStatusAsync(int id, int userId, string status)
    {
        var device = await _context.Devices
            .Include(d => d.DeviceType)
            .FirstOrDefaultAsync(d =>
                d.Id == id && d.UserId == userId);

        if (device == null) return null;

        // Kiểm tra trạng thái có hợp lệ với loại thiết bị không
        var allowedStatuses = System.Text.Json.JsonSerializer
            .Deserialize<List<string>>(device.DeviceType.AllowedStatuses)?? new List<string>();

        if (!allowedStatuses.Contains(status, StringComparer.OrdinalIgnoreCase))
        {
            throw new ArgumentException(
                $"Trạng thái '{status}' không hợp lệ " +
                $"với thiết bị loại '{device.DeviceType.TypeName}'.");
        }

        device.CurrentStatus = status;

        await _context.SaveChangesAsync();

        return device;
    }


}