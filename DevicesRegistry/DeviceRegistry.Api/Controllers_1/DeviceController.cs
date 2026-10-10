// Quản lý thiết bị
using Microsoft.AspNetCore.Mvc;
using DeviceRegistry.Api.DTOs;
using DeviceRegistry.Api.Services;

namespace DeviceRegistry.Api.Controllers;

[ApiController]
[Route("api/[controller]")]
public class DeviceController:ControllerBase
{// POST /api/device/resolve
    // inject _resolutionService
    private readonly DeviceResolutionService _resolutionService;
    public DeviceController(DeviceResolutionService resolutionService)
    {
        _resolutionService = resolutionService;
    }

    // 1. ánh xạ tìm device từ các tag 
    [HttpPost("resolve")]
    public async Task<IActionResult> Resolve( [FromBody] DeviceResolutionRequestDto request)
    {
        // TODO: 
        // 1. Gọi DeviceResolutionService
        // 2. nếu ko tìm thấy device thì trả HTTP 404
        // 3. nếu có thì trả 200 và DeviceResolutionResponseDto
        return Ok();
        
    }

// User 1 --- N Device
// Microcontroller 1 --- N Device
// DeviceType 1 --- N Device

    // 2. thêm device cho userId
    // 3. thêm device cho espId
    // 4. lấy list deviceId của userId
    // 5. lấy list deviceId của espId
    // 6. xóa deviceId
    // 7. đổi DeviceType của Devie
    // 8. lấy device infor theo device Id
    // 9. update infor của device

}