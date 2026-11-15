
using DeviceRegistry.Api.DTOs;
using DeviceRegistry.Api.Services;

using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace DeviceRegistry.Api.Controllers;

[ApiController]
[Authorize]
[Route("api/[controller]")]
public class MicrocontrollerTypeController : ControllerBase
{
    private readonly MicrocontrollerTypeService _service;

    public MicrocontrollerTypeController(MicrocontrollerTypeService service)
    {
        _service = service;
    }

    // 1. GET ALL
    // GET /api/microcontrollertype
    [HttpGet]
    public async Task<IActionResult> GetAll()
    {
        var result = await _service.GetAllAsync();
        return Ok(result);
    }


    // 2. GET BY ID
    // GET /api/microcontrollertype/{id}
    [HttpGet("{id:int}")]
    public async Task<IActionResult> GetById(int id)
    {
        var result = await _service.GetByIdAsync(id);

        if (result == null)
        {
            return NotFound(new
            {
                message = "Không tìm thấy loại vi điều khiển."
            });
        }
        return Ok(result);
    }


    // 3. CREATE - chỉ admin được phép
    // POST /api/microcontrollertype
    [HttpPost]
    [Authorize(Roles = "Admin")]
    public async Task<IActionResult> Create([FromBody] CreateMicrocontrollerTypeRequestDto request)
    {
        try
        {
            var result = await _service.CreateAsync(request);
            return CreatedAtAction(
                nameof(GetById),
                new { id = result.Id },
                result
            );
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

    // 4. UPDATE - chỉ admin
    // PATCH /api/microcontrollertype/{id}
    [HttpPatch("{id:int}")]
    [Authorize(Roles = "Admin")]
    public async Task<IActionResult> Update(
        int id,
        [FromBody] UpdateMicrocontrollerTypeRequestDto request)
    {
        try
        {
            var result = await _service.UpdateAsync(id, request);
            if (result == null)
            {
                return NotFound(new
                {
                    message = "Không tìm thấy loại vi điều khiển."
                });
            }

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


    // 5. DELETE - ADMIN ONLY
    // DELETE /api/microcontrollertype/{id}
    [HttpDelete("{id:int}")]
    [Authorize(Roles = "Admin")]
    public async Task<IActionResult> Delete(int id)
    {
        try
        {
            bool deleted = await _service.DeleteAsync(id);
            if (!deleted)
            {
                return NotFound(new
                {
                    message = "Không tìm thấy loại vi điều khiển."
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
