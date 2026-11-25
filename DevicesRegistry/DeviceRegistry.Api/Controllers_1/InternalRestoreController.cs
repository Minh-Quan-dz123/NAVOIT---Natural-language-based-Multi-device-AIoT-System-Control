
using System.Text.RegularExpressions;

using DeviceRegistry.Api.Data;

using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;

namespace DeviceRegistry.Api.Controllers;


[ApiController]
[Authorize(Policy = "NlpServerOnly")]
[Route("api/internal/microcontrollers")]
public class InternalRestoreController : ControllerBase
{
    private readonly AppDbContext _context;

    public InternalRestoreController(AppDbContext context)
    {
        _context = context;
    }


    // 1. LẤY CẤU HÌNH ĐỂ KHÔI PHỤC MCU
    // GET /api/internal/microcontrollers/{mac}/restore
    //
    // Chỉ NLP Server được gọi bằng X-Internal-Key.
    // Không thay đổi dữ liệu trong Registry.

    [HttpGet("{mac}/restore")]
    public async Task<IActionResult> GetRestoreData(
        string mac,
        [FromQuery] string? type)
    {
        // 1.1. Chuẩn hóa MAC.
        // Ví dụ: AA:BB:CC:DD:EE:FF -> AABBCCDDEEFF
        string normalizedMac = mac
            .Trim()
            .Replace(":", "")
            .Replace("-", "")
            .ToUpperInvariant();

        if (!Regex.IsMatch(normalizedMac, @"^[0-9A-F]{12}$"))
        {
            return BadRequest(new
            {
                message = "MAC không hợp lệ."
            });
        }


        // 1.2. Kiểm tra loại MCU
        string normalizedType = (type ?? "").Trim().ToLowerInvariant();

        if (
            normalizedType.Length > 50 ||
            !Regex.IsMatch(
                normalizedType,
                @"^[a-z0-9][a-z0-9_-]*$"
            )
        )
        {
            return BadRequest(new
            {
                message = "Loại MCU không hợp lệ."
            });
        }

        // 1.3. Tìm MCU theo MAC và Type
        var mcu = await _context.Microcontrollers
            .AsNoTracking()
            .FirstOrDefaultAsync(m =>
                m.MacAddress == normalizedMac &&
                m.Type == normalizedType);

            if (mcu == null)
            {
                return NotFound(new
                {
                    message = "Không tìm thấy MCU tương ứng trong Registry."
                });
            }


        // 1.3. Kiểm tra MCU đã có chủ sở hữu.
        if (!mcu.UserId.HasValue || mcu.UserId.Value <= 0)
        {
            return Conflict(new
            {
                message = "MCU chưa được cấp cho User."
            });
        }

        int userId = mcu.UserId.Value;


        // 1.4. Lấy tất cả Device đang liên kết với MCU
        // Lấy cả DeviceType và Schedule.
        //
        // Schedule thuộc Device trong Registry.
        // Không phụ thuộc cố định vào GPIO.

        var devices = await _context.Devices
            .AsNoTracking()
            .Where(d => d.MicrocontrollerId == mcu.Id)
            .Include(d => d.DeviceType)
            .Include(d => d.Schedule)
            .OrderBy(d => d.Gpio)
            .ToListAsync();


        // 1.5. Kiểm tra dữ liệu liên kết.
        // Nếu dữ liệu Registry bất thường thì báo lỗi,
        // không trả cấu hình thiếu cho NLP.

        foreach (var device in devices)
        {
            if (device.UserId != userId)
            {
                return Conflict(new
                {
                    message = "Device không thuộc User sở hữu MCU."
                });
            }

            if (!device.Gpio.HasValue)
            {
                return Conflict(new
                {
                    message = "Device đang liên kết MCU nhưng thiếu GPIO."
                });
            }
        }


        // 1.6. Chuyển Device và Schedule sang JSON.
        // Tên trường phải khớp với NLP Server.

        long now = DateTimeOffset.UtcNow.ToUnixTimeSeconds();

        var result = devices.Select(d => new
        {
            deviceId = d.Id,

            microcontrollerId = d.MicrocontrollerId,

            gpio = d.Gpio,

            deviceType = d.DeviceType.TypeName,

            deviceName = d.DeviceName ?? "",

            syncStatus = d.SyncStatus,

            currentStatus = d.CurrentStatus,

            // Không có Schedule thì trả null.
            // Có Schedule thì trả đầy đủ dữ liệu.
            schedule = d.Schedule == null ? null : new
            {
                id = d.Schedule.Id,

                deviceId = d.Schedule.DeviceId,

                action = d.Schedule.Action,

                scheduledDelay = d.Schedule.Delay,

                duration = d.Schedule.Duration,

                scheduledStartAt = d.Schedule.ScheduledStartAt,

                scheduledEndAt = d.Schedule.ScheduledEndAt,

                expiresAt = d.Schedule.ExpiresAt,

                isExpired = now >= d.Schedule.ExpiresAt
            }

        }).ToList();


        // 1.7. Trả cấu hình chuẩn cho NLP Server.
        return Ok(new
        {
            microcontroller = new
            {
                id = mcu.Id,

                userId = userId,

                macAddress = mcu.MacAddress,

                type = mcu.Type
            },

            devices = result
        });
    }
}
