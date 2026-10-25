
using DeviceRegistry.Api.Data;
using DeviceRegistry.Api.DTOs;
using DeviceRegistry.Api.Models;

using Microsoft.EntityFrameworkCore;
using Npgsql;

using System.Text.Json;
using System.Text.RegularExpressions;


namespace DeviceRegistry.Api.Services;

public class DeviceTypeService
{
    // 1
    private readonly AppDbContext _context;
    public DeviceTypeService(AppDbContext context)
    {
        _context = context;
    }

    // 2. CHUẨN HÓA TÊN LOẠI THIẾT BỊ
    private static string NormalizeTypeName(string? typeName)
    {
        if (string.IsNullOrWhiteSpace(typeName)) throw new ArgumentException("TypeName không được để trống.");

        // Ví dụ: " LIGHT " -> "light".
        var name = typeName.Trim().ToLowerInvariant();

        // TypeName là mã dùng trong hệ thống và giao thức.
        // Chỉ chấp nhận chữ thường, số và dấu gạch dưới.
        //
        // Ví dụ hợp lệ:
        // light, fan, door, ceiling_fan.
        if (!Regex.IsMatch(name, @"^[a-z][a-z0-9_]{0,49}$"))
            throw new ArgumentException(
                "TypeName chỉ được chứa chữ cái không dấu, " +
                "chữ số, dấu gạch dưới và tối đa 50 ký tự."
            );

        return name;
    }

    // 3. KIỂM TRA ALLOWED STATUSES
    private static string NormalizeAllowedStatuses(List<string>? statuses)
    {
        // Danh sách trạng thái phải có ít nhất một phần tử.
        if (statuses == null || statuses.Count == 0)
            throw new ArgumentException("AllowedStatuses không được rỗng.");

        var normalized = new List<string>();

        foreach (var status in statuses)
        {
            if (string.IsNullOrWhiteSpace(status))
                throw new ArgumentException("AllowedStatuses không được chứa trạng thái rỗng.");

            // Ví dụ: " on " -> "ON".
            var value = status.Trim().ToUpperInvariant();

            if (value.Length > 32 ||!Regex.IsMatch(value, @"^[A-Z][A-Z0-9_]*$"))
            {
                throw new ArgumentException(
                    "Trạng thái phải là mã không dấu, " +
                    "bắt đầu bằng chữ cái và tối đa 32 ký tự."
                );
            }

            // Sau khi chuyển thành chữ hoa,
            // "on" và "ON" được coi là trùng nhau.
            if (normalized.Contains(value))
                throw new ArgumentException($"Trạng thái '{value}' bị trùng.");

            normalized.Add(value);
        }

        // Model DeviceType hiện lưu AllowedStatuses
        // bằng kiểu string.
        //
        // Vì vậy chuyển List<string> thành JSON string
        // trước khi lưu database.
        //
        // ["ON", "OFF"] -> "[\"ON\",\"OFF\"]"
        return JsonSerializer.Serialize(normalized);
    }

    // 4. CHUYỂN DỮ LIỆU DATABASE SANG RESPONSE DTO
    private static DeviceTypeResponseDto ToResponseDto(
        int id,
        string typeName,
        string allowedStatuses,
        int deviceCount
    )
    {
        // Chuyển chuỗi JSON trong database
        // trở lại thành List<string> để trả về API.
        var statuses =JsonSerializer.Deserialize<List<string>>(allowedStatuses)?? new List<string>();

        return new DeviceTypeResponseDto
        {
            Id = id,
            TypeName = typeName,
            AllowedStatuses = statuses,
            DeviceCount = deviceCount
        };
    }


    // 5. LẤY TẤT CẢ DEVICE TYPE
    public async Task<List<DeviceTypeResponseDto>> GetAllAsync()
    {
        // Lấy dữ liệu từ database.
        //
        // Chưa deserialize JSON trong IQueryable
        // vì phần đó không được thực thi bằng SQL.
        var types = await _context.DeviceTypes
            .AsNoTracking()
            .OrderBy(dt => dt.Id)
            .Select(dt => new
            {
                dt.Id,
                dt.TypeName,
                dt.AllowedStatuses,

                // Đếm số Device đang sử dụng DeviceType.
                DeviceCount = dt.Devices.Count()
            })
            .ToListAsync();

        // Sau khi có dữ liệu trong RAM,
        // chuyển AllowedStatuses thành List<string>.
        return types.Select(dt => ToResponseDto(
            dt.Id,
            dt.TypeName,
            dt.AllowedStatuses,
            dt.DeviceCount
        )).ToList();
    }

    // 6. LẤY DEVICE TYPE THEO ID
    public async Task<DeviceTypeResponseDto?> GetByIdAsync(int id)
    {
        var type = await _context.DeviceTypes
            .AsNoTracking()
            .Where(dt => dt.Id == id)
            .Select(dt => new
            {
                dt.Id,
                dt.TypeName,
                dt.AllowedStatuses,
                DeviceCount = dt.Devices.Count()
            })
            .FirstOrDefaultAsync();

        if (type == null) return null;

        return ToResponseDto(
            type.Id,
            type.TypeName,
            type.AllowedStatuses,
            type.DeviceCount
        );
    }

    // 7. TẠO DEVICE TYPE
    public async Task<DeviceTypeResponseDto> CreateAsync(
        CreateDeviceTypeRequestDto dto
    )
    {
        // 7.1. Chuẩn hóa và kiểm tra dữ liệu.
        var typeName = NormalizeTypeName(dto.TypeName);

        var allowedStatuses = NormalizeAllowedStatuses(dto.AllowedStatuses);

        // 7.2. Kiểm tra tên đã tồn tại chưa.
        // ToLower() ở đây được EF Core dịch sang SQL.
        var exists = await _context.DeviceTypes.AnyAsync(dt => dt.TypeName.ToLower() == typeName);

        if (exists) throw new InvalidOperationException("Tên loại thiết bị đã tồn tại.");

        // 7.3. Tạo Entity.
        var deviceType = new DeviceType
        {
            TypeName = typeName,
            AllowedStatuses = allowedStatuses
        };

        // 7.4. Lưu database.
        _context.DeviceTypes.Add(deviceType);

        try
        {
            await _context.SaveChangesAsync();
        }
        catch (DbUpdateException ex) when (
            ex.InnerException is PostgresException pg &&
            pg.SqlState == PostgresErrorCodes.UniqueViolation
        )
        {
            // Bắt trường hợp vi phạm unique constraint
            // nếu database đã được cấu hình constraint.
            throw new InvalidOperationException("Tên loại thiết bị đã tồn tại.", ex);
        }

        return ToResponseDto(
            deviceType.Id,
            deviceType.TypeName,
            deviceType.AllowedStatuses,
            0
        );
    }

    // 8. CẬP NHẬT DEVICE TYPE
    public async Task<DeviceTypeResponseDto?> UpdateAsync(int id, UpdateDeviceTypeRequestDto dto)
    {
        // 8.1. Kiểm tra request có nội dung hay không.
        if (dto.TypeName == null && dto.AllowedStatuses == null)
            throw new ArgumentException(
                "Không có thông tin cần cập nhật."
            );

        // 8.2. Tìm loại thiết bị.
        var deviceType = await _context.DeviceTypes
            .FirstOrDefaultAsync(dt => dt.Id == id);

        if (deviceType == null)
            return null;

        // 8.3. Nếu không gửi TypeName, giữ tên cũ.
        var newName = dto.TypeName == null
            ? deviceType.TypeName
            : NormalizeTypeName(dto.TypeName);

        // 8.4. Nếu không gửi AllowedStatuses, giữ danh sách cũ.
        var newStatuses = dto.AllowedStatuses == null
            ? deviceType.AllowedStatuses
            : NormalizeAllowedStatuses(dto.AllowedStatuses);

        // 8.5. Nếu đổi TypeName, phải kiểm tra
        // có Device đang sử dụng DeviceType này không.
        if (newName != deviceType.TypeName)
        {
            var isUsed = await _context.Devices
                .AnyAsync(d => d.DeviceTypeId == id);

            if (isUsed)
                throw new InvalidOperationException(
                    "Không thể đổi TypeName khi đã có Device sử dụng."
                );

            // Kiểm tra tên mới đã được sử dụng chưa.
            var nameExists = await _context.DeviceTypes
                .AnyAsync(dt =>
                    dt.Id != id &&
                    dt.TypeName.ToLower() == newName
                );

            if (nameExists)
                throw new InvalidOperationException(
                    "Tên loại thiết bị đã tồn tại."
                );
        }

        // 8.6. Cập nhật Entity.
        deviceType.TypeName = newName;
        deviceType.AllowedStatuses = newStatuses;

        // 8.7. Lưu thay đổi.
        try
        {
            await _context.SaveChangesAsync();
        }
        catch (DbUpdateException ex) when (
            ex.InnerException is PostgresException pg &&
            pg.SqlState == PostgresErrorCodes.UniqueViolation
        )
        {
            throw new InvalidOperationException("Tên loại thiết bị đã tồn tại.", ex);
        }

        var deviceCount = await _context.Devices.CountAsync(d => d.DeviceTypeId == id);

        return ToResponseDto(
            deviceType.Id,
            deviceType.TypeName,
            deviceType.AllowedStatuses,
            deviceCount
        );
    }

    // 9. XÓA DEVICE TYPE
    public async Task<bool> DeleteAsync(int id)
    {
        var deviceType = await _context.DeviceTypes
            .FirstOrDefaultAsync(dt => dt.Id == id);

        if (deviceType == null)
            return false;

        // Kiểm tra có Device nào đang tham chiếu
        // đến DeviceType này không.
        var isUsed = await _context.Devices.AnyAsync(d => d.DeviceTypeId == id);

        if (isUsed) throw new InvalidOperationException("Không thể xóa DeviceType đang được sử dụng.");

        _context.DeviceTypes.Remove(deviceType);

        try
        {
            await _context.SaveChangesAsync();
        }
        catch (DbUpdateException ex) when (
            ex.InnerException is PostgresException pg &&
            pg.SqlState == PostgresErrorCodes.ForeignKeyViolation
        )
        {
            // Bắt tình huống một Device mới được tạo
            // tham chiếu tới loại này ngay trước khi xóa.
            throw new InvalidOperationException(
                "Không thể xóa DeviceType đang được sử dụng.", ex
            );
        }

        return true;
    }

    
}