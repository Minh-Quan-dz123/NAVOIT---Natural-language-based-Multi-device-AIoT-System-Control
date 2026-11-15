
using System.Security.Claims;

using DeviceRegistry.Api.DTOs;
using DeviceRegistry.Api.Services;

using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace DeviceRegistry.Api.Controllers;

[ApiController]
[Authorize]
[Route("api/[controller]")]
public class MicrocontrollerController : ControllerBase
{
    private readonly MicrocontrollerService _service;

    public MicrocontrollerController(MicrocontrollerService service)
    {
        _service = service;
    }

    // 0. HELPER LẤY USER ID TỪ JWT
    private int? GetCurrentUserId()
    {
        string? userIdString = User.FindFirst(ClaimTypes.NameIdentifier)?.Value;
        if (!int.TryParse(userIdString, out int userId)|| userId <= 0)  return null;
        return userId;
    }

    // 1. USER LẤY DANH SÁCH MCU CỦA MK
    // GET /api/microcontroller
    [HttpGet]
    public async Task<IActionResult> GetAll()
    {
        int? userId = GetCurrentUserId();
        if (userId == null)
        {
            return Unauthorized(new{ message = "JWT không hợp lệ."});
        }

        var result = await _service.GetAllAsync(userId.Value);

        return Ok(result);
    }

    // 2. USER XEM MCU CỦA MÌNH QUA ID
    // GET /api/microcontroller/{id}

    [HttpGet("{id:int}")]
    public async Task<IActionResult> GetById(int id)
    {
        int? userId = GetCurrentUserId();

        if (userId == null)
        {
            return Unauthorized(new{message = "JWT không hợp lệ."});
        }

        var result = await _service.GetByIdAsync(id, userId.Value);

        if (result == null)
        {
            return NotFound(new
            {
                message = "Không tìm thấy Microcontroller."
            });
        }

        return Ok(result);
    }

    // 3. USER XEM DEVICE CỦA MCU
    // GET /api/microcontroller/{id}/devices
    [HttpGet("{id:int}/devices")]
    public async Task<IActionResult> GetDevices(int id)
    {
        int? userId = GetCurrentUserId();

        if (userId == null)
        {
            return Unauthorized(new {message = "JWT không hợp lệ."});

                
        }

        var result = await _service.GetDevicesAsync(id, userId.Value);

        if (result == null)
        {
            return NotFound(new
            {
                message = "Không tìm thấy Microcontroller."
            });
        }

        return Ok(result);
    }

    // 4. ADMIN XEM TẤT CẢ MCU
    // GET /api/microcontroller/admin
    [HttpGet("admin")]
    [Authorize(Roles = "Admin")]
    public async Task<IActionResult> GetAllForAdmin()
    {
        var result = await _service.GetAllForAdminAsync();
        return Ok(result);
    }

    // 5. ADMIN XEM MCU THEO ID
    // GET /api/microcontroller/admin/{id}
    [HttpGet("admin/{id:int}")]
    [Authorize(Roles = "Admin")]
    public async Task<IActionResult> GetForAdminById(int id)
    {
        var result = await _service.GetForAdminByIdAsync(id);

        if (result == null)
        {
            return NotFound(new
            {
                message = "Không tìm thấy Microcontroller."
            });
        }
        return Ok(result);
    }

    // 6. ADMIN TẠO MCU
    // POST /api/microcontroller
    // UserId có thể null.
    [HttpPost]
    [Authorize(Roles = "Admin")]
    public async Task<IActionResult> Create([FromBody] CreateMicrocontrollerRequestDto request)
    {
        try
        {
            // Service mới chỉ nhận 1 tham số.
            var result = await _service.CreateAsync(request);

            return CreatedAtAction(
                nameof(GetForAdminById),
                new { id = result.Id },
                result
            );
        }
        catch (ArgumentException ex)
        {
            return BadRequest(new{ message = ex.Message});
        }
        catch (InvalidOperationException ex)
        {
            return Conflict(new {message = ex.Message});
        }
    }

    // 7. ADMIN - CẬP NHẬT MCU
    // PATCH /api/microcontroller/{id}
    [HttpPatch("{id:int}")]
    [Authorize(Roles = "Admin")]
    public async Task<IActionResult> Update(
        int id,
        [FromBody] UpdateMicrocontrollerRequestDto request)
    {
        try
        {
            // Service mới nhận id và request.
            var result = await _service.UpdateAsync(id, request);

            if (result == null)
            {
                return NotFound(new
                {
                    message = "Không tìm thấy Microcontroller."
                });
            }
            return Ok(result);
        }
        catch (ArgumentException ex)
        {
            return BadRequest(new {message = ex.Message});  
        }
        catch (InvalidOperationException ex)
        {
            return Conflict(new {message = ex.Message});
        }
    }

    // 8. ADMIN - CẤP / CHUYỂN QUYỀN MCU
    // PATCH /api/microcontroller/{id}/owner
    [HttpPatch("{id:int}/owner")]
    [Authorize(Roles = "Admin")]
    public async Task<IActionResult> Transfer(
        int id,
        [FromBody] TransferMicrocontrollerRequestDto request)
    {
        try
        {
            var result = await _service.TransferAsync(id, request.UserId);

            if (result == null)
            {
                return NotFound(new
                {
                    message = "Không tìm thấy Microcontroller."
                });
            }
            return Ok(result);
        }
        catch (ArgumentException ex)
        {
            return BadRequest(new {message = ex.Message});  
        }
        catch (InvalidOperationException ex)
        {
            return Conflict(new {message = ex.Message});
        }
    }

    // 9. ADMIN - XÓA MCU
    // DELETE /api/microcontroller/{id}
    [HttpDelete("{id:int}")]
    [Authorize(Roles = "Admin")]
    public async Task<IActionResult> Delete(int id)
    {
        try
        {
            // Service mới chỉ nhận id.
            bool deleted = await _service.DeleteAsync(id);

            if (!deleted)
            {
                return NotFound(new
                {
                    message = "Không tìm thấy Microcontroller."
                });
            }
            return NoContent();
        }
        catch (InvalidOperationException ex)
        {
            return Conflict(new { message = ex.Message });   
        }
    }
}
