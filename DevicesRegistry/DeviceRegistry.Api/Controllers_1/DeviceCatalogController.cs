
using System.Security.Claims;

using DeviceRegistry.Api.Data;
using DeviceRegistry.Api.DTOs;

using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;

namespace DeviceRegistry.Api.Controllers;

[ApiController]
[Authorize]
[Route("api/device/catalog")]
public class DeviceCatalogController : ControllerBase
{
    private readonly AppDbContext _context;

    // 1. CONSTRUCTOR
    public DeviceCatalogController(AppDbContext context)
    {
        _context = context;
    }

    // ==========================================
    // 2. GET DEVICE CATALOG
    // GET /api/device/catalog
    // ==========================================

    [HttpGet]
    public async Task<IActionResult> GetCatalog()
    {
        // 2.1. Lấy UserId từ JWT.
        var userIdString = User.FindFirst(ClaimTypes.NameIdentifier)?.Value;

        if (!int.TryParse(userIdString, out var userId)|| userId <= 0)
        {
            return Unauthorized();
        }

        // 2.2. Lấy tất cả Device của User.
        //
        // Include DeviceType để lấy tên loại thiết bị.
        // Include Microcontroller để lấy MAC, Type.
        //
        // Include DeviceTagGroups -> TagGroup -> Tags
        // để lấy các nhóm tag đồng nghĩa.
        //
        // AsNoTracking vì API chỉ đọc database.
        var devices = await _context.Devices
            .AsNoTracking()
            .Where(d => d.UserId == userId)
            .Include(d => d.DeviceType)
            .Include(d => d.Microcontroller)
            .Include(d => d.DeviceTagGroups)
                .ThenInclude(dtg => dtg.TagGroup)
                    .ThenInclude(tg => tg.Tags)
            .AsSplitQuery()
            .OrderBy(d => d.Id)
            .ToListAsync();

        // 2.3. Chuyển Entity sang DTO.
        //
        // Không trả trực tiếp Entity vì có thể
        // gây vòng lặp serialization giữa
        // các navigation properties.
        var result = devices.Select(d => new DeviceCatalogDto
        {
            DeviceId = d.Id,

            DeviceName = d.DeviceName,

            DeviceType = d.DeviceType.TypeName,

            MicrocontrollerId = d.MicrocontrollerId,

            MicrocontrollerType = d.Microcontroller?.Type,

            MacAddress = d.Microcontroller?.MacAddress,

            Gpio = d.Gpio,

            CurrentStatus = d.CurrentStatus,

            SyncStatus = d.SyncStatus,

            // Giữ cấu trúc từng TagGroup riêng biệt.
            //
            // NLP Server cần biết các tag nào
            // được coi là đồng nghĩa.
            //
            // Chỉ lấy nhóm thuộc User hiện tại.
            TagGroups = d.DeviceTagGroups
                .Where(link => link.TagGroup.UserId == userId)
                .OrderBy(link => link.TagGroupId)
                .Select(link => link.TagGroup.Tags
                    .OrderBy(t => t.Value)
                    .Select(t => t.Value)
                    .ToList()
                )
                .ToList()

        }).ToList();

        return Ok(new
        {
            DeviceCount = result.Count,
            Devices = result
        });
    }
}
