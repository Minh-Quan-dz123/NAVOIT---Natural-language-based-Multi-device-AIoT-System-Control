
using System.Security.Claims;

using DeviceRegistry.Api.DTOs;
using DeviceRegistry.Api.Services;

using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace DeviceRegistry.Api.Controllers;

[ApiController]
[Authorize]
[Route("api/[controller]")]
public class DeviceController : ControllerBase
{
    private readonly DeviceService _deviceService;

    // 1. CONSTRUCTOR
    public DeviceController(DeviceService deviceService)
    {
        _deviceService = deviceService;
    }

    // 2. GET USER ID FROM JWT
    private int? GetCurrentUserId()
    {
        // JWT được Authentication Middleware xác thực
        // trước khi request vào Controller.
        //
        // ClaimTypes.NameIdentifier được AuthService
        // sử dụng để lưu ID người dùng.
        var userIdString = User.FindFirst(ClaimTypes.NameIdentifier)?.Value;

        if (!int.TryParse(userIdString, out var userId) || userId <= 0)return null;

        return userId;
    }

    // 3. CREATE DEVICE
    // POST /api/device

    [HttpPost]
    public async Task<IActionResult> Create([FromBody] CreateDeviceRequestDto request)
    {
        var userId = GetCurrentUserId();

        if (userId == null)return Unauthorized();

        try
        {
            var device = await _deviceService.CreateAsync(userId.Value, request);

            // 201 Created.
            // Trả về bản ghi đã tạo và URL để truy vấn.
            //
            // HTTP 201 chỉ xác nhận lưu database,
            // không xác nhận firmware đã tạo DeviceTask.
            return CreatedAtAction( nameof(GetById), new { id = device.Id }, device);
        }
        catch (ArgumentException ex)
        {
            return BadRequest(new { message = ex.Message });
        }
        catch (InvalidOperationException ex)
        {
            // Ví dụ: GPIO đã được sử dụng.
            return Conflict(new { message = ex.Message });
        }
    }

    // 4. GET ALL DEVICES
    // GET /api/device
    [HttpGet]
    public async Task<IActionResult> GetAll()
    {
        var userId = GetCurrentUserId();

        if (userId == null) return Unauthorized();

        var devices = await _deviceService.GetAllByUserIdAsync(userId.Value);

        return Ok(devices);
    }

    // 5. GET UNASSIGNED DEVICES
    // GET /api/device/unassigned
    [HttpGet("unassigned")]
    public async Task<IActionResult> GetUnassigned()
    {
        var userId = GetCurrentUserId();

        if (userId == null) return Unauthorized();

        var devices = await _deviceService.GetUnassignedAsync(userId.Value);

        return Ok(devices);
    }

    // 6. GET DEVICE BY ID
    // GET /api/device/{id}

    [HttpGet("{id:int}")]
    public async Task<IActionResult> GetById(int id)
    {
        var userId = GetCurrentUserId();

        if (userId == null) return Unauthorized();

        var device = await _deviceService.GetByIdAsync(id, userId.Value);

        if (device == null)
        {
            return NotFound(new {message = "Không tìm thấy Device."});
        }

        return Ok(device);
    }

    // 7. UPDATE DEVICE
    // PATCH /api/device/{id}
    [HttpPatch("{id:int}")]
    public async Task<IActionResult> Update(int id, [FromBody] UpdateDeviceRequestDto request)
    {
        var userId = GetCurrentUserId();

        if (userId == null) return Unauthorized();

        try
        {
            var device = await _deviceService.UpdateAsync( id, userId.Value, request);

            if (device == null)
            {
                return NotFound(new { message = "Không tìm thấy Device."});
            }

            return Ok(device);
        }
        catch (ArgumentException ex)
        {
            return BadRequest(new { message = ex.Message });
        }
        catch (InvalidOperationException ex)
        {
            // Ví dụ: đổi DeviceType khi đang gắn MCU.
            return Conflict(new { message = ex.Message });
        }
    }

    // 8. DELETE DEVICE
    // DELETE /api/device/{id}
    [HttpDelete("{id:int}")]
    public async Task<IActionResult> Delete(int id)
    {
        var userId = GetCurrentUserId();

        if (userId == null) return Unauthorized();

        try
        {
            var deleted = await _deviceService.DeleteAsync(id,userId.Value);

            if (!deleted)
            {
                return NotFound(new{  message = "Không tìm thấy Device."});
            }

            // 204 No Content.
            return NoContent();
        }
        catch (InvalidOperationException ex)
        {
            return Conflict(new { message = ex.Message });
        }
    }

    // 9. DEVICE RESOLUTION
    // POST /api/device/resolve

    [HttpPost("resolve")]
    public IActionResult Resolve(
        [FromBody] DeviceResolutionRequestDto request
    )
    {
        // TODO: Hoàn thiện khi code Tag và TagGroup.
        //
        // Chức năng sẽ:
        // 1. Lấy UserId từ JWT hoặc danh tính service tin cậy.
        // 2. Chuẩn hóa danh sách tags.
        // 3. Tìm các TagGroup tương ứng.
        // 4. Tìm Device liên kết với các TagGroup.
        // 5. Trả danh sách Device và điểm khớp.
        //
        // Không sử dụng request.UserId một cách trực tiếp
        // vì client có thể giả mạo ID người dùng.
        //
        // Chưa triển khai nên không trả 200 OK giả.

        // có thể triển khai bên server NLP

        return StatusCode(
            StatusCodes.Status501NotImplemented,
            new
            {
                message = "Device Resolution chưa được triển khai."
            }
        );
    }
}
