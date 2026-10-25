
using DeviceRegistry.Api.DTOs;
using DeviceRegistry.Api.Services;

using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace DeviceRegistry.Api.Controllers;

[ApiController]
[Authorize]
[Route("api/[controller]")]
public class DeviceTypeController : ControllerBase
{
    private readonly DeviceTypeService _service;

    // 1. CONSTRUCTOR

    public DeviceTypeController(DeviceTypeService service)
    {
        _service = service;
    }

    // 2. GET ALL DEVICE TYPES
    // GET /api/devicetype
    [HttpGet]
    public async Task<IActionResult> GetAll()
    {
        var result = await _service.GetAllAsync();
        return Ok(result);
    }

    // 3. GET DEVICE TYPE BY ID
    // GET /api/devicetype/{id}

    [HttpGet("{id:int}")]
    public async Task<IActionResult> GetById(int id)
    {
        var result = await _service.GetByIdAsync(id);

        if (result == null)return NotFound(new { message = "Không tìm thấy DeviceType."});

        return Ok(result);
    }

    // 4. CREATE DEVICE TYPE
    // POST /api/devicetype
    [HttpPost]
    public async Task<IActionResult> Create([FromBody] CreateDeviceTypeRequestDto request)
    {
        try
        {
            var result = await _service.CreateAsync(request);

            // HTTP 201 Created.
            // Trả về Location của DeviceType mới.
            return CreatedAtAction(nameof(GetById), new { id = result.Id }, result);
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

    // 5. UPDATE DEVICE TYPE
    // PATCH /api/devicetype/{id}

    [HttpPatch("{id:int}")]
    public async Task<IActionResult> Update(int id,[FromBody] UpdateDeviceTypeRequestDto request)
    {
        try
        {
            var result = await _service.UpdateAsync(id, request);

            if (result == null)return NotFound(new{ message = "Không tìm thấy DeviceType."});

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

    // 6. DELETE DEVICE TYPE
    // DELETE /api/devicetype/{id}

    [HttpDelete("{id:int}")]
    public async Task<IActionResult> Delete(int id)
    {
        try
        {
            var deleted = await _service.DeleteAsync(id);

            if (!deleted)return NotFound(new {message = "Không tìm thấy DeviceType."});

            // Xóa thành công, không cần response body.
            return NoContent();
        }
        catch (InvalidOperationException ex)
        {
            return Conflict(new { message = ex.Message });
        }
    }
}
