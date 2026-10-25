// Controller này chịu trách nhiệm liên kết Device với TagGroup.
using System.Security.Claims;

using DeviceRegistry.Api.DTOs;
using DeviceRegistry.Api.Services;

using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace DeviceRegistry.Api.Controllers;

[ApiController]
[Authorize]
[Route("api/device/{deviceId:int}/tags")]
public class DeviceTagGroupController : ControllerBase
{
    private readonly ManageTagsService _service;

    // 1. CONSTRUCTOR
    public DeviceTagGroupController(ManageTagsService service)
    {
        _service = service;
    }

    // 2. GET USER ID FROM JWT
    private int? GetCurrentUserId()
    {
        var value = User.FindFirst(ClaimTypes.NameIdentifier)?.Value;

        if (!int.TryParse(value, out var userId) || userId <= 0) return null;

        return userId;
    }

    // 3. GET DEVICE TAGS
    // GET /api/device/{deviceId}/tags

    [HttpGet]
    public async Task<IActionResult> GetDeviceTags(int deviceId)
    {
        var userId = GetCurrentUserId();

        if (userId == null)return Unauthorized();

        var result = await _service.GetDeviceTagsAsync(deviceId,userId.Value);

        if (result == null)
        {
            return NotFound(new{ message = "Không tìm thấy Device."});
        }

        return Ok(result);
    }

    // 4. REPLACE DEVICE TAGS
    // PUT /api/device/{deviceId}/tags

    [HttpPut]
    public async Task<IActionResult> ReplaceDeviceTags(
        int deviceId,
        [FromBody] CreateTagRequestDto request
    )
    {
        var userId = GetCurrentUserId();

        if (userId == null) return Unauthorized();

        try
        {
            var result = await _service.ReplaceDeviceTagsAsync(deviceId, userId.Value, request);

            // 200 OK:
            // Đã lưu các liên kết TagGroup vào database.
            //
            // Không có MQTT ở API này vì TagGroup
            // chỉ phục vụ Device Resolution.
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
}
