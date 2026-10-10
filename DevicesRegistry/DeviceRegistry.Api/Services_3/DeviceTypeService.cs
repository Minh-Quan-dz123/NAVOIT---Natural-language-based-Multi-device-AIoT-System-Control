using DeviceRegistry.Api.Data;
using DeviceRegistry.Api.Models;
using Microsoft.EntityFrameworkCore;

namespace DeviceRegistry.Api.Services;

public class DeviceTypeService
{
    private readonly AppDbContext _context;
    public DeviceTypeService(AppDbContext context)
    {
        _context = context;
    }

    // 1. Lấy tất cả loại thiết bị
    public async Task<List<DeviceType>> GetAllAsync()
    {
        return await _context.DeviceTypes
            .AsNoTracking()
            .ToListAsync();
    }

    // 2. Lấy loại thiết bị theo ID
    public async Task<DeviceType?> GetByIdAsync(int id)
    {
        //không theo dõi (tracking) đối tượng được truy vấn.
        return await _context.DeviceTypes.AsNoTracking().FirstOrDefaultAsync(dt => dt.Id == id);
    }

    // 3. Thêm loại thiết bị
    public async Task<DeviceType> CreateAsync(DeviceType deviceType)
    {
        deviceType.Id = 0;
        deviceType.TypeName = deviceType.TypeName.Trim();

        // 3.1. kiểm tra type name
        if (string.IsNullOrWhiteSpace(deviceType.TypeName))
        {
            throw new ArgumentException("Tên loại thiết bị không được để trống.");
        }

        // 3.2. Kiểm tra tên loại thiết bị đã tồn tại chưa
        bool exists = await _context.DeviceTypes.AnyAsync(dt => dt.TypeName == deviceType.TypeName);

        if (exists)
        {
            throw new ArgumentException("Tên loại thiết bị đã tồn tại.");
        }

        // 3.3. Kiểm tra AllowedStatuses có phải JSON hợp lệ không
        ValidateAllowedStatuses(deviceType.AllowedStatuses);
        _context.DeviceTypes.Add(deviceType);
        await _context.SaveChangesAsync();

        return deviceType;
    }

    // 4. Cập nhật loại thiết bị
    public async Task<DeviceType?> UpdateAsync(int id, DeviceType updatedDeviceType)
    {
        var deviceType = await _context.DeviceTypes.FirstOrDefaultAsync(dt => dt.Id == id);
        if (deviceType == null) return null;
        var typeName = updatedDeviceType.TypeName.Trim();

        if (string.IsNullOrWhiteSpace(typeName))
        {
            throw new ArgumentException("Tên loại thiết bị không được để trống.");
        }

        // kiểm tra xem có loại thiết bị nào khác cùng type name chưa
        bool exists = await _context.DeviceTypes.AnyAsync
        (dt => dt.Id != id &&dt.TypeName == typeName);

        if (exists)
        {
            throw new ArgumentException("Tên loại thiết bị đã tồn tại.");
        }

        ValidateAllowedStatuses(updatedDeviceType.AllowedStatuses);

        deviceType.TypeName = typeName;
        deviceType.AllowedStatuses = updatedDeviceType.AllowedStatuses;

        await _context.SaveChangesAsync();

        return deviceType;
    }

    // 5. Xóa loại thiết bị
    public async Task<bool> DeleteAsync(int id)
    {
        var deviceType = await _context.DeviceTypes
            .Include(dt => dt.Devices)
            .FirstOrDefaultAsync(dt => dt.Id == id);

        if (deviceType == null)
        {
            return false;
        }

        // Không cho xóa loại thiết bị đang được sử dụng
        if (deviceType.Devices.Any())
        {
            throw new InvalidOperationException(
                "Không thể xóa loại thiết bị đang được sử dụng.");
        }

        _context.DeviceTypes.Remove(deviceType);
        await _context.SaveChangesAsync();

        return true;
    }

    // 6. Kiểm tra AllowedStatuses
    private static void ValidateAllowedStatuses(string allowedStatuses)
    {
        // chứa các trạng thái không rỗng và không bị trùng lặp hay không.
        try
        {
            var statuses = System.Text.Json.JsonSerializer
                    .Deserialize<List<string>>(allowedStatuses);

            if (statuses == null || statuses.Any(string.IsNullOrWhiteSpace))
            {
                throw new ArgumentException("AllowedStatuses phải là JSON array chứa các trạng thái hợp lệ.");
            }

            if (statuses.Distinct(StringComparer.OrdinalIgnoreCase).Count()
                != statuses.Count)
            {
                throw new ArgumentException( "AllowedStatuses không được chứa trạng thái trùng lặp.");
            }
        }
        catch (System.Text.Json.JsonException)
        {
            throw new ArgumentException("AllowedStatuses phải là JSON hợp lệ, ví dụ [\"ON\", \"OFF\"].");
        }
    }
}