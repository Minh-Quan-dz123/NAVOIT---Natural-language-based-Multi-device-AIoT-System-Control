// Tạo, xem, sửa, xóa user
using DeviceRegistry.Api.DTOs;
using DeviceRegistry.Api.Services;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Authorization;


namespace DeviceRegistry.Api.Controllers;

[Authorize]
[ApiController]
[Route("api/[controller]")]
public class UserController : ControllerBase
{
    private readonly UsersService _userService;

    public UserController(UsersService service)
    {
        _userService = service;
    }

    // 1. Tạo User
    // POST: /api/user
    [HttpPost]
    public async Task<IActionResult> Create(CreateUserRequestDto request)
    {
        try
        {
            var result = await _userService.CreateUserAsync(request);
            return CreatedAtAction(nameof(GetById), new { id = result.Id },result);
        }
        catch (ArgumentException ex)
        {
            return BadRequest(new { message = ex.Message });
        }
    }

    // 2. Cập nhật toàn bộ thông tin được phép sửa
    // PUT: /api/user/{id}
    [HttpPut("{id:int}")]
    public async Task<IActionResult> Update(int id, [FromBody] UpdateUserRequestDto request)
    {
        try
        {
            var result = await _userService.UpdateUserAsync(id, request);

            if (result == null) return NotFound(new { message = "Không tìm thấy User." });

            return Ok(result);
        }
        catch (ArgumentException ex)
        {
            return BadRequest(new { message = ex.Message });
        }
    }
    

    // 3. Xóa User
    // DELETE: /api/user/{id}
    [HttpDelete("{id:int}")]
    public async Task<IActionResult> Delete(int id)
    {
        var deleted = await _userService.DeleteUserAsync(id);

        if (!deleted) return NotFound(new { message = "Không tìm thấy User." });

        return NoContent();
    }

    // 4.1. Lấy thông tin một User
    // GET: /api/user/{id}
    [HttpGet("{id:int}")]
    public async Task<IActionResult> GetById(int id)
    {
        var result = await _userService.GetUserByIdAsync(id);

        if (result == null) return NotFound(new { message = "Không tìm thấy User." });

        return Ok(result);
    }

    // 4.2. Lấy thông tin User theo Username
    // GET: /api/user/username/{username}
    [HttpGet("username/{username}")]
    public async Task<IActionResult> GetByUsername(string username)
    {
        var result = await _userService.GetUserByUsernameAsync(username);

        if (result == null)
            return NotFound(new { message = "Không tìm thấy User." });

        return Ok(result);
    }

    // 4.3. lấy danh sách User
    // GET: /api/user
    [HttpGet]
    public async Task<IActionResult> GetAll()
    {
        var result = await _userService.GetAllUsersAsync();
        return Ok(result);
    }

    // 5. Đổi mật khẩu
    [HttpPut("{id:int}/password")]
    public async Task<IActionResult> ChangePassword(int id, [FromBody] ChangePasswordRequestDto request)
    {
        try
        {
            var changed = await _userService.ChangePasswordAsync(id, request);
            if (!changed) return NotFound(new { message = "Không tìm thấy User." });

            return NoContent();
        }
        catch (UnauthorizedAccessException ex)
        {
            return Unauthorized(new { message = ex.Message });
        }
        catch (ArgumentException ex)
        {
            return BadRequest(new { message = ex.Message });
        }
    }
}