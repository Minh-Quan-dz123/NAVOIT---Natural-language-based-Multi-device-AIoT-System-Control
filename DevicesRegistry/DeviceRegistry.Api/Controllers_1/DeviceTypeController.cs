// Quản lý loại thiết bị
// DeviceType 1 --- N Device
using Microsoft.AspNetCore.Mvc;
using DeviceRegistry.Api.DTOs;
using DeviceRegistry.Api.Services;

[ApiController]
[Route("api/[controller]")]
public class DeviceTypeController : ControllerBase
{
    private readonly DeviceTypeService _service;

    public DeviceTypeController(DeviceTypeService service)
    {
        _service = service;
    }

    // thêm, sửa, xóa DeviceType
    // lấy DeviceType theo device_id
    // lấy tất cả devicetype trong hệ thống
}