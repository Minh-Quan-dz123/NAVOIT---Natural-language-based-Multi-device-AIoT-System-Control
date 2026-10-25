
using DeviceRegistry.Api.Data;
using DeviceRegistry.Api.DTOs;
using DeviceRegistry.Api.Models;

using Microsoft.EntityFrameworkCore;
using Npgsql;                           // một thư viện giúp ứng dụng .NET làm việc với PostgreSQL.
using System.Text.RegularExpressions;   // Import namespace chứa các class hỗ trợ Regular Expression (Regex), dùng để kiểm tra, tìm kiếm hoặc thay thế chuỗi theo một mẫu.

namespace DeviceRegistry.Api.Services;

public class MicrocontrollerService
{
    private readonly AppDbContext _context;

    // Các loại MCU cho phép đăng ký ở phiên bản này.
    // Loại không phải ESP32 cần firmware và MQTT protocol
    // tương thích mới có thể điều khiển thực sự.
    private static readonly HashSet<string> SupportedTypes = new()
    {
        "esp32",
        "esp8266",
        "arduino",
        "stm32"
    };

    // 1. Constructor - nhận AppDbContext từ DI.
    public MicrocontrollerService(AppDbContext context)
    {
        _context = context;
    }

    // 2. CHUẨN HÓA DỮ LIỆU

    // 2.1. Helper chuẩn hóa "type"
    private static string NormalizeType(string? type)
    {
        if (string.IsNullOrWhiteSpace(type)) throw new ArgumentException("Type không được để trống.");

        var value = type.Trim().ToLowerInvariant();

        if (!SupportedTypes.Contains(value)) throw new ArgumentException("Loại vi điều khiển chưa được hỗ trợ.");

        return value;
    }

    // 2.2. Helper chuẩn hóa "MAC"
    private static string NormalizeMac(string? macAddress)
    {
        if (string.IsNullOrWhiteSpace(macAddress)) throw new ArgumentException("MacAddress không được để trống.");

        // Chấp nhận:
        // D8:BF:C0:80:0F:A0
        // D8-BF-C0-80-0F-A0
        // D8BFC0800FA0
        // Lưu thống nhất ở dạng D8BFC0800FA0.
        var mac = macAddress.Trim().Replace(":", "").Replace("-", "").ToUpperInvariant();

        if (!Regex.IsMatch(mac, @"^[0-9A-F]{12}$"))throw new ArgumentException("MacAddress phải gồm 12 ký tự hexadecimal.");

        return mac;
    }

    // 3. LẤY TẤT CẢ MCU CỦA USER

    public async Task<List<MicrocontrollerResponseDto>> GetAllAsync(int userId)
    {
        return await _context.Microcontrollers
            .AsNoTracking()
            .Where(m => m.UserId == userId)
            .OrderByDescending(m => m.Id)
            .Select(m => new MicrocontrollerResponseDto
            {
                Id = m.Id,
                Type = m.Type,
                MacAddress = m.MacAddress,
                ConnectionStatus = m.ConnectionStatus,
                LastSeenAt = m.LastSeenAt,
                CreatedAt = m.CreatedAt,

                // EF Core chuyển Count thành truy vấn SQL.
                DeviceCount = m.Devices.Count()
            })
            .ToListAsync();
    }

    // 4. LẤY MỘT MCU THEO ID
    public async Task<MicrocontrollerResponseDto?> GetByIdAsync(int id, int userId)
    {
        return await _context.Microcontrollers
            .AsNoTracking()
            .Where(m => m.Id == id && m.UserId == userId)
            .Select(m => new MicrocontrollerResponseDto
            {
                Id = m.Id,
                Type = m.Type,
                MacAddress = m.MacAddress,
                ConnectionStatus = m.ConnectionStatus,
                LastSeenAt = m.LastSeenAt,
                CreatedAt = m.CreatedAt,
                DeviceCount = m.Devices.Count()
            })
            .FirstOrDefaultAsync();
    }

    // 5. USER TẠO MICROCONTROLLER

    public async Task<MicrocontrollerResponseDto> CreateAsync(int userId,CreateMicrocontrollerRequestDto dto)
    {
        var type = NormalizeType(dto.Type);
        var mac = NormalizeMac(dto.MacAddress);

        // Kiểm tra MCU đã được đăng ký trong hệ thống chưa.
        // Kiểm tra toàn database, không chỉ trong cùng User.
        var existed = await _context.Microcontrollers.AnyAsync(m => m.Type == type && m.MacAddress == mac);

        if (existed) throw new InvalidOperationException("Vi điều khiển này đã được đăng ký bởi 1 ai đó.");

        var microcontroller = new Microcontroller
        {
            UserId = userId,
            Type = type,
            MacAddress = mac,
            ConnectionStatus = "unknown",
            CreatedAt = DateTime.UtcNow
        };

        _context.Microcontrollers.Add(microcontroller);

        try
        {
            await _context.SaveChangesAsync();
        }
        catch (DbUpdateException ex) when ( // Chỉ bắt và xử lý lỗi DbUpdateException nếu nguyên nhân bên trong là lỗi vi phạm ràng buộc UNIQUE của PostgreSQL (lỗi trùng dữ liệu).
            ex.InnerException is PostgresException pg &&
            pg.SqlState == PostgresErrorCodes.UniqueViolation
        )
        {
            // Vẫn xử lý lỗi trùng tại database vì có thể
            // hai request đồng thời vượt qua bước AnyAsync.
            throw new InvalidOperationException("Vi điều khiển này đã được đăng ký.", ex);
        }

        return new MicrocontrollerResponseDto
        {
            Id = microcontroller.Id,
            Type = microcontroller.Type,
            MacAddress = microcontroller.MacAddress,
            ConnectionStatus = microcontroller.ConnectionStatus,
            LastSeenAt = microcontroller.LastSeenAt,
            CreatedAt = microcontroller.CreatedAt,
            DeviceCount = 0
        };
    }

    // 6. CẬP NHẬT MICROCONTROLLER
    // cập nhật loại vi điều khiển (Type) hoặc địa chỉ MAC (MacAddress) của một Microcontroller đã tồn tại.

    // Tuy nhiên, nó có 3 quy tắc quan trọng:
    // 1. Chỉ được sửa Microcontroller thuộc về userId hiện tại.
    // 2. Không được thay đổi Type hoặc MacAddress nếu Microcontroller đang quản lý các Device.
    // 3. Không được cập nhật thành cặp (Type, MacAddress) đã tồn tại trong Database.
    public async Task<MicrocontrollerResponseDto?> UpdateAsync(int id, int userId, UpdateMicrocontrollerRequestDto dto)
    {
        if (dto.Type == null && dto.MacAddress == null)throw new ArgumentException("Cần cung cấp ít nhất một trường để cập nhật.");

        var microcontroller = await _context.Microcontrollers
            .Include(m => m.Devices)
            .FirstOrDefaultAsync(m =>
                m.Id == id && m.UserId == userId
            );

        if (microcontroller == null) return null;

        var type = dto.Type == null? microcontroller.Type : NormalizeType(dto.Type);

        var mac = dto.MacAddress == null? microcontroller.MacAddress: NormalizeMac(dto.MacAddress);

        var changed = type != microcontroller.Type || mac != microcontroller.MacAddress;

        // Không cho đổi loại hoặc định danh phần cứng
        // khi MCU đang quản lý các Device.
        // Nếu cho đổi trực tiếp, các lệnh MQTT có thể
        // được định tuyến tới sai phần cứng.
        if (changed && microcontroller.Devices.Count > 0)throw new InvalidOperationException("Cần bỏ liên kết các Device trước khi đổi MCU.");

        if (changed)
        {
            var existed = await _context.Microcontrollers
                .AnyAsync(m =>
                    m.Id != id &&
                    m.Type == type &&
                    m.MacAddress == mac
                );

            if (existed) throw new InvalidOperationException("Định danh vi điều khiển đã tồn tại.");

            microcontroller.Type = type;
            microcontroller.MacAddress = mac;

            // Định danh thay đổi thì trạng thái kết nối cũ
            // không còn đáng tin cậy.
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
                throw new InvalidOperationException(
                    "Định danh vi điều khiển đã tồn tại.", ex
                );
            }
        }

        return new MicrocontrollerResponseDto
        {
            Id = microcontroller.Id,
            Type = microcontroller.Type,
            MacAddress = microcontroller.MacAddress,
            ConnectionStatus = microcontroller.ConnectionStatus,
            LastSeenAt = microcontroller.LastSeenAt,
            CreatedAt = microcontroller.CreatedAt,
            DeviceCount = microcontroller.Devices.Count
        };
    }

    // 7. XÓA MICROCONTROLLER
    // Hàm DeleteAsync() này dùng để xóa một Microcontroller khỏi Database, 
    // nhưng có một điểm đặc biệt: Các Device đang liên kết với Microcontroller 
    // đó sẽ không bị xóa, mà chỉ bị hủy liên kết.
    public async Task<bool> DeleteAsync(int id, int userId)
    {
        // Tìm Microcontroller cần xóa, chỉ tìm MCU thuộc userId này
        var microcontroller = await _context.Microcontrollers
            .FirstOrDefaultAsync(m =>
                m.Id == id && m.UserId == userId
            );

        if (microcontroller == null) return false;

        // Dùng transaction để bảo đảm thay đổi liên kết
        // và xóa Microcontroller được commit cùng nhau.
        // Nếu có lỗi trước khi Commit → Có thể Rollback.
        await using var transaction = await _context.Database.BeginTransactionAsync();

        // Lấy danh sách Device đang liên kết với MCU.
        //
        // Include Schedule để đồng thời lấy lịch
        // của từng Device (nếu tồn tại).
        var devices = await _context.Devices
            .Include(d => d.Schedule)
            .Where(d =>
                d.MicrocontrollerId == id &&
                d.UserId == userId
            )
            .ToListAsync();

        foreach (var device in devices)
        {
            // 1. Bỏ liên kết với Microcontroller.
            // Device vẫn được giữ trong database.
            device.MicrocontrollerId = null;

            // 2. Không thể điều khiển qua MCU đã bị xóa.
            device.SyncStatus = "unassigned";

            // 3. Trạng thái GPIO hiện tại không còn được xác minh.
            device.CurrentStatus = "UNKNOWN";
            device.StatusUpdatedAt = null;

            // 4. Xử lý Schedule liên quan.
            if (device.Schedule != null)
            {
                // Không tự xóa Schedule vì trên MCU thực tế
                // có thể vẫn còn lịch đang chạy.
                //
                // Đánh dấu unknown để hệ thống biết
                // cần đối chiếu hoặc xử lý lại.
                device.Schedule.SyncStatus = "unknown";
                device.Schedule.UpdatedAt = DateTime.UtcNow;
            }
        }

        _context.Microcontrollers.Remove(microcontroller);

        await _context.SaveChangesAsync();

        await transaction.CommitAsync();

        return true;
    }

    // 8. LẤY DEVICE THUỘC MICROCONTROLLER

    public async Task<List<MicrocontrollerDeviceDto>?> GetDevicesAsync(int id, int userId)
    {
        // Kiểm tra quyền sở hữu MCU trước.
        var exists = await _context.Microcontrollers.AnyAsync(m => m.Id == id && m.UserId == userId);

        if (!exists) return null;

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
