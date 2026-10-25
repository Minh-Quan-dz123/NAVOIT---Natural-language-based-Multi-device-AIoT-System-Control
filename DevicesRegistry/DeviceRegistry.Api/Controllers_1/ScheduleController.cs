
using System.Security.Claims;

using DeviceRegistry.Api.DTOs;
using DeviceRegistry.Api.Services;

using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace DeviceRegistry.Api.Controllers;

[ApiController]
[Authorize]
[Route("api/device/{deviceId:int}/schedule")]
public class ScheduleController : ControllerBase
{
    private readonly ScheduleServices _service;

    // 1. CONSTRUCTOR
    public ScheduleController(ScheduleServices service)
    {
        _service = service;
    }

    // 2. GET CURRENT USER ID FROM JWT
    private int? GetCurrentUserId()
    {
        // Đọc UserId đã được AuthService đưa vào JWT.
        // Không lấy UserId từ Body hoặc QueryString.
        var userIdString = User.FindFirst(ClaimTypes.NameIdentifier)?.Value;

        if (!int.TryParse(userIdString, out var userId)|| userId <= 0) return null;

        return userId;
    }

    // 3. GET SCHEDULE
    // GET /api/device/{deviceId}/schedule

    [HttpGet]
    public async Task<IActionResult> GetSchedule(int deviceId)
    {
        var userId = GetCurrentUserId();

        if (userId == null)return Unauthorized();

        var schedule = await _service.GetByDeviceIdAsync(
            deviceId,
            userId.Value
        );

        if (schedule == null) return NotFound(new {message = "Không tìm thấy Schedule."});

        return Ok(schedule);
    }

    // 4. CREATE / UPDATE SCHEDULE
    // PUT /api/device/{deviceId}/schedule

    [HttpPut]
    public async Task<IActionResult> UpsertSchedule(
        int deviceId,
        [FromBody] UpsertScheduleRequestDto request
    )
    {
        var userId = GetCurrentUserId();

        if (userId == null) return Unauthorized();

        try
        {
            var result = await _service.UpsertAsync(
                deviceId,
                userId.Value,
                request
            );

            // HTTP 200:
            // Đã lưu cấu hình Schedule vào database.
            //
            // syncStatus = pending:
            // Chưa xác nhận ESP32 tiếp nhận.
            //
            // Không trả về thông báo "ESP đã lập lịch".
            return Ok(result);
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

    // 5. CANCEL SCHEDULE
    // DELETE /api/device/{deviceId}/schedule
    [HttpDelete]
    public async Task<IActionResult> CancelSchedule(int deviceId)
    {
        var userId = GetCurrentUserId();

        if (userId == null) return Unauthorized();

        try
        {
            var result = await _service.CancelAsync(deviceId, userId.Value);

            // null: Lịch pending chưa gửi MQTT
            // đã được xóa khỏi database.
            if (result == null) return NoContent();

            // Nếu lịch từng được gửi:
            // chỉ ghi nhận yêu cầu hủy, chưa xóa lịch.
            //
            // syncStatus = cancel_pending.
            return Ok(result);
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
