
using System.Text.RegularExpressions;

using DeviceRegistry.Api.Data;
using DeviceRegistry.Api.DTOs;
using DeviceRegistry.Api.Models;

using Microsoft.EntityFrameworkCore;

using Npgsql;

namespace DeviceRegistry.Api.Services;

public class MicrocontrollerTypeService
{
    private readonly AppDbContext _context;

    public MicrocontrollerTypeService(AppDbContext context)
    {
        _context = context;
    }

    // 1. Chuẩn hóa tên loại
    private static string NormalizeTypeName(string? typeName)
    {
        if (string.IsNullOrWhiteSpace(typeName))
        {
            throw new ArgumentException("Tên loại vi điều khiển không được để trống.");
        }

        string name = typeName.Trim().ToLowerInvariant();
        if (name.Length > 50)
        {
            throw new ArgumentException( "Tên loại không được vượt quá 50 ký tự." );
        }

        // Chỉ cho phép chữ thường, số, dấu _ và dấu -
        if (!Regex.IsMatch(name, @"^[a-z0-9][a-z0-9_-]*$"))
        {
            throw new ArgumentException("Tên loại chỉ được chứa chữ cái không dấu, số, _ hoặc -.");
        }

        return name;
    }


    // 2. Chuyển Model sang DTO
    private static MicrocontrollerTypeResponseDto ToDto(MicrocontrollerType model)
    {
        return new MicrocontrollerTypeResponseDto
        {
            Id = model.Id,
            TypeName = model.TypeName
        };
    }

    // 3. Lấy tất cả loại MCU
    public async Task<List<MicrocontrollerTypeResponseDto>> GetAllAsync()
    {
        return await _context.MicrocontrollerTypes
            .AsNoTracking()
            .OrderBy(t => t.TypeName)
            .Select(t => new MicrocontrollerTypeResponseDto
            {
                Id = t.Id,
                TypeName = t.TypeName
            })
            .ToListAsync();
    }

    // 4. Lấy loại MCU theo ID
    public async Task<MicrocontrollerTypeResponseDto?> GetByIdAsync(int id)
    {
        return await _context.MicrocontrollerTypes
            .AsNoTracking()
            .Where(t => t.Id == id)
            .Select(t => new MicrocontrollerTypeResponseDto
            {
                Id = t.Id,
                TypeName = t.TypeName
            })
            .FirstOrDefaultAsync();
    }


    // 5. Kiểm tra tên có bị trùng
    private async Task<bool> TypeNameExistsAsync( string typeName, int excludeId = 0)
    {
        return await _context.MicrocontrollerTypes
            .AnyAsync(t =>
                t.TypeName == typeName &&
                t.Id != excludeId
            );
    }

    // 6. Kiểm tra loại đang được MCU sử dụng
    private async Task<bool> IsTypeInUseAsync(string typeName)
    {
        return await _context.Microcontrollers
            .AnyAsync(m =>m.Type.Trim().ToLower() == typeName);
    }

    // 7. Tạo loại MCU
    public async Task<MicrocontrollerTypeResponseDto> CreateAsync(
        CreateMicrocontrollerTypeRequestDto request)
    {
        string typeName = NormalizeTypeName(request.TypeName);

        bool exists = await TypeNameExistsAsync(typeName);

        if (exists)
        {
            throw new InvalidOperationException( "Loại vi điều khiển đã tồn tại." );
        }

        var model = new MicrocontrollerType
        {
            TypeName = typeName
        };

        _context.MicrocontrollerTypes.Add(model);

        try
        {
            await _context.SaveChangesAsync();
        }
        catch (DbUpdateException ex) when (
            ex.InnerException is PostgresException pg &&
            pg.SqlState == PostgresErrorCodes.UniqueViolation
        )
        {
            throw new InvalidOperationException( "Loại vi điều khiển đã tồn tại.", ex);
        }

        return ToDto(model);
    }

  
    // 8. Cập nhật loại MCU

    public async Task<MicrocontrollerTypeResponseDto?> UpdateAsync(
        int id,
        UpdateMicrocontrollerTypeRequestDto request)
    {
        string newName = NormalizeTypeName(request.TypeName);

        var model = await _context.MicrocontrollerTypes
            .FirstOrDefaultAsync(t => t.Id == id);

        if (model == null) return null;


        // Không cần ghi database nếu không thay đổi.
        if (model.TypeName == newName) return ToDto(model);

        // Không cho đổi tên loại đang được sử dụng.
        bool inUse = await IsTypeInUseAsync(model.TypeName);

        if (inUse)
        {
            throw new InvalidOperationException("Không thể đổi tên loại đang được vi điều khiển sử dụng." );
        }

        // Kiểm tra tên mới có trùng loại khác không.
        bool exists = await TypeNameExistsAsync(newName, id);

        if (exists)
        {
            throw new InvalidOperationException("Tên loại vi điều khiển đã tồn tại.");
        }

        model.TypeName = newName;

        try
        {
            await _context.SaveChangesAsync();
        }
        catch (DbUpdateException ex) when (
            ex.InnerException is PostgresException pg &&
            pg.SqlState == PostgresErrorCodes.UniqueViolation
        )
        {
            throw new InvalidOperationException( "Tên loại vi điều khiển đã tồn tại.", ex);
        }

        return ToDto(model);
    }


    // 9. Xóa loại MCU
    public async Task<bool> DeleteAsync(int id)
    {
        var model = await _context.MicrocontrollerTypes.FirstOrDefaultAsync(t => t.Id == id);

        if (model == null) return false;
        bool inUse = await IsTypeInUseAsync(model.TypeName);

        if (inUse)
        {
            throw new InvalidOperationException( "Không thể xóa loại đang được vi điều khiển sử dụng.");
        }

        _context.MicrocontrollerTypes.Remove(model);
        await _context.SaveChangesAsync();
        return true;
    }
}
