
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

}
