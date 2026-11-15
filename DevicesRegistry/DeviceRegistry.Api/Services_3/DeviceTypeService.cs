
using System.Text.Json;
using System.Text.RegularExpressions;

using DeviceRegistry.Api.Data;
using DeviceRegistry.Api.DTOs;
using DeviceRegistry.Api.Models;

using Microsoft.EntityFrameworkCore;
using Npgsql;

namespace DeviceRegistry.Api.Services;

public class DeviceTypeService
{
    private readonly AppDbContext _context;

    public DeviceTypeService(AppDbContext context)
    {
        _context = context;
    }

    // 1. CHUẨN HÓA TÊN LOẠI
    private static string NormalizeTypeName(string? typeName)
    {
        if (string.IsNullOrWhiteSpace(typeName))
        {
            throw new ArgumentException("Tên loại thiết bị không được để trống.");
        }

        string name = typeName.Trim().ToLowerInvariant();
        if (!Regex.IsMatch(name, @"^[a-z][a-z0-9_]{0,49}$"))
        {
            throw new ArgumentException(
                "Tên loại phải bắt đầu bằng chữ cái, " +
                "chỉ chứa chữ thường, số, _ và tối đa 50 ký tự."
            );
        }

        return name;
    }

    // 2. CHUẨN HÓA TRẠNG THÁI
    private static string NormalizeAllowedStatuses( List<string>? statuses)
    {
        if (statuses == null || statuses.Count == 0)
        {
            throw new ArgumentException( "Phải có ít nhất một trạng thái.");
        }

        var normalized = new List<string>();
        foreach (string? status in statuses)
        {
            if (string.IsNullOrWhiteSpace(status))
            {
                throw new ArgumentException("Danh sách không được chứa trạng thái rỗng.");
            }

            string value = status.Trim().ToUpperInvariant();
            if (value.Length > 32 || !Regex.IsMatch(value, @"^[A-Z][A-Z0-9_]*$"))
            {
                throw new ArgumentException(
                    "Trạng thái phải bắt đầu bằng chữ cái, " +
                    "chỉ chứa chữ hoa, số, _ và tối đa 32 ký tự."
                );
            }

            if (normalized.Contains(value))
            {
                throw new ArgumentException($"Trạng thái '{value}' bị trùng.");
            }

            normalized.Add(value);
        }

        // Model lưu dưới dạng string JSON.
        return JsonSerializer.Serialize(normalized);
    }

    // 3. CHUYỂN MODEL SANG RESPONSE DTO
    private static DeviceTypeResponseDto ToDto(
        int id,
        string typeName,
        string allowedStatuses,
        int deviceCount)
    {
        return new DeviceTypeResponseDto
        {
            Id = id,
            TypeName = typeName,
            AllowedStatuses = JsonSerializer.Deserialize<List<string>>(allowedStatuses) ?? new List<string>(),
            DeviceCount = deviceCount
        };
    }

    // 4. GET ALL
    public async Task<List<DeviceTypeResponseDto>> GetAllAsync()
    {
        var types = await _context.DeviceTypes
            .AsNoTracking()
            .OrderBy(t => t.Id)
            .Select(t => new
            {
                t.Id,
                t.TypeName,
                t.AllowedStatuses,
                DeviceCount = t.Devices.Count()
            })
            .ToListAsync();

        return types.Select(t => ToDto(
            t.Id,
            t.TypeName,
            t.AllowedStatuses,
            t.DeviceCount
        )).ToList();
    }

    // 5. GET BY ID
    public async Task<DeviceTypeResponseDto?> GetByIdAsync(int id)
    {
        var type = await _context.DeviceTypes
            .AsNoTracking()
            .Where(t => t.Id == id)
            .Select(t => new
            {
                t.Id,
                t.TypeName,
                t.AllowedStatuses,
                DeviceCount = t.Devices.Count()
            })
            .FirstOrDefaultAsync();

        if (type == null) return null;

        return ToDto(
            type.Id,
            type.TypeName,
            type.AllowedStatuses,
            type.DeviceCount
        );
    }

    // 6. CREATE
    public async Task<DeviceTypeResponseDto> CreateAsync(CreateDeviceTypeRequestDto request)
    {
        string name = NormalizeTypeName(request.TypeName);
        string statuses = NormalizeAllowedStatuses(request.AllowedStatuses);

        bool exists = await _context.DeviceTypes.AnyAsync(t => t.TypeName.ToLower() == name);

        if (exists)
        {
            throw new InvalidOperationException("Loại thiết bị đã tồn tại.");
        }

        var type = new DeviceType
        {
            TypeName = name,
            AllowedStatuses = statuses
        };

        _context.DeviceTypes.Add(type);

        try
        {
            await _context.SaveChangesAsync();
        }
        catch (DbUpdateException ex) when (
            ex.InnerException is PostgresException pg &&
            pg.SqlState == PostgresErrorCodes.UniqueViolation
        )
        {
            throw new InvalidOperationException("Loại thiết bị đã tồn tại.", ex);
        }

        return ToDto(
            type.Id,
            type.TypeName,
            type.AllowedStatuses,
            0
        );
    }

    // 7. UPDATE
    public async Task<DeviceTypeResponseDto?> UpdateAsync(
        int id,
        UpdateDeviceTypeRequestDto request)
    {
        if (request.TypeName == null &&
            request.AllowedStatuses == null)
        {
            throw new ArgumentException("Không có thông tin cần cập nhật.");
        }

        var type = await _context.DeviceTypes.FirstOrDefaultAsync(t => t.Id == id);

        if (type == null) return null;

        // Không gửi trường nào thì giữ dữ liệu cũ.
        string newName = request.TypeName == null
            ? type.TypeName
            : NormalizeTypeName(request.TypeName);

        string newStatuses = request.AllowedStatuses == null
            ? type.AllowedStatuses
            : NormalizeAllowedStatuses(request.AllowedStatuses);

        bool changed = (newName != type.TypeName) || (newStatuses != type.AllowedStatuses);

        if (!changed) return await GetByIdAsync(id);

        // Không sửa cấu hình loại đang có Device sử dụng.
        bool inUse = await _context.Devices.AnyAsync(d => d.DeviceTypeId == id);

        if (inUse)
        {
            throw new InvalidOperationException("Không thể sửa loại thiết bị đang được Device sử dụng.");
        }

        // Kiểm tra tên mới có bị trùng không.
        if (newName != type.TypeName)
        {
            bool duplicate = await _context.DeviceTypes
                .AnyAsync(t =>
                    t.Id != id &&
                    t.TypeName.ToLower() == newName
                );

            if (duplicate)
            {
                throw new InvalidOperationException("Tên loại thiết bị đã tồn tại.");
            }
        }

        type.TypeName = newName;
        type.AllowedStatuses = newStatuses;

        try
        {
            await _context.SaveChangesAsync();
        }
        catch (DbUpdateException ex) when (
            ex.InnerException is PostgresException pg &&
            pg.SqlState == PostgresErrorCodes.UniqueViolation
        )
        {
            throw new InvalidOperationException("Tên loại thiết bị đã tồn tại.");
        }

        return await GetByIdAsync(id);
    }

    // 8. DELETE
    public async Task<bool> DeleteAsync(int id)
    {
        var type = await _context.DeviceTypes.FirstOrDefaultAsync(t => t.Id == id);
        if (type == null) return false;
        bool inUse = await _context.Devices.AnyAsync(d => d.DeviceTypeId == id);

        if (inUse)
        {
            throw new InvalidOperationException("Không thể xóa loại thiết bị đang được sử dụng.");
        }

        _context.DeviceTypes.Remove(type);

        try
        {
            await _context.SaveChangesAsync();
        }
        catch (DbUpdateException ex) when (
            ex.InnerException is PostgresException pg &&
            pg.SqlState == PostgresErrorCodes.ForeignKeyViolation
        )
        {
            throw new InvalidOperationException( "Không thể xóa loại đang được Device sử dụng.", ex);
        }

        return true;
    }
}
