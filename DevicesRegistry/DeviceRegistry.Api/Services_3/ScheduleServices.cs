
using DeviceRegistry.Api.Data;
using DeviceRegistry.Api.DTOs;
using DeviceRegistry.Api.Models;

using Microsoft.EntityFrameworkCore;
using Npgsql;

namespace DeviceRegistry.Api.Services;

public class ScheduleServices
{
    private readonly AppDbContext _context;

    public ScheduleServices(AppDbContext context)
    {
        _context = context;
    }

    // 1. CHUYỂN SCHEDULE SANG RESPONSE DTO
    private static ScheduleResponseDto ToDto(Schedule schedule)
    {
        long now = DateTimeOffset.UtcNow.ToUnixTimeSeconds();

        return new ScheduleResponseDto
        {
            Id = schedule.Id,
            DeviceId = schedule.DeviceId,
            Action = schedule.Action,

            ScheduledDelay = schedule.Delay,
            Duration = schedule.Duration,
            ScheduledStartAt = schedule.ScheduledStartAt,
            ScheduledEndAt = schedule.ScheduledEndAt,

            ExpiresAt = schedule.ExpiresAt,
            IsExpired = now >= schedule.ExpiresAt,

            CreatedAt = schedule.CreatedAt,
            UpdatedAt = schedule.UpdatedAt
        };
    }

    // 2. KIỂM TRA LỊCH VÀ TÍNH EXPIRES AT
    private static (string Action, long ExpiresAt) ValidateAndCalculate(UpsertScheduleRequestDto request,long commandSentAt)
    {
        if (commandSentAt <= 0)
        {
            throw new ArgumentException("Thời điểm gửi lệnh không hợp lệ.");
        }

        string action = request.Action?.Trim().ToLowerInvariant()?? string.Empty;

        if (action != "on" && action != "off")
        {
            throw new ArgumentException("Action chỉ hỗ trợ on hoặc off.");
        }

        int? delay = request.ScheduledDelay;
        int? duration = request.Duration;
        long? start = request.ScheduledStartAt;
        long? end = request.ScheduledEndAt;

        if (delay < 0) throw new ArgumentException("Delay không được âm.");

        if (duration.HasValue && duration.Value <= 0)
            throw new ArgumentException("Duration phải lớn hơn 0.");

        // Giữ nguyên những tổ hợp đang được NLP hỗ trợ.
        if (delay.HasValue && start.HasValue)
        {
            throw new ArgumentException("Không dùng đồng thời Delay và StartAt.");
        }

        if (duration.HasValue && end.HasValue)
        {
            throw new ArgumentException("Không dùng đồng thời Duration và EndAt.");
        }

        bool hasTiming =
            delay is > 0 ||
            duration.HasValue ||
            start.HasValue ||
            end.HasValue;

        if (!hasTiming)
        {
            throw new ArgumentException("Schedule phải có ít nhất một tham số thời gian.");
        }

        // Giữ quy tắc đã áp dụng trong NLP hiện tại.
        if (end.HasValue && !delay.HasValue && !start.HasValue)
        {
            throw new ArgumentException("Cần chỉ định thời điểm bắt đầu khi dùng EndAt.");
        }

        if (start.HasValue && start.Value <= commandSentAt)
        {
            throw new ArgumentException("ScheduledStartAt phải sau thời điểm gửi lệnh.");
        }

        if (end.HasValue && end.Value <= commandSentAt)
        {
            throw new ArgumentException("ScheduledEndAt phải sau thời điểm gửi lệnh.");
        }

        // Thời điểm bắt đầu thực tế theo yêu cầu.
        long effectiveStart =start ?? (commandSentAt + (delay ?? 0));

        if (end.HasValue && end.Value <= effectiveStart)
        {
            throw new ArgumentException("ScheduledEndAt phải lớn hơn thời điểm bắt đầu.");
        }

        // EndAt có độ ưu tiên cao nhất.
        // Nếu không có EndAt, hết hạn khi bắt đầu + Duration.
        // Nếu không có Duration, hết hạn tại thời điểm bắt đầu.
        long expiresAt = end?? (effectiveStart + (duration ?? 0));

        return (action, expiresAt);
    }

    // 3. XEM SCHEDULE CỦA DEVICE THUỘC USER
    public async Task<ScheduleResponseDto?> GetByDeviceIdAsync(
        int deviceId,
        int userId)
    {
        var schedule = await _context.Schedules
            .AsNoTracking()
            .FirstOrDefaultAsync(s =>
                s.DeviceId == deviceId &&
                s.Device.UserId == userId
            );

        if (schedule == null) return null;

            
        return ToDto(schedule);
    }

    // 4. LƯU SCHEDULE SAU KHI NLP NHẬN ACK TẠO LỊCH
    public async Task<ScheduleResponseDto> ConfirmCreatedAsync(
        int deviceId,
        int userId,
        int microcontrollerId,
        int gpio,
        string commandId,
        long commandSentAt,
        UpsertScheduleRequestDto request)
    {
        if (string.IsNullOrWhiteSpace(commandId))
        {
            throw new ArgumentException("CommandId không hợp lệ.");
        }

        var (action, expiresAt) = ValidateAndCalculate(request, commandSentAt);

        var device = await _context.Devices
            .Include(d => d.Schedule)
            .FirstOrDefaultAsync(d =>
                d.Id == deviceId &&
                d.UserId == userId
            );

        if (device == null)
            throw new KeyNotFoundException("Không tìm thấy Device.");

        // Phải đúng MCU/GPIO mà NLP vừa điều khiển.
        if (device.MicrocontrollerId != microcontrollerId ||
            device.Gpio != gpio ||
            device.SyncStatus != "synced")
        {
            throw new InvalidOperationException("Liên kết MCU/GPIO không còn khớp.");
        }

        // Một Device chỉ có tối đa một Schedule.
        if (device.Schedule != null)
        {
            throw new InvalidOperationException("Device đã có Schedule. Cần xử lý lịch cũ trước.");
        }

        DateTime now = DateTime.UtcNow;

        var schedule = new Schedule
        {
            DeviceId = deviceId,
            Action = action,

            Delay = request.ScheduledDelay,
            Duration = request.Duration,
            ScheduledStartAt = request.ScheduledStartAt,
            ScheduledEndAt = request.ScheduledEndAt,

            ExpiresAt = expiresAt,

            CreatedAt = now,
            UpdatedAt = now
        };

        _context.Schedules.Add(schedule);

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
                "Device đã có Schedule. Cần tải lại dữ liệu.",
                ex
            );
        }

        return ToDto(schedule);
    }

    // 5. XÓA SCHEDULE SAU KHI NLP NHẬN ACK HỦY LỊCH
    public async Task ConfirmCancelledAsync(
        int deviceId,
        int userId,
        int microcontrollerId,
        int gpio,
        int scheduleId,
        string commandId)
    {
        if (string.IsNullOrWhiteSpace(commandId))
        {
            throw new ArgumentException( "CommandId không hợp lệ.");
        }

        var device = await _context.Devices
            .AsNoTracking()
            .FirstOrDefaultAsync(d =>
                d.Id == deviceId &&
                d.UserId == userId
            );

        if (device == null)
            throw new KeyNotFoundException("Không tìm thấy Device.");

        // Không cho ACK cũ xóa lịch sau khi đổi binding.
        if (device.MicrocontrollerId != microcontrollerId ||
            device.Gpio != gpio ||
            device.SyncStatus != "synced")
        {
            throw new InvalidOperationException("Liên kết MCU/GPIO không còn khớp.");
        }

        // Xóa theo đúng ScheduleId đã đọc trước khi gửi MQTT.
        // Không được xóa nhầm một lịch mới của cùng Device.
        int deleted = await _context.Schedules
            .Where(s =>
                s.Id == scheduleId &&
                s.DeviceId == deviceId
            )
            .ExecuteDeleteAsync();

        if (deleted == 0)
        {
            throw new InvalidOperationException("Schedule không còn khớp. Cần đối soát.");
        }
    }
}
