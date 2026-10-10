// Quản lý vi điều khiển
using Microsoft.AspNetCore.Mvc;
using DeviceRegistry.Api.DTOs;
using DeviceRegistry.Api.Services;

namespace DeviceRegistry.Api.Controllers;

// User 1 --- N Microcontroller
[ApiController]
[Route("api/[controller]")]
public class MicrocontrollerController:ControllerBase
{
    private readonly MicrocontrollerService _service;
    public MicrocontrollerController(MicrocontrollerService x)
    {
        _service = x;
    }

    // 1. thêm microController
    // 2. 
}