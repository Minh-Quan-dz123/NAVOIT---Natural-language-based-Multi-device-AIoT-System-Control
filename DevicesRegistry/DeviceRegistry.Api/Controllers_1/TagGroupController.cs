// Controller này cho phép người dùng xem các TagGroup đã được hệ thống tạo.
using System.Security.Claims;

using DeviceRegistry.Api.Services;

using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace DeviceRegistry.Api.Controllers;

[ApiController]
[Authorize]
[Route("api/taggroup")]
public class TagGroupController : ControllerBase
{
    private readonly ManageTagsService _service;

    // 1. CONSTRUCTOR
    public TagGroupController(ManageTagsService service)
    {
        _service = service;
    }

    // 2. GET ALL TAGGROUPS
    // GET /api/taggroup

    [HttpGet]
    public async Task<IActionResult> GetAll()
    {
        // Lấy UserId từ JWT.
        var userIdString = User.FindFirst(ClaimTypes.NameIdentifier)?.Value;

        if (!int.TryParse(userIdString, out var userId) || userId <= 0)
        {
            return Unauthorized();
        }

        // Chỉ lấy các TagGroup thuộc User này.
        var result = await _service.GetAllGroupsAsync(userId);

        return Ok(result);
    }
}
