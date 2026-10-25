
using System.Security.Cryptography;
using System.Text;

using DeviceRegistry.Api.Data;
using DeviceRegistry.Api.DTOs;
using DeviceRegistry.Api.Services;

using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;

using Npgsql;

namespace DeviceRegistry.Api.Controllers;

[ApiController]
[Route("api/internal")]
public class InternalSyncController : ControllerBase
{
    private readonly AppDbContext _context;
    private readonly ScheduleServices _scheduleService;
    private readonly IConfiguration _configuration;

    // 1. CONSTRUCTOR

    public InternalSyncController(
        AppDbContext context,
        ScheduleServices scheduleService,
        IConfiguration configuration
    )
    {
        _context = context;
        _scheduleService = scheduleService;
        _configuration = configuration;
    }

    // 2. KIỂM TRA INTERNAL API KEY

    private bool IsInternalAuthorized()
    {
        // Không dùng JWT của User cho API này.
        // Chỉ NLP Server được biết InternalApiKey.

        var expectedKey = _configuration["InternalApiKey"];

        if (string.IsNullOrWhiteSpace(expectedKey))
            return false;

        if (!Request.Headers.TryGetValue(
            "X-Internal-Key",
            out var providedKey
        ))
        {
            return false;
        }

        var expectedBytes = Encoding.UTF8.GetBytes(expectedKey);
        var providedBytes = Encoding.UTF8.GetBytes(
            providedKey.ToString()
        );

        // So sánh constant-time, tránh so sánh
        // secret theo cách dừng tại ký tự khác đầu tiên.
        return CryptographicOperations.FixedTimeEquals(
            expectedBytes,
            providedBytes
        );
    }

    // ==========================================
    // 3. UPDATE DEVICE BINDING
    // PATCH /api/internal/devices/{id}/binding
    // ==========================================

    [HttpPatch("devices/{deviceId:int}/binding")]
    public async Task<IActionResult> UpdateBinding(
        int deviceId,
        [FromBody] UpdateDeviceBindingRequestDto request
    )
    {
        if (!IsInternalAuthorized())return Unauthorized();

        // MCU và GPIO phải cùng có giá trị hoặc cùng null.
        if (request.MicrocontrollerId.HasValue != request.Gpio.HasValue)
        {
            return BadRequest(new
            {
                message = "MicrocontrollerId và Gpio phải cùng null hoặc cùng có giá trị."
            });
        }

        if (request.Gpio < 0) return BadRequest(new { message = "GPIO không hợp lệ." });

        // 3.1. Kiểm tra Device thuộc User.
        var device = await _context.Devices
            .Include(d => d.Schedule)
            .FirstOrDefaultAsync(d =>
                d.Id == deviceId &&
                d.UserId == request.UserId
            );

        if (device == null)
            return NotFound(new { message = "Không tìm thấy Device." });

        // 3.2. Lưu thông tin liên kết cũ.
        var oldMicrocontrollerId = device.MicrocontrollerId;
        var oldGpio = device.Gpio;

        // 3.3. Kiểm tra MCU đích.
        if (request.MicrocontrollerId.HasValue)
        {
            var mcuId = request.MicrocontrollerId.Value;

            var mcu = await _context.Microcontrollers
                .FirstOrDefaultAsync(m =>
                    m.Id == mcuId &&
                    m.UserId == request.UserId
                );

            if (mcu == null)
                return BadRequest(new
                {
                    message = "Microcontroller không tồn tại hoặc không thuộc User."
                });

            // Không cho hai Device chiếm cùng GPIO.
            var gpioUsed = await _context.Devices
                .AnyAsync(d =>
                    d.Id != deviceId &&
                    d.MicrocontrollerId == mcuId &&
                    d.Gpio == request.Gpio
                );

            if (gpioUsed) return Conflict(new
                {
                    message = "GPIO đang được Device khác sử dụng."
                });

            // Giới hạn firmware ESP32 hiện tại.
            if (mcu.Type.Equals(
                "esp32",
                StringComparison.OrdinalIgnoreCase
            ))
            {
                var count = await _context.Devices
                    .CountAsync(d =>
                        d.MicrocontrollerId == mcuId &&
                        d.Id != deviceId
                    );

                if (count >= 6)
                    return Conflict(new
                    {
                        message = "ESP32 đã đạt giới hạn 6 Device."
                    });
            }
        }

        // 3.4. Chỉ lưu sau khi NLP Server đã hoàn tất
        // các thao tác vật lý liên quan.
        //
        // Ví dụ chuyển MCU A -> B:
        // - NLP gửi DELETE tới A.
        // - NLP xác minh DeviceTask cũ đã bị xóa.
        // - NLP gửi CREATE tới B.
        // - NLP xác minh DeviceTask mới đã được tạo.
        // - Cuối cùng mới gọi API này.
        //
        // Registry KHÔNG gửi MQTT tại đây.
        device.MicrocontrollerId = request.MicrocontrollerId;
        device.Gpio = request.Gpio;

        device.SyncStatus = request.MicrocontrollerId.HasValue ? "synced" : "unassigned";

        // Không thể lấy trạng thái ON/OFF cũ làm
        // trạng thái chắc chắn của liên kết mới.
        device.CurrentStatus = "UNKNOWN";
        device.StatusUpdatedAt = null;

        if (
            device.Schedule != null &&
            (oldMicrocontrollerId != request.MicrocontrollerId ||
             oldGpio != request.Gpio)
        )
        {
            // Không tự chuyển Schedule sang MCU mới.
            // Firmware cũ phải được xử lý trước khi gọi API.
            device.Schedule.SyncStatus = "unknown";
            device.Schedule.UpdatedAt = DateTime.UtcNow;
        }

        try
        {
            await _context.SaveChangesAsync();
        }
        catch (DbUpdateException ex) when (
            ex.InnerException is PostgresException pg &&
            pg.SqlState == PostgresErrorCodes.UniqueViolation
        )
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

    // 4. REPORT DEVICE STATUS
    // PUT /api/internal/devices/{id}/status

    [HttpPut("devices/{deviceId:int}/status")]
    public async Task<IActionResult> ReportDeviceStatus(
        int deviceId,
        [FromBody] ReportDeviceStatusRequestDto request
    )
    {
        if (!IsInternalAuthorized())return Unauthorized();

        // Chỉ cho phép ba trạng thái kết quả.
        // "pending" được quản lý khi tạo request,
        // không phải trạng thái kết quả từ firmware.
        var syncStatus = request.SyncStatus.Trim().ToLowerInvariant();

        if (
            syncStatus != "synced" &&
            syncStatus != "out_of_sync" &&
            syncStatus != "error"
        )
        {
            return BadRequest(new{ message = "SyncStatus không hợp lệ."});
        }

        // 4.1. Tìm đúng Device của User.
        var device = await _context.Devices
            .FirstOrDefaultAsync(d =>
                d.Id == deviceId &&
                d.UserId == request.UserId
            );

        if (device == null) return NotFound();

        // 4.2. Kiểm tra vị trí phần cứng hiện tại.
        //
        // Chống việc response cũ từ GPIO/MCU trước đó
        // cập nhật nhầm Device sau khi đã chuyển GPIO.
        if (
            device.MicrocontrollerId != request.MicrocontrollerId ||
            device.Gpio != request.Gpio
        )
        {
            return Conflict(new{message = "MCU/GPIO không khớp với liên kết hiện tại."});
        }

        // 4.3. Cập nhật kết quả đồng bộ.
        device.SyncStatus = syncStatus;

        // Chỉ cập nhật CurrentStatus khi có báo cáo
        // trạng thái thực tế đáng tin cậy từ ESP32.
        if (request.CurrentStatus != null)
        {
            var status = request.CurrentStatus
                .Trim()
                .ToUpperInvariant();

            if (status != "ON" &&status != "OFF" && status != "UNKNOWN")
            {
                return BadRequest(new{message = "CurrentStatus không hợp lệ."});
            }

            device.CurrentStatus = status;
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

    // 5. REFRESH DEVICE LIST
    // POST /api/internal/microcontrollers/{id}/refresh

    [HttpPost("microcontrollers/{mcuId:int}/refresh")]
    public async Task<IActionResult> RefreshDevices(int mcuId,[FromBody] RefreshDevicesRequestDto request)
    {
        if (!IsInternalAuthorized()) return Unauthorized();

        // 5.1. Tìm MCU thuộc User.
        var mcu = await _context.Microcontrollers
            .FirstOrDefaultAsync(m =>
                m.Id == mcuId &&
                m.UserId == request.UserId
            );

        if (mcu == null)return NotFound(new{message = "Không tìm thấy Microcontroller."});

        // 5.2. Kiểm tra định danh phần cứng.
        //
        // MAC có thể được viết có hoặc không có dấu ':'.
        // Chuẩn hóa để so sánh.
        static string NormalizeId(string value)
        {
            return value.Trim()
                .Replace(":", "")
                .Replace("-", "")
                .ToUpperInvariant();
        }

        if (NormalizeId(mcu.MacAddress) !=
            NormalizeId(request.HardwareId))
        {
            return Conflict(new
            {
                message = "HardwareId không khớp."
            });
        }

        // 5.3. Kiểm tra số lượng phần tử trong
        // các mảng song song từ firmware.
        var n = request.DeviceCount;

        if (
            request.Gpios.Count != n ||
            request.DeviceTypes.Count != n ||
            request.DeviceNames.Count != n ||
            request.DeviceStatus.Count != n ||
            request.Gpios.Distinct().Count() != n
        )
        {
            return BadRequest(new
            {
                message = "REFRESH_DEVICE_RESPONSE không hợp lệ."
            });
        }

        if (mcu.Type.Equals("esp32", StringComparison.OrdinalIgnoreCase) && n > 6)
        {
            return BadRequest(new
            {
                message = "Số lượng Device vượt giới hạn ESP32."
            });
        }

        // 5.4. Chuẩn hóa status trước khi thay đổi database.
        var statuses = request.DeviceStatus
            .Select(s => s?.Trim().ToUpperInvariant())
            .ToList();

        if (
            request.Gpios.Any(g => g < 0) ||
            request.DeviceTypes.Any(string.IsNullOrWhiteSpace) ||
            statuses.Any(s => s != "ON" && s != "OFF")
        )
        {
            return BadRequest(new
            {
                message = "GPIO, DeviceType hoặc DeviceStatus không hợp lệ."
            });
        }

        // 5.5. Tạo bảng tra cứu GPIO -> vị trí trong mảng.
        var indexByGpio = request.Gpios
            .Select((gpio, index) => new { gpio, index })
            .ToDictionary(x => x.gpio, x => x.index);

        // 5.6. Lấy các Device đã đăng ký ở MCU này.
        var devices = await _context.Devices
            .Include(d => d.DeviceType)
            .Include(d => d.Schedule)
            .Where(d =>
                d.MicrocontrollerId == mcuId &&
                d.UserId == request.UserId
            )
            .ToListAsync();

        var now = DateTime.UtcNow;
        var matched = new List<int>();
        var mismatched = new List<int>();

        foreach (var device in devices)
        {
            // 5.7. Không tìm thấy GPIO của Device
            // trong snapshot firmware.
            if (
                device.Gpio == null ||
                !indexByGpio.TryGetValue(
                    device.Gpio.Value,
                    out var index
                )
            )
            {
                // Nếu đang pending CREATE thì có thể
                // lệnh vẫn chưa được gửi xuống firmware.
                if (device.SyncStatus != "pending")
                    device.SyncStatus = "out_of_sync";

                mismatched.Add(device.Id);
                continue;
            }

            // 5.8. Kiểm tra loại và tên thiết bị.
            // Không tự ý đổi metadata trong Registry
            // theo thông tin firmware.
            bool typeMatches = string.Equals(
                device.DeviceType.TypeName,
                request.DeviceTypes[index]?.Trim(),
                StringComparison.OrdinalIgnoreCase
            );

            bool nameMatches = string.Equals(
                device.DeviceName?.Trim() ?? "",
                request.DeviceNames[index]?.Trim() ?? "",
                StringComparison.OrdinalIgnoreCase
            );

            if (!typeMatches || !nameMatches)
            {
                device.SyncStatus = "out_of_sync";
                mismatched.Add(device.Id);
                continue;
            }

            // 5.9. Cấu hình khớp với firmware.
            device.SyncStatus = "synced";

            // Refresh báo cáo trạng thái GPIO hiện tại.
            device.CurrentStatus = statuses[index]!;
            device.StatusUpdatedAt = now;

            matched.Add(device.Id);
        }

        // 5.10. Những GPIO tồn tại ở ESP32
        // nhưng chưa được đăng ký trong Registry.
        //
        // Không tự tạo Device mới vì thiếu User
        // cung cấp các mô tả và TagGroup.
        var knownGpios = devices
            .Where(d => d.Gpio.HasValue)
            .Select(d => d.Gpio!.Value)
            .ToHashSet();

        var unknownGpios = request.Gpios
            .Where(g => !knownGpios.Contains(g))
            .ToList();

        // Có phản hồi refresh hợp lệ từ MCU.
        mcu.ConnectionStatus = "online";
        mcu.LastSeenAt = now;

        // REFRESH_DEVICE_RESPONSE hiện chưa báo Schedule,
        // nên tuyệt đối không đánh dấu Schedule đã chạy.
        await _context.SaveChangesAsync();

        return Ok(new
        {
            microcontrollerId = mcu.Id,
            matchedDeviceIds = matched,
            mismatchedDeviceIds = mismatched,
            unknownGpios,
            refreshedAt = now
        });
    }

    // 6. REGISTER SCHEDULE COMMAND
    // POST /api/internal/schedules/{id}/command

    [HttpPost("schedules/{deviceId:int}/command")]
    public async Task<IActionResult> RegisterScheduleCommand(
        int deviceId,
        [FromBody] RegisterScheduleCommandRequestDto request
    )
    {
        if (!IsInternalAuthorized())return Unauthorized();

        // Kiểm tra Device thuộc User được chỉ định.
        var belongsToUser = await _context.Devices
            .AnyAsync(d =>
                d.Id == deviceId &&
                d.UserId == request.UserId
            );

        if (!belongsToUser)return NotFound();

        try
        {
            // Ghi command_id trước khi NLP publish MQTT,
            // giúp đối chiếu response về sau.
            await _scheduleService.RegisterCommandAsync(
                deviceId,
                request.CommandId
            );

            return NoContent();
        }
        catch (KeyNotFoundException ex)
        {
            return NotFound(new { message = ex.Message });
        }
        catch (ArgumentException ex)
        {
            return BadRequest(new { message = ex.Message });
        }
        catch (InvalidOperationException ex)
        {
            return Conflict(new { message = ex.Message });
        }
    }

    // 7. APPLY SCHEDULE ACK
    // POST /api/internal/schedules/{id}/ack
    [HttpPost("schedules/{deviceId:int}/ack")]
    public async Task<IActionResult> ApplyScheduleAck(int deviceId, [FromBody] ScheduleAckRequestDto request)
    {
        if (!IsInternalAuthorized())return Unauthorized();

        // Không cho response của User này
        // cập nhật Schedule của User khác.
        var belongsToUser = await _context.Devices
            .AnyAsync(d =>
                d.Id == deviceId &&
                d.UserId == request.UserId
            );

        if (!belongsToUser)return NotFound();

        if (!request.Accepted.HasValue)return BadRequest(new { message = "Thiếu kết quả Accepted."});

        try
        {
            // CommandId phải khớp với lịch đang chờ.
            // Accepted chỉ được lấy từ kết quả xác thực
            // thực tế của firmware.
            await _scheduleService.ApplyAcknowledgementAsync(
                deviceId,
                request.CommandId,
                request.Accepted.Value
            );

            return NoContent();
        }
        catch (KeyNotFoundException ex)
        {
            return NotFound(new { message = ex.Message });
        }
        catch (InvalidOperationException ex)
        {
            return Conflict(new { message = ex.Message });
        }
    }
}
