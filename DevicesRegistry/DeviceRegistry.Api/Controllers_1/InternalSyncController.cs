
using DeviceRegistry.Api.Data;
using DeviceRegistry.Api.DTOs;

using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;

using Npgsql;

namespace DeviceRegistry.Api.Controllers;

[ApiController]
[Authorize(Policy = "NlpServerOnly")]
[Route("api/internal")]
public class InternalSyncController : ControllerBase
{
    private readonly AppDbContext _context;

    public InternalSyncController(AppDbContext context)
    {
        _context = context;
    }

    // 1. CẬP NHẬT LIÊN KẾT DEVICE - MCU - GPIO
    // PATCH /api/internal/devices/{deviceId}/binding

    [HttpPatch("devices/{deviceId:int}/binding")]
    public async Task<IActionResult> UpdateBinding(int deviceId, [FromBody] UpdateDeviceBindingRequestDto request)
    {
        // MCU và GPIO phải cùng null hoặc cùng có giá trị.
        if (request.MicrocontrollerId.HasValue != request.Gpio.HasValue)
        {
            return BadRequest(new
            {
                message = "MicrocontrollerId và Gpio phải cùng null hoặc cùng có giá trị."
            });
        }

        if (request.Gpio.HasValue && request.Gpio.Value < 0)
        {
            return BadRequest(new {message = "GPIO không hợp lệ." }); 
        }

        // 1.1. Tìm Device thuộc User
        var device = await _context.Devices
            .FirstOrDefaultAsync(d =>
                d.Id == deviceId &&
                d.UserId == request.UserId);

        if (device == null) return NotFound(new {message = "Không tìm thấy Device."});

        // 1.2. Lưu liên kết cũ
        int? oldMicrocontrollerId = device.MicrocontrollerId;
        int? oldGpio = device.Gpio;

        // 1.3. Kiểm tra MCU đích nếu có
        if (request.MicrocontrollerId.HasValue)
        {
            int mcuId = request.MicrocontrollerId.Value;

            var mcu = await _context.Microcontrollers
                .FirstOrDefaultAsync(m =>
                    m.Id == mcuId &&
                    m.UserId == request.UserId);

            if (mcu == null)
            {
                return BadRequest(new
                {
                    message = "Microcontroller không tồn tại hoặc không thuộc User."
                });
            }

            // Kiểm tra GPIO đã có thiết bị khác sử dụng
            bool gpioUsed = await _context.Devices
                .AnyAsync(d =>
                    d.Id != deviceId &&
                    d.MicrocontrollerId == mcuId &&
                    d.Gpio == request.Gpio);

            if (gpioUsed)
            {
                return Conflict(new
                {
                    message = "GPIO đã được Device khác sử dụng."
                });
            }

            // Giới hạn ESP32 tối đa 6 Device
            if (string.Equals(mcu.Type, "esp32", StringComparison.OrdinalIgnoreCase))
            {
                int count = await _context.Devices
                    .CountAsync(d =>
                        d.MicrocontrollerId == mcuId &&
                        d.Id != deviceId);

                if (count >= 6)
                {
                    return Conflict(new
                    {
                        message = "ESP32 đã đạt giới hạn 6 Device."
                    });
                }
            }
        }

        // 1.4. Cập nhật liên kết
        //
        // API này chỉ được NLP Server gọi sau khi
        // ESP32 đã xác nhận thao tác phần cứng thành công.
        //
        // Registry không tự gửi MQTT.

        device.MicrocontrollerId = request.MicrocontrollerId;
        device.Gpio = request.Gpio;

        if (request.MicrocontrollerId.HasValue)
        {
            device.SyncStatus = "synced";
        }
        else
        {
            device.SyncStatus = "unassigned";
        }

        // Nếu thay đổi liên kết, trạng thái vật lý cũ
        // không còn là thông tin đáng tin cậy.
        bool bindingChanged =
            oldMicrocontrollerId != request.MicrocontrollerId ||
            oldGpio != request.Gpio;

        if (bindingChanged)
        {
            device.CurrentStatus = "UNKNOWN";
            device.StatusUpdatedAt = null;
        }

        // Không thay đổi Schedule tại đây.
        // Đồng bộ lịch sẽ được xử lý riêng.

        try
        {
            await _context.SaveChangesAsync();
        }
        catch (DbUpdateException ex) when (
            ex.InnerException is PostgresException pg &&
            pg.SqlState == PostgresErrorCodes.UniqueViolation)
        {
            return Conflict(new
            {
                message = "Liên kết MCU/GPIO đã được sử dụng."
            });
        }

        return Ok(new
        {
            deviceId = device.Id,
            oldMicrocontrollerId,
            oldGpio,
            microcontrollerId = device.MicrocontrollerId,
            gpio = device.Gpio,
            syncStatus = device.SyncStatus
        });
    }

    // 2. CẬP NHẬT TRẠNG THÁI DEVICE
    // PUT /api/internal/devices/{deviceId}/status
    [HttpPut("devices/{deviceId:int}/status")]
    public async Task<IActionResult> ReportDeviceStatus(
        int deviceId,
        [FromBody] ReportDeviceStatusRequestDto request)
    {
        // 2.1. Kiểm tra SyncStatus
        string syncStatus = request.SyncStatus
            .Trim()
            .ToLowerInvariant();

        if (syncStatus != "synced" &&
            syncStatus != "out_of_sync" &&
            syncStatus != "error")
        {
            return BadRequest(new
            {
                message = "SyncStatus không hợp lệ."
            });
        }

        // 2.2. Kiểm tra CurrentStatus nếu được gửi
        string? currentStatus = null;

        if (request.CurrentStatus != null)
        {
            currentStatus = request.CurrentStatus
                .Trim()
                .ToUpperInvariant();

            if (currentStatus != "ON" &&
                currentStatus != "OFF" &&
                currentStatus != "UNKNOWN")
            {
                return BadRequest(new
                {
                    message = "CurrentStatus không hợp lệ."
                });
            }
        }

        // 2.3. Tìm Device thuộc User
        var device = await _context.Devices
            .FirstOrDefaultAsync(d =>
                d.Id == deviceId &&
                d.UserId == request.UserId);

        if (device == null)
        {
            return NotFound(new
            {
                message = "Không tìm thấy Device."
            });
        }

        // 2.4. Kiểm tra MCU/GPIO hiện tại
        //
        // Không cho phản hồi từ liên kết cũ
        // cập nhật nhầm trạng thái liên kết mới.
        if (device.MicrocontrollerId != request.MicrocontrollerId ||
            device.Gpio != request.Gpio)
        {
            return Conflict(new
            {
                message = "MCU/GPIO không khớp với liên kết hiện tại."
            });
        }

        // 2.5. Cập nhật trạng thái đồng bộ
        device.SyncStatus = syncStatus;

        // 2.6. Cập nhật trạng thái vật lý nếu được báo cáo
        if (currentStatus != null)
        {
            device.CurrentStatus = currentStatus;
            device.StatusUpdatedAt = DateTime.UtcNow;
        }

        await _context.SaveChangesAsync();

        return Ok(new
        {
            deviceId = device.Id,
            syncStatus = device.SyncStatus,
            currentStatus = device.CurrentStatus,
            statusUpdatedAt = device.StatusUpdatedAt
        });
    }

    // 3. NHẬN THÔNG TIN ĐỐI SOÁT TỪ ESP32
    // POST /api/internal/microcontrollers/{mcuId}/refresh

    [HttpPost("microcontrollers/{mcuId:int}/refresh")]
    public async Task<IActionResult> RefreshDevices(
        int mcuId,
        [FromBody] RefreshDevicesRequestDto request)
    {
        // 3.1. Tìm MCU thuộc User
        var mcu = await _context.Microcontrollers
            .FirstOrDefaultAsync(m =>
                m.Id == mcuId &&
                m.UserId == request.UserId);

        if (mcu == null)
        {
            return NotFound(new
            {
                message = "Không tìm thấy Microcontroller."
            });
        }

        // 3.2. Xác minh MAC
        string hardwareId = NormalizeHardwareId(request.HardwareId);
        string registeredId = NormalizeHardwareId(mcu.MacAddress);

        if (hardwareId != registeredId)
        {
            return Conflict(new
            {
                message = "HardwareId không khớp."
            });
        }

        // 3.3. Kiểm tra số lượng Device
        int count = request.DeviceCount;

        if (request.Gpios.Count != count ||
            request.DeviceTypes.Count != count ||
            request.DeviceNames.Count != count ||
            request.DeviceStatus.Count != count)
        {
            return BadRequest(new
            {
                message = "Số phần tử trong các mảng không khớp DeviceCount."
            });
        }

        // Không được trùng GPIO
        if (request.Gpios.Distinct().Count() != count)
        {
            return BadRequest(new
            {
                message = "Danh sách GPIO bị trùng."
            });
        }

        // Giới hạn ESP32
        if (string.Equals(
            mcu.Type,
            "esp32",
            StringComparison.OrdinalIgnoreCase) && count > 6)
        {
            return BadRequest(new
            {
                message = "Số Device vượt giới hạn ESP32."
            });
        }

        // 3.4. Kiểm tra GPIO và DeviceType
        if (request.Gpios.Any(g => g < 0) ||
            request.DeviceTypes.Any(string.IsNullOrWhiteSpace))
        {
            return BadRequest(new
            {
                message = "GPIO hoặc DeviceType không hợp lệ."
            });
        }

        // 3.5. Chuẩn hóa trạng thái
        var statuses = request.DeviceStatus
            .Select(s => s?.Trim().ToUpperInvariant())
            .ToList();

        if (statuses.Any(s => s != "ON" && s != "OFF"))
        {
            return BadRequest(new
            {
                message = "DeviceStatus chỉ được ON hoặc OFF."
            });
        }

        // 3.6. Lấy toàn bộ Device đã liên kết với MCU
        var devices = await _context.Devices
            .Include(d => d.DeviceType)
            .Where(d =>
                d.MicrocontrollerId == mcuId &&
                d.UserId == request.UserId)
            .ToListAsync();

        var matchedDeviceIds = new List<int>();
        var mismatchedDeviceIds = new List<int>();

        DateTime now = DateTime.UtcNow;

        // 3.7. Đối chiếu từng Device trên Registry
        foreach (var device in devices)
        {
            // Tìm GPIO của Device trong thông tin ESP32
            int index = -1;

            if (device.Gpio.HasValue)
            {
                index = request.Gpios.IndexOf(device.Gpio.Value);
            }

            // ESP32 không có GPIO tương ứng
            if (index == -1)
            {
                if (device.SyncStatus != "pending")
                {
                    device.SyncStatus = "out_of_sync";
                }

                mismatchedDeviceIds.Add(device.Id);
                continue;
            }

            // Kiểm tra loại thiết bị
            bool typeMatches = string.Equals(
                device.DeviceType?.TypeName,
                request.DeviceTypes[index]?.Trim(),
                StringComparison.OrdinalIgnoreCase
            );

            // Kiểm tra tên thiết bị
            bool nameMatches = string.Equals(
                device.DeviceName?.Trim() ?? "",
                request.DeviceNames[index]?.Trim() ?? "",
                StringComparison.OrdinalIgnoreCase
            );

            if (!typeMatches || !nameMatches)
            {
                device.SyncStatus = "out_of_sync";
                mismatchedDeviceIds.Add(device.Id);
                continue;
            }

            // Cấu hình trên Registry và ESP32 khớp
            device.SyncStatus = "synced";

            // Cập nhật trạng thái vật lý
            device.CurrentStatus = statuses[index]!;
            device.StatusUpdatedAt = now;

            matchedDeviceIds.Add(device.Id);
        }

        // 3.8. Tìm GPIO thừa trên ESP32
        var knownGpios = devices
            .Where(d => d.Gpio.HasValue)
            .Select(d => d.Gpio!.Value)
            .ToList();

        var unknownGpios = request.Gpios
            .Where(gpio => !knownGpios.Contains(gpio))
            .ToList();

        // 3.9. Cập nhật thông tin kết nối MCU
        mcu.ConnectionStatus = "online";
        mcu.LastSeenAt = now;

        // API chỉ ghi nhận kết quả đối soát.
        // Không tự ý tạo hoặc xóa Device tại đây.
        // Việc xử lý sai lệch thuộc quy trình đồng bộ riêng.

        await _context.SaveChangesAsync();

        return Ok(new
        {
            microcontrollerId = mcu.Id,
            matchedDeviceIds,
            mismatchedDeviceIds,
            unknownGpios,
            refreshedAt = now
        });
    }

    // 4. HÀM HỖ TRỢ CHUẨN HÓA MAC
    private static string NormalizeHardwareId(string value)
    {
        return value.Trim()
            .Replace(":", "")
            .Replace("-", "")
            .ToUpperInvariant();
    }
}
