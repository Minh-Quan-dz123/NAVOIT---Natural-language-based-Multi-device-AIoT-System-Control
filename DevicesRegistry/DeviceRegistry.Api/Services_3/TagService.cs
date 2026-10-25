
using System.Text.RegularExpressions;

using DeviceRegistry.Api.Data;
using DeviceRegistry.Api.DTOs;
using DeviceRegistry.Api.Models;

using Microsoft.EntityFrameworkCore;
using Npgsql;

namespace DeviceRegistry.Api.Services;

public class ManageTagsService
{
    private readonly AppDbContext _context;

    // 1. CONSTRUCTOR
    public ManageTagsService(AppDbContext context)
    {
        _context = context;
    }

    // 2. CHUẨN HÓA TAG
    private static string NormalizeTag(string? value)
    {
        if (string.IsNullOrWhiteSpace(value)) throw new ArgumentException("Tag không được để trống.");

        // Ví dụ:
        // "  Phòng   Con Gái  "
        // -> "phòng con gái"
        //
        // Giữ nguyên dấu tiếng Việt, chỉ chuẩn hóa
        // khoảng trắng và chữ hoa/chữ thường.
        var tag = Regex.Replace(value.Trim(), @"\s+"," ").ToLowerInvariant();

        if (tag.Length > 150)throw new ArgumentException("Tag không được vượt quá 150 ký tự.");

        return tag;
    }

    // 3. CHUYỂN TAGGROUP SANG DTO
    private static TagGroupResponseDto ToDto(TagGroup group)
    {
        return new TagGroupResponseDto
        {
            TagGroupId = group.Id,

            Tags = group.Tags
                .Select(t => t.Value)
                .OrderBy(t => t)
                .ToList()
        };
    }

    // 4. GET ALL TAGGROUPS BY USER

    public async Task<List<TagGroupResponseDto>> GetAllGroupsAsync(int userId)
    {
        var groups = await _context.TagGroups
            .AsNoTracking()
            .Include(g => g.Tags)
            .Where(g => g.UserId == userId)
            .OrderBy(g => g.Id)
            .ToListAsync();

        return groups.Select(ToDto).ToList();
    }

    // 5. GET TAGGROUPS OF A DEVICE
    public async Task<List<TagGroupResponseDto>?> GetDeviceTagsAsync(int deviceId, int userId)
    {
        // Kiểm tra Device có thuộc User hay không.
        var deviceExists = await _context.Devices
            .AnyAsync(d =>
                d.Id == deviceId &&
                d.UserId == userId
            );

        if (!deviceExists) return null;

        // Device -> DeviceTagGroup -> TagGroup -> Tags.
        //
        // Đồng thời kiểm tra TagGroup thuộc User,
        // tránh trả nhầm dữ liệu của User khác.
        var links = await _context.DeviceTagGroups
            .AsNoTracking()
            .Include(link => link.TagGroup)
                .ThenInclude(group => group.Tags)
            .Where(link =>
                link.DeviceId == deviceId &&
                link.TagGroup.UserId == userId
            )
            .ToListAsync();

        return links
            .Select(link => ToDto(link.TagGroup))
            .OrderBy(group => group.TagGroupId)
            .ToList();
    }

    // 6. REPLACE DEVICE TAGS

    // PUT /api/device/{deviceId}/tags
    //
    // Nhận danh sách tag đã được NLP trích xuất.
    //
    // Thuật toán:
    // 1. Kiểm tra Device thuộc User.
    // 2. Chuẩn hóa và loại tag trùng.
    // 3. Tìm các TagGroup có tag đã tồn tại.
    // 4. Mỗi tag mới tạo một TagGroup mới.
    // 5. Đồng bộ các liên kết DeviceTagGroup.
    //
    // Không xóa TagGroup khi bỏ liên kết Device.
    public async Task<List<TagGroupResponseDto>> ReplaceDeviceTagsAsync(
        int deviceId,
        int userId,
        CreateTagRequestDto request
    )
    {
        if (request.Tags == null || request.Tags.Count > 20)
            throw new ArgumentException(
                "Danh sách Tag không hợp lệ hoặc vượt quá 20 phần tử."
            );

        // 6.1. Chuẩn hóa tag.
        var tags = request.Tags
            .Select(NormalizeTag)
            .Distinct(StringComparer.Ordinal)
            .ToList();

        // 6.2. Tìm Device cùng các liên kết hiện tại.
        var device = await _context.Devices
            .Include(d => d.DeviceTagGroups)
            .FirstOrDefaultAsync(d =>
                d.Id == deviceId &&
                d.UserId == userId
            );

        if (device == null) throw new KeyNotFoundException("Không tìm thấy Device.");

        // 6.3. Tìm những tag đã tồn tại của User.
        //
        // Chỉ xét TagGroup thuộc User hiện tại.
        var existingTags = await _context.Tags
            .Where(t =>
                t.TagGroup.UserId == userId &&
                tags.Contains(t.Value)
            )
            .Select(t => new
            {
                t.Value,
                t.TagGroupId
            })
            .ToListAsync();

        // 6.4. Map: Tag -> TagGroupId.
        var tagToGroup = new Dictionary<string, int>(StringComparer.Ordinal);

        foreach (var tag in existingTags)
        {
            // Nếu dữ liệu cũ bị trùng tag ở hai nhóm khác nhau,
            // không tự ý chọn một nhóm bất kỳ.
            if (
                tagToGroup.TryGetValue(tag.Value, out var oldGroupId) &&
                oldGroupId != tag.TagGroupId
            )
            {
                throw new InvalidOperationException($"Tag '{tag.Value}' thuộc nhiều TagGroup.");
            }

            tagToGroup[tag.Value] = tag.TagGroupId;
        }

        // 6.5. Danh sách ID các nhóm đã tồn tại cần liên kết.
        var requiredGroupIds = new HashSet<int>();

        // Danh sách các nhóm mới.
        var newGroups = new List<TagGroup>();

        foreach (var tag in tags)
        {
            if (tagToGroup.TryGetValue(tag, out var groupId))
            {
                // Tag đã tồn tại -> dùng lại TagGroup.
                requiredGroupIds.Add(groupId);
            }
            else
            {
                // Tag chưa tồn tại -> tạo TagGroup riêng.
                //
                // Không gộp tất cả tag mới vào cùng nhóm,
                // vì chúng có thể mang ý nghĩa khác nhau.
                var group = new TagGroup
                {
                    UserId = userId,
                    CreatedAt = DateTime.UtcNow,

                    Tags = new List<Tag>
                    {
                        new Tag
                        {
                            Value = tag,
                            CreatedAt = DateTime.UtcNow
                        }
                    }
                };

                _context.TagGroups.Add(group);
                newGroups.Add(group);
            }
        }

        // 6.6. Xóa những liên kết cũ không còn được yêu cầu.
        //
        // Chỉ xóa DeviceTagGroup.
        // Không xóa các TagGroup và Tag tương ứng.
        var oldLinks = device.DeviceTagGroups.ToList();

        foreach (var link in oldLinks)
        {
            if (!requiredGroupIds.Contains(link.TagGroupId))
                _context.DeviceTagGroups.Remove(link);
        }

        // 6.7. Thêm liên kết với các TagGroup đã tồn tại.
        foreach (var groupId in requiredGroupIds)
        {
            bool alreadyLinked = oldLinks.Any(link => link.TagGroupId == groupId);

            if (!alreadyLinked)
            {
                _context.DeviceTagGroups.Add(
                    new DeviceTagGroup
                    {
                        DeviceId = deviceId,
                        TagGroupId = groupId
                    }
                );
            }
        }

        // 6.8. Liên kết các TagGroup mới với Device.
        foreach (var group in newGroups)
        {
            // Chưa có group.Id vì database chưa cấp ID.
            //
            // Gán navigation property TagGroup
            // để EF Core tự insert theo đúng thứ tự.
            _context.DeviceTagGroups.Add(
                new DeviceTagGroup
                {
                    DeviceId = deviceId,
                    TagGroup = group
                }
            );
        }

        // 6.9. Lưu database.
        //
        // EF Core mặc định sử dụng transaction cho
        // một SaveChanges có nhiều thao tác ghi,
        // tránh lưu nửa chừng danh sách liên kết.
        try
        {
            await _context.SaveChangesAsync();
        }
        catch (DbUpdateException ex) when (
            ex.InnerException is PostgresException pg &&
            pg.SqlState == PostgresErrorCodes.UniqueViolation
        )
        {
            throw new InvalidOperationException(
                "Có liên kết hoặc Tag bị trùng. Hãy tải lại dữ liệu.",
                ex
            );
        }

        return (await GetDeviceTagsAsync(deviceId, userId))!;
    }

    // 7. ADD ALIAS TO EXISTING TAGGROUP

    // POST /api/tag/aliases
    //
    // Ví dụ:
    // ExistingTag = "phòng bếp"
    // NewTag      = "nhà bếp"
    //
    // Nếu "phòng bếp" thuộc TagGroup 10,
    // tạo Tag "nhà bếp" trong TagGroup 10.
    public async Task<TagGroupResponseDto> AddAliasAsync(int userId,UpdateAliasRequestDto request)
    {
        var existingValue = NormalizeTag(request.ExistingTag);
        var newValue = NormalizeTag(request.NewTag);

        // 7.1. Tìm Tag gốc trong phạm vi User.
        var existingTag = await _context.Tags
            .Include(t => t.TagGroup)
                .ThenInclude(group => group.Tags)
            .FirstOrDefaultAsync(t =>
                t.Value == existingValue &&
                t.TagGroup.UserId == userId
            );

        if (existingTag == null) throw new KeyNotFoundException("Không tìm thấy Tag gốc.");

        var group = existingTag.TagGroup;

        // 7.2. Kiểm tra NewTag có tồn tại chưa.
        var duplicate = await _context.Tags
            .FirstOrDefaultAsync(t =>
                t.Value == newValue &&
                t.TagGroup.UserId == userId
            );

        if (duplicate != null)
        {
            // Nếu NewTag đã nằm trong cùng nhóm
            // thì không cần thêm lần nữa.
            if (duplicate.TagGroupId == group.Id)return ToDto(group);

            // Nếu nằm trong nhóm khác, không tự gộp
            // hai TagGroup vì có thể làm thay đổi
            // kết quả Device Resolution của nhiều Device.
            throw new InvalidOperationException("Tag mới đã thuộc một TagGroup khác.");
        }

        // 7.3. Thêm Tag mới vào nhóm đồng nghĩa.
        group.Tags.Add(new Tag
        {
            Value = newValue,
            CreatedAt = DateTime.UtcNow
        });

        try
        {
            await _context.SaveChangesAsync();
        }
        catch (DbUpdateException ex) when (
            ex.InnerException is PostgresException pg &&
            pg.SqlState == PostgresErrorCodes.UniqueViolation
        )
        {
            throw new InvalidOperationException(
                "Tag đã tồn tại trong nhóm.",
                ex
            );
        }

        return ToDto(group);
    }
}
