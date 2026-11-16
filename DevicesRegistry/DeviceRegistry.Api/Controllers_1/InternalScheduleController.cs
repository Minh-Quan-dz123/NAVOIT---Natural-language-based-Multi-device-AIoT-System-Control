
using System.ComponentModel.DataAnnotations;

using DeviceRegistry.Api.DTOs;
using DeviceRegistry.Api.Services;

using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace DeviceRegistry.Api.Controllers;

// Dữ liệu NLP Server gửi sau ACK.
public class ConfirmScheduleRequestDto : UpsertScheduleRequestDto
{
    [Range(1, int.MaxValue)]
    public int UserId { get; set; }

    [Range(1, int.MaxValue)]
    public int MicrocontrollerId { get; set; }

    [Range(0, 39)]
    public int Gpio { get; set; }

    [Required]
    public string CommandId { get; set; } = "";
}

[ApiController]
[Authorize(Policy = "NlpServerOnly")]
[Route("api/internal/devices")]
public class InternalScheduleController : ControllerBase
{
    private readonly ScheduleServices _service;

    public InternalScheduleController(ScheduleServices service)
    {
        _service = service;
    }

    // Chỉ xác nhận và lưu lịch sau ACK của ESP32.
    [HttpPost("{deviceId:int}/schedule/confirm")]
    public async Task<IActionResult> ConfirmSchedule(
        int deviceId,
        [FromBody] ConfirmScheduleRequestDto request)
    {
        try
        {
            var result = await _service.ConfirmCreatedAsync(
                deviceId,
                request.UserId,
                request.MicrocontrollerId,
                request.Gpio,
                request.CommandId,
                request
            );

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



    // POST /api/internal/devices/{deviceId}/schedule/cancel-confirm
    // Chỉ xóa Schedule sau khi NLP Server đã nhận ACK hủy.
    [HttpPost("{deviceId:int}/schedule/cancel-confirm")]
    public async Task<IActionResult> ConfirmCancelSchedule(
        int deviceId,
        [FromBody] ConfirmCancelScheduleRequestDto request)
    {
        try
        {
            await _service.ConfirmCancelledAsync(
                deviceId,
                request.UserId,
                request.MicrocontrollerId,
                request.Gpio,
                request.ScheduleId,
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

}



public class ConfirmCancelScheduleRequestDto
{
    [Range(1, int.MaxValue)]
    public int UserId { get; set; }

    [Range(1, int.MaxValue)]
    public int MicrocontrollerId { get; set; }

    [Range(0, 39)]
    public int Gpio { get; set; }

    [Range(1, int.MaxValue)]
    public int ScheduleId { get; set; }

    [Required]
    public string CommandId { get; set; } = "";
}
