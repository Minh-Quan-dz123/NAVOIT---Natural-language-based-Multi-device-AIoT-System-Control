using DeviceRegistry.Api.DTOs;
using DeviceRegistry.Api.Services;
using Microsoft.AspNetCore.Mvc;

namespace DeviceRegistry.Api.Controllers;
[ApiController]
[Route("api/[controller]")]
public class AuthController : ControllerBase
{

    private readonly AuthService _authService;

    
    public AuthController(AuthService authService)
    {
        _authService = authService;
    }

    // POST: /api/auth/register
    [HttpPost("register")]
    public async Task<IActionResult> Register(CreateUserRequestDto dto)
    {
        try
        {
            var result = await _authService.RegisterAsync(dto);
            return Ok(result);
        }
        catch (ArgumentException ex)
        {
            return BadRequest(new { message = ex.Message });
        }
    }

    // POST: /api/auth/login
    [HttpPost("login")]
    public async Task<IActionResult> Login(LoginDto dto)
    {
        var result = await _authService.LoginAsync(dto);

        if (result == null)
        {
            return Unauthorized(new
            {
                message = "Username hoặc password không chính xác."
            });
        }

        return Ok(result);
    }
}