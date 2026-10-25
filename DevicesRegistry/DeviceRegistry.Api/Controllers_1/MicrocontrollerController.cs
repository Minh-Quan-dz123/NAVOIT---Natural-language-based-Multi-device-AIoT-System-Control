
using System.Security.Claims;

using DeviceRegistry.Api.DTOs;
using DeviceRegistry.Api.Services;

using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace DeviceRegistry.Api.Controllers;

[ApiController]
[Authorize]
[Route("api/[controller]")]
public class MicrocontrollerController : ControllerBase // Trong ControllerBase, ASP.NET Core đã định nghĩa sẵn property User, về mặt ý tưởng tương đương: public ClaimsPrincipal User => HttpContext.User;
{
    private readonly MicrocontrollerService _service;

    // 1. CONSTRUCTOR
    public MicrocontrollerController(MicrocontrollerService service)
    {
        _service = service;
    }

    // 2. LẤY USER ID TỪ JWT
    private int? GetCurrentUserId()
    {
        // AuthService hiện lưu UserId vào claim
        // ClaimTypes.NameIdentifier.
        //
        // Sau khi JWT được xác thực thành công,
        // có thể đọc claim thông qua HttpContext.User.
        var userIdString = User.FindFirst(ClaimTypes.NameIdentifier)?.Value;

        if (!int.TryParse(userIdString, out var userId) || userId <= 0) return null;

        return userId;
    }

    // 3. CREATE MICROCONTROLLER
    // POST /api/microcontroller
    [HttpPost]
    public async Task<IActionResult> Create([FromBody] CreateMicrocontrollerRequestDto request)
    {
        var userId = GetCurrentUserId();

        if (userId == null) return Unauthorized(new { message = "JWT không hợp lệ." });

        try
        {
            var result = await _service.CreateAsync(userId.Value, request);

            // HTTP 201 Created.
            // Location trỏ tới GET /api/microcontroller/{id}.
            return CreatedAtAction(nameof(GetById), new { id = result.Id },result);
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

    // 4. GET ALL MICROCONTROLLERS
    // GET /api/microcontroller

    [HttpGet]
    public async Task<IActionResult> GetAll()
    {
        var userId = GetCurrentUserId();

        if (userId == null) return Unauthorized(new { message = "JWT không hợp lệ." });

        var result = await _service.GetAllAsync(userId.Value);

        return Ok(result);
    }

    // 5. GET MICROCONTROLLER BY ID
    // GET /api/microcontroller/{id}

    [HttpGet("{id:int}")]
    public async Task<IActionResult> GetById(int id)
    {
        var userId = GetCurrentUserId();

        if (userId == null) return Unauthorized(new { message = "JWT không hợp lệ." });

        var result = await _service.GetByIdAsync(id, userId.Value);

        if (result == null)return NotFound(new { message = "Không tìm thấy Microcontroller." });

        return Ok(result);
    }

    // 6. UPDATE MICROCONTROLLER
    // PATCH /api/microcontroller/{id}

    [HttpPatch("{id:int}")]
    public async Task<IActionResult> Update(int id, [FromBody] UpdateMicrocontrollerRequestDto request)
    {
        var userId = GetCurrentUserId();

        if (userId == null)
            return Unauthorized(new { message = "JWT không hợp lệ." });

        try
        {
            var result = await _service.UpdateAsync(id, userId.Value, request);

            if (result == null) return NotFound(new {message = "Không tìm thấy Microcontroller."});

            return Ok(result);
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

    // 7. DELETE MICROCONTROLLER
    // DELETE /api/microcontroller/{id}
    [HttpDelete("{id:int}")]
    public async Task<IActionResult> Delete(int id)
    {
        var userId = GetCurrentUserId();

        if (userId == null) return Unauthorized(new { message = "JWT không hợp lệ." });

        var deleted = await _service.DeleteAsync(id, userId.Value);

        if (!deleted) return NotFound(new { message = "Không tìm thấy Microcontroller."});

        // HTTP 204, không trả response body.
        return NoContent();
    }

    // 8. GET DEVICES BY MICROCONTROLLER
    // GET /api/microcontroller/{id}/devices
    [HttpGet("{id:int}/devices")]
    public async Task<IActionResult> GetDevices(int id)
    {
        var userId = GetCurrentUserId();

        if (userId == null) return Unauthorized(new { message = "JWT không hợp lệ." });

        var result = await _service.GetDevicesAsync(id, userId.Value);

        if (result == null) return NotFound(new {message = "Không tìm thấy Microcontroller."});

        return Ok(result);
    }
}
