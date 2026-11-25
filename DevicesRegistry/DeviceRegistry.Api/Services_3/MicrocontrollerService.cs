
using System.Text.RegularExpressions;

using DeviceRegistry.Api.Data;
using DeviceRegistry.Api.DTOs;
using DeviceRegistry.Api.Models;

using Microsoft.EntityFrameworkCore;
using Npgsql;

namespace DeviceRegistry.Api.Services;

public class MicrocontrollerService
{
    private readonly AppDbContext _context;

    public MicrocontrollerService(AppDbContext context)
    {
        _context = context;
    }


    // 1. CHUẨN HÓA DỮ LIỆU
    private static string NormalizeType(string? type)
    {
        if (string.IsNullOrWhiteSpace(type))
        {
            throw new ArgumentException("Type không được để trống.");
        }

        string value = type.Trim().ToLowerInvariant();

        if (value.Length > 50 || !Regex.IsMatch(value, @"^[a-z0-9][a-z0-9_-]*$"))
        {
            throw new ArgumentException("Type không hợp lệ.");
        }

        return value;
    }

    private static string NormalizeMac(string? macAddress)
    {
        if (string.IsNullOrWhiteSpace(macAddress))
        {
            throw new ArgumentException("MacAddress không được để trống.");
        }

        string mac = macAddress.Trim().Replace(":", "").Replace("-", "").ToUpperInvariant();

        if (!Regex.IsMatch(mac, @"^[0-9A-F]{12}$"))
        {
            throw new ArgumentException("MacAddress phải gồm 12 ký tự hexadecimal.");
        }
        return mac;
    }

    // 2. KIỂM TRA LOẠI MCU
    private async Task ValidateTypeAsync(string type)
    {
        bool exists = await _context.MicrocontrollerTypes.AnyAsync(t => t.TypeName == type);
        if (!exists)
        {
            throw new ArgumentException( "Loại vi điều khiển chưa tồn tại trong danh mục.");
        }
    }

    // 3. KIỂM TRA ĐỊNH DANH TRÙNG
    private async Task<bool> IsDuplicateAsync(string type, string mac, int excludeId = 0)
    {
        return await _context.Microcontrollers
            .AnyAsync(m =>
                m.Type == type &&
                m.MacAddress == mac &&
                m.Id != excludeId
            );
    }

    // 4. QUERY DTO DÙNG CHUNG
    private IQueryable<MicrocontrollerResponseDto> ResponseQuery()
    {
        return _context.Microcontrollers
            .AsNoTracking()
            .Select(m => new MicrocontrollerResponseDto
            {
                Id = m.Id,
                Type = m.Type,
                MacAddress = m.MacAddress,

                UserId = m.UserId,

                // MCU chưa có chủ thì Username = null.
                OwnerUsername = m.User == null? null : m.User.Username,

                ConnectionStatus = m.ConnectionStatus,
                LastSeenAt = m.LastSeenAt,
                CreatedAt = m.CreatedAt,

                DeviceCount = m.Devices.Count()
            });
    }

    // 5. USER XEM MCU CỦA MK
    public async Task<List<MicrocontrollerResponseDto>> GetAllAsync(int userId)
    {
        return await ResponseQuery()
            .Where(m => m.UserId == userId)
            .OrderByDescending(m => m.Id)
            .ToListAsync();
    }

    public async Task<MicrocontrollerResponseDto?> GetByIdAsync(int id, int userId)
    {
        return await ResponseQuery().FirstOrDefaultAsync(m => m.Id == id && m.UserId == userId);
    }

    // 6. ADMIN - XEM TOÀN BỘ MCU
    public async Task<List<MicrocontrollerResponseDto>> GetAllForAdminAsync()
    {
        return await ResponseQuery()
            .OrderByDescending(m => m.Id)
            .ToListAsync();
    }

    public async Task<MicrocontrollerResponseDto?> GetForAdminByIdAsync(int id)
    {
        return await ResponseQuery().FirstOrDefaultAsync(m => m.Id == id);
    }

    // 7. ADMIN - TẠO MCU
    public async Task<MicrocontrollerResponseDto> CreateAsync(
        CreateMicrocontrollerRequestDto request)
    {
        string type = NormalizeType(request.Type);
        string mac = NormalizeMac(request.MacAddress);

        // Kiểm tra loại MCU.
        await ValidateTypeAsync(type);

        // Chỉ kiểm tra User khi Admin có chỉ định.
        if (request.UserId.HasValue)
        {
            if (request.UserId.Value <= 0)
            {
                throw new ArgumentException("UserId không hợp lệ.");
            }

            bool userExists = await _context.Users.AnyAsync(u => u.Id == request.UserId.Value);

            if (!userExists)
            {
                throw new ArgumentException("Không tìm thấy User được cấp MCU." );
            }
        }

        // Kiểm tra MCU đã tồn tại chưa.
        bool duplicate = await IsDuplicateAsync(type, mac);

        if (duplicate)
        {
            throw new InvalidOperationException("Vi điều khiển đã tồn tại.");
        }

        var microcontroller = new Microcontroller
        {
            Type = type,
            MacAddress = mac,

            // Có thể null.
            UserId = request.UserId,

            ConnectionStatus = "unknown",
            LastSeenAt = null,
            CreatedAt = DateTime.UtcNow
        };

        _context.Microcontrollers.Add(microcontroller);

        try
        {
            await _context.SaveChangesAsync();
        }
        catch (DbUpdateException ex) when (
            ex.InnerException is PostgresException pg &&
            pg.SqlState == PostgresErrorCodes.UniqueViolation
        )
        {
            throw new InvalidOperationException("Vi điều khiển đã tồn tại.", ex);
        }

        return (await GetForAdminByIdAsync(microcontroller.Id))!;
    }

    // 8. ADMIN - CẬP NHẬT MCU
    public async Task<MicrocontrollerResponseDto?> UpdateAsync(int id, UpdateMicrocontrollerRequestDto request)
    {
        if (request.Type == null && request.MacAddress == null)
        {
            throw new ArgumentException("Cần cung cấp Type hoặc MacAddress.");
        }

        var microcontroller = await _context.Microcontrollers.FirstOrDefaultAsync(m => m.Id == id);

        if (microcontroller == null) return null;

        string type = request.Type == null ? microcontroller.Type : NormalizeType(request.Type);
        string mac = request.MacAddress == null ? microcontroller.MacAddress : NormalizeMac(request.MacAddress);

        bool changed = (type != microcontroller.Type) || (mac != microcontroller.MacAddress);

        if (!changed) return await GetForAdminByIdAsync(id);

        // Không cho đổi định danh khi đang có Device.
        bool hasDevices = await _context.Devices.AnyAsync(d => d.MicrocontrollerId == id);

        if (hasDevices)
        {
            throw new InvalidOperationException("Không thể đổi Type hoặc MAC khi MCU đang liên kết Device.");
        }

        if (type != microcontroller.Type) await ValidateTypeAsync(type);

        bool duplicate = await IsDuplicateAsync(type, mac, id);

        if (duplicate) throw new InvalidOperationException("Định danh MCU đã tồn tại." );

        microcontroller.Type = type;
        microcontroller.MacAddress = mac;

        microcontroller.ConnectionStatus = "unknown";
        microcontroller.LastSeenAt = null;

        try
        {
            await _context.SaveChangesAsync();
        }
        catch (DbUpdateException ex) when (
            ex.InnerException is PostgresException pg &&
            pg.SqlState == PostgresErrorCodes.UniqueViolation
        )
        {
            throw new InvalidOperationException("Định danh MCU đã tồn tại.", ex);
        }

        return await GetForAdminByIdAsync(id);
    }

    // 9. ADMIN - CẤP / CHUYỂN QUYỀN MCU
    public async Task<MicrocontrollerResponseDto?> TransferAsync(int id, int newUserId)
    {
        if (newUserId <= 0)
        {
            throw new ArgumentException("UserId không hợp lệ.");
        }

        var microcontroller = await _context.Microcontrollers.FirstOrDefaultAsync(m => m.Id == id);

        if (microcontroller == null) return null;

        bool userExists = await _context.Users.AnyAsync(u => u.Id == newUserId);

        if (!userExists)
        {
            throw new ArgumentException("Không tìm thấy User nhận quyền sử dụng MCU.");
        }

        // Nếu đã thuộc User này thì giữ nguyên.
        if (microcontroller.UserId == newUserId)
        {
            return await GetForAdminByIdAsync(id);
        }

        // Không chuyển MCU khi còn Device liên kết.
        bool hasDevices = await _context.Devices.AnyAsync(d => d.MicrocontrollerId == id);

        if (hasDevices)
        {
            throw new InvalidOperationException("Cần bỏ liên kết Device trước khi chuyển quyền MCU.");
        }

        // Nếu UserId đang null: đây là cấp quyền lần đầu.
        // Nếu đã có UserId: đây là chuyển nhượng.
        microcontroller.UserId = newUserId;

        await _context.SaveChangesAsync();

        return await GetForAdminByIdAsync(id);
    }

    // 10. ADMIN - XÓA MCU
    public async Task<bool> DeleteAsync(int id)
    {
        var microcontroller = await _context.Microcontrollers.FirstOrDefaultAsync(m => m.Id == id);

        if (microcontroller == null) return false;

        bool hasDevices = await _context.Devices.AnyAsync(d => d.MicrocontrollerId == id);

        if (hasDevices)
        {
            throw new InvalidOperationException("Không thể xóa MCU đang liên kết Device." );
        }

        _context.Microcontrollers.Remove(microcontroller);

        await _context.SaveChangesAsync();

        return true;
    }

    // 11. USER XEM DEVICE THUỘC MCU
    public async Task<List<MicrocontrollerDeviceDto>?> GetDevicesAsync(int id, int userId)
    {
        // Chỉ chủ sở hữu được xem.
        bool isOwner = await _context.Microcontrollers
            .AnyAsync(m =>
                m.Id == id &&
                m.UserId == userId
            );

        if (!isOwner) return null;

        return await _context.Devices
            .AsNoTracking()
            .Where(d =>
                d.MicrocontrollerId == id &&
                d.UserId == userId
            )
            .OrderBy(d => d.Gpio)
            .Select(d => new MicrocontrollerDeviceDto
            {
                Id = d.Id,
                DeviceName = d.DeviceName,
                Gpio = d.Gpio,
                DeviceTypeId = d.DeviceTypeId,
                CurrentStatus = d.CurrentStatus,
                SyncStatus = d.SyncStatus
            })
            .ToListAsync();
    }
}
