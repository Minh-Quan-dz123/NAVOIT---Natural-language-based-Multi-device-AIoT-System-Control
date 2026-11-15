
using DeviceRegistry.Api.Data;

using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;

namespace DeviceRegistry.Api.Controllers;

[ApiController]
[Authorize(Roles = "Admin")]
[Route("api/admin/users")]
public class AdminUsersController : ControllerBase
{
    private readonly AppDbContext _context;

    public AdminUsersController(AppDbContext context)
    {
        _context = context;
    }

    // GET /api/admin/users/options
    // Danh sách tài khoản User để Admin cấp MCU.
    [HttpGet("options")]
    public async Task<IActionResult> GetUserOptions()
    {
        var users = await _context.Users
            .AsNoTracking()
            .Where(u => u.Role == "User")
            .OrderBy(u => u.Username)
            .Select(u => new
            {
                u.Id,
                u.Username
            })
            .ToListAsync();

        return Ok(users);
    }
}
