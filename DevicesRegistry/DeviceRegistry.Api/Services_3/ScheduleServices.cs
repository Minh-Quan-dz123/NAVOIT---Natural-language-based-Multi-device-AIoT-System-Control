
using DeviceRegistry.Api.Data;
using DeviceRegistry.Api.DTOs;
using DeviceRegistry.Api.Models;

using Microsoft.EntityFrameworkCore;
using Npgsql;

namespace DeviceRegistry.Api.Services;

public class ScheduleServices
{
    private readonly AppDbContext _context;

    // 1. CONSTRUCTOR
    public ScheduleServices(AppDbContext context)
    {
        _context = context;
    }

    // 2. CHUYỂN ENTITY SANG RESPONSE DTO
    private static ScheduleResponseDto ToDto(Schedule schedule)
    {
        return new ScheduleResponseDto
        {
            Id = schedule.Id,
            DeviceId = schedule.DeviceId,

            Action = schedule.Action,
            ScheduledDelay = schedule.Delay,
            Duration = schedule.Duration,

            ScheduledStartAt = schedule.ScheduledStartAt,
            ScheduledEndAt = schedule.ScheduledEndAt,

            SyncStatus = schedule.SyncStatus,
            CommandId = schedule.CommandId,

            CreatedAt = schedule.CreatedAt,
            UpdatedAt = schedule.UpdatedAt,
            AcknowledgedAt = schedule.AcknowledgedAt
        };
    }

    // 3. KIỂM TRA DỮ LIỆU SCHEDULE
    private static string ValidateSchedule(UpsertScheduleRequestDto dto)
    {
        // 3.1. Chuẩn hóa action.
        var action = dto.Action?.Trim().ToLowerInvariant();

        if (action != "on" && action != "off")
        {
            throw new ArgumentException("Action chỉ hỗ trợ 'on' hoặc 'off'.");
        }

        // 3.2. Kiểm tra các giá trị thời gian.
        // DTO đã có Range, nhưng vẫn kiểm tra tại
        // Service để bảo vệ cả những nơi gọi trực tiếp.
        if (dto.ScheduledDelay < 0)throw new ArgumentException("ScheduledDelay phải >= 0.");

        if (dto.Duration.HasValue && dto.Duration.Value <= 0) throw new ArgumentException("Duration phải lớn hơn 0.");

        // 3.3. Không cho dùng đồng thời hai kiểu
        // xác định thời điểm bắt đầu.
        if (dto.ScheduledDelay.HasValue && dto.ScheduledStartAt.HasValue)
        {
            throw new ArgumentException("Không sử dụng đồng thời " + "ScheduledDelay và ScheduledStartAt.");
        }

        // 3.4. Không sử dụng đồng thời hai kiểu
        // xác định thời điểm kết thúc.
        if (dto.Duration.HasValue &&dto.ScheduledEndAt.HasValue)
        {
            throw new ArgumentException("Không sử dụng đồng thời " + "Duration và ScheduledEndAt.");
        }

        // 3.5. Schedule phải có ít nhất một tham số
        // thời gian thực sự có hiệu lực.
        //
        // Nếu không có tham số thời gian thì đó là
        // lệnh ON/OFF tức thời, không phải Schedule.
        var hasTiming = dto.ScheduledDelay is > 0 ||
                        dto.Duration.HasValue ||
                        dto.ScheduledStartAt.HasValue ||
                        dto.ScheduledEndAt.HasValue;

        if (!hasTiming)
        {
            throw new ArgumentException(
                "Schedule phải có ít nhất một tham số thời gian. " +
                "ON/OFF tức thời phải dùng API điều khiển."
            );
        }

        // 3.6. Kiểm tra các Unix timestamp.
        var now = DateTimeOffset.UtcNow.ToUnixTimeSeconds();

        if (dto.ScheduledStartAt.HasValue && dto.ScheduledStartAt.Value <= now)
        {
            throw new ArgumentException("ScheduledStartAt phải ở tương lai.");
        }

        if (dto.ScheduledEndAt.HasValue && dto.ScheduledEndAt.Value <= now)
        {
            throw new ArgumentException("ScheduledEndAt phải ở tương lai.");
        }

        // 3.7. Tính mốc bắt đầu dự kiến để kiểm tra
        // thứ tự của ScheduledEndAt.
        //
        // Đây chỉ là phép kiểm tra dữ liệu.
        // Với ScheduledDelay, ESP tính độ trễ
        // từ lúc nhận MQTT command, không phải
        // từ thời điểm Registry lưu database.
        long expectedStart = dto.ScheduledStartAt ?? (now + (dto.ScheduledDelay ?? 0));

        if (dto.ScheduledEndAt.HasValue && dto.ScheduledEndAt.Value <= expectedStart)
        {
            throw new ArgumentException("ScheduledEndAt phải lớn hơn thời điểm bắt đầu.");
        }

        return action;
    }

    // 4. GET SCHEDULE BY DEVICE ID
    public async Task<ScheduleResponseDto?> GetByDeviceIdAsync(int deviceId, int userId)
    {
        // Schedule không có UserId riêng.
        //
        // Ta kiểm tra quyền sở hữu thông qua
        // quan hệ Schedule -> Device -> UserId.
        var schedule = await _context.Schedules
            .AsNoTracking()
            .FirstOrDefaultAsync(s =>
                s.DeviceId == deviceId &&
                s.Device.UserId == userId
            );

        if (schedule == null) return null;

        return ToDto(schedule);
    }

    // 5. CREATE / UPDATE SCHEDULE
    public async Task<ScheduleResponseDto> UpsertAsync(int deviceId, int userId, UpsertScheduleRequestDto dto)
    {
        // 5.1. Kiểm tra và chuẩn hóa dữ liệu.
        var action = ValidateSchedule(dto);

        // 5.2. Tìm Device thuộc User.
        //
        // Include Schedule để biết Device hiện tại
        // đã có lịch hay chưa.
        var device = await _context.Devices
            .Include(d => d.Schedule)
            .FirstOrDefaultAsync(d =>
                d.Id == deviceId &&
                d.UserId == userId
            );

        if (device == null)throw new KeyNotFoundException("Không tìm thấy Device.");

        // 5.3. Device phải có thông tin phần cứng
        // để về sau có thể gửi lịch xuống ESP.
        if (device.MicrocontrollerId == null || device.Gpio == null)
        {
            throw new InvalidOperationException("Device chưa được liên kết với Microcontroller và GPIO.");
        }

        // Không cho lập lịch trên cấu hình đang được
        // biết là lỗi hoặc sai lệch với phần cứng.
        //
        // Device đang pending CREATE_DEVICE_REQUEST
        // vẫn có thể lưu lịch chờ, nhưng NLP Server
        // phải chờ Device được đồng bộ trước khi gửi lịch.
        if (device.SyncStatus == "error" || device.SyncStatus == "out_of_sync")
        {
            throw new InvalidOperationException("Cấu hình Device chưa đồng bộ hợp lệ.");
        }

        var schedule = device.Schedule;
        var now = DateTime.UtcNow;

        // 5.4. Nếu đã có lịch, chỉ cho chỉnh sửa khi:
        //
        // - Lịch vẫn ở trạng thái pending.
        // - Chưa gắn command_id cho lần gửi MQTT.
        //
        // Không ghi đè lịch mà ESP có thể đang chạy.
        if (schedule != null)
        {
            bool canEdit =
                schedule.SyncStatus == "pending" &&
                schedule.CommandId == null;

            if (!canEdit)
            {
                throw new InvalidOperationException(
                    "Schedule đã được gửi, đang đồng bộ " +
                    "hoặc có trạng thái chưa xác định. " +
                    "Cần hoàn tất hoặc hủy lịch cũ trước khi thay thế."
                );
            }
        }

        // 5.5. Nếu chưa có Schedule thì tạo mới.
        if (schedule == null)
        {
            schedule = new Schedule
            {
                DeviceId = deviceId,
                CreatedAt = now
            };

            _context.Schedules.Add(schedule);
        }

        // 5.6. Gán thông tin lịch.
        schedule.Action = action;
        schedule.Delay = dto.ScheduledDelay;
        schedule.Duration = dto.Duration;

        schedule.ScheduledStartAt = dto.ScheduledStartAt;
        schedule.ScheduledEndAt = dto.ScheduledEndAt;

        // Lưu cấu hình mong muốn.
        // KHÔNG đánh dấu đã nhận ACK.
        schedule.SyncStatus = "pending";

        schedule.CommandId = null;
        schedule.AcknowledgedAt = null;
        schedule.UpdatedAt = now;

        // 5.7. Lưu database.
        try
        {
            await _context.SaveChangesAsync();
        }
        catch (DbUpdateException ex) when (
            ex.InnerException is PostgresException pg &&
            pg.SqlState == PostgresErrorCodes.UniqueViolation
        )
        {
            // Bảo vệ trường hợp hai request đồng thời
            // cùng tạo Schedule cho một Device.
            //
            // Quan hệ 1-1 phải có unique index DeviceId.
            throw new InvalidOperationException(
                "Device đã có Schedule. Hãy tải lại dữ liệu.",
                ex
            );
        }

        // Lúc này chỉ mới lưu database.
        // Chưa có MQTT command được gửi.
        return ToDto(schedule);
    }

    // 6. DELETE / CANCEL SCHEDULE
    // Trả về:
    // - null: Lịch chưa gửi MQTT, đã xóa khỏi database.
    // - DTO : Đang chờ gửi / xác nhận yêu cầu hủy.
    //
    // Trường hợp lịch đã gửi không được xóa ngay.
    public async Task<ScheduleResponseDto?> CancelAsync(int deviceId,int userId)
    {
        var device = await _context.Devices
            .Include(d => d.Schedule)
            .FirstOrDefaultAsync(d =>
                d.Id == deviceId &&
                d.UserId == userId
            );

        if (device == null)throw new KeyNotFoundException("Không tìm thấy Device.");

        var schedule = device.Schedule;

        if (schedule == null) throw new KeyNotFoundException("Device không có Schedule.");

        // 6.1. Trường hợp lịch pending nhưng chưa được
        // gắn command_id, tức là chưa đưa vào luồng gửi.
        //
        // Có thể xóa bản ghi trực tiếp vì lịch mới này
        // chưa được chuyển cho MQTT Handler.
        if (schedule.SyncStatus == "pending" && schedule.CommandId == null)
        {
            _context.Schedules.Remove(schedule);

            await _context.SaveChangesAsync();

            return null;
        }

        // 6.2. Trường hợp đã có CREATE/CONTROL command
        // đang chờ ACK.
        //
        // Không gửi CANCEL đè lên command đang chờ,
        // vì có thể dẫn tới thứ tự MQTT không mong muốn.
        if (schedule.SyncStatus == "pending")
        {
            throw new InvalidOperationException(
                "Schedule đang chờ phản hồi từ ESP. " +
                "Chưa thể hủy cho tới khi trạng thái được xác định."
            );
        }

        // 6.3. Đã yêu cầu hủy trước đó.
        // Trả về trạng thái hiện tại, không tạo yêu cầu trùng.
        if (schedule.SyncStatus == "cancel_pending")return ToDto(schedule);

        // 6.4. Muốn hủy trên firmware cần biết MCU/GPIO.
        if (device.MicrocontrollerId == null || device.Gpio == null)
        {
            // Không có tuyến gửi lệnh.
            // Không được báo đã hủy lịch thực tế.
            throw new InvalidOperationException(
                "Device không còn liên kết phần cứng. " +
                "Không thể xác nhận hủy lịch trên ESP."
            );
        }

        // 6.5. Ghi nhận yêu cầu hủy.
        //
        // Có thể đi từ acknowledged, failed hoặc unknown
        // sang cancel_pending.
        //
        // NLP Server sẽ gửi action = cancel_schedule.
        schedule.SyncStatus = "cancel_pending";

        // CommandId cũ không còn đại diện cho thao tác mới.
        // MQTT Handler sẽ đăng ký command_id của lệnh hủy.
        schedule.CommandId = null;
        schedule.UpdatedAt = DateTime.UtcNow;

        await _context.SaveChangesAsync();

        return ToDto(schedule);
    }

    // 7. ĐĂNG KÝ COMMAND ID CHO MQTT

    // Hàm nội bộ, KHÔNG expose cho User qua Controller.
    //
    // Trong đợt tích hợp NLP Server, thành phần điều phối
    // gọi hàm này qua API nội bộ đã xác thực trước khi
    // publish MQTT để gắn command_id cho thao tác.
    public async Task RegisterCommandAsync(int deviceId, string commandId)
    {
        if (string.IsNullOrWhiteSpace(commandId)) throw new ArgumentException("CommandId không được để trống.");

        var schedule = await _context.Schedules.FirstOrDefaultAsync(s => s.DeviceId == deviceId);

        if (schedule == null) throw new KeyNotFoundException("Không tìm thấy Schedule.");

        if (
            schedule.SyncStatus != "pending" &&
            schedule.SyncStatus != "cancel_pending"
        )
        {
            throw new InvalidOperationException("Schedule không ở trạng thái chờ đồng bộ.");
        }

        // Không cho một thao tác có hai command_id khác nhau.
        // Gọi lại cùng command_id thì chấp nhận để hỗ trợ retry.
        if (schedule.CommandId != null && schedule.CommandId != commandId)
        {
            throw new InvalidOperationException("Schedule đã có CommandId đang xử lý.");
        }

        schedule.CommandId = commandId;
        schedule.UpdatedAt = DateTime.UtcNow;

        await _context.SaveChangesAsync();
    }

    // 8. XỬ LÝ MQTT ACK
    // Hàm nội bộ, KHÔNG expose trực tiếp cho User.
    //
    // accepted = true chỉ khi firmware phản hồi rõ ràng
    // rằng đã chấp nhận hoặc hủy lịch thành công.
    //
    // Không coi việc publish MQTT thành công là ACK.
    //
    // Không dùng hàm này nếu response firmware hiện tại
    // chưa đủ thông tin để xác nhận thành công/thất bại.
    public async Task ApplyAcknowledgementAsync(int deviceId, string commandId,bool accepted)
    {
        var schedule = await _context.Schedules
            .FirstOrDefaultAsync(s => s.DeviceId == deviceId);

        if (schedule == null) throw new KeyNotFoundException("Không tìm thấy Schedule.");

        // Kiểm tra command_id để tránh ACK cũ
        // cập nhật nhầm Schedule mới.
        if (schedule.CommandId != commandId)
        {
            throw new InvalidOperationException("CommandId không khớp với thao tác đang chờ.");
        }

        if (
            schedule.SyncStatus != "pending" &&
            schedule.SyncStatus != "cancel_pending"
        )
        {
            throw new InvalidOperationException("Schedule không chờ xác nhận MQTT.");
        }

        var now = DateTime.UtcNow;

        // 8.1. Firmware báo từ chối hoặc thất bại.
        if (!accepted)
        {
            schedule.SyncStatus = "failed";
            schedule.UpdatedAt = now;

            await _context.SaveChangesAsync();
            return;
        }

        // 8.2. Xác nhận tạo / thiết lập lịch.
        if (schedule.SyncStatus == "pending")
        {
            schedule.SyncStatus = "acknowledged";

            // Thời điểm ESP xác nhận tiếp nhận lịch,
            // KHÔNG phải thời điểm thực thi lịch.
            schedule.AcknowledgedAt = now;
            schedule.UpdatedAt = now;

            await _context.SaveChangesAsync();
            return;
        }

        // 8.3. Xác nhận hủy lịch.
        if (schedule.SyncStatus == "cancel_pending")
        {
            // Chỉ sau ACK hủy hợp lệ mới xóa
            // Schedule hiện hành khỏi Registry.
            //
            // Theo firmware, hủy lịch không làm thay đổi
            // trạng thái ON/OFF hiện tại.
            _context.Schedules.Remove(schedule);

            await _context.SaveChangesAsync();
        }
    }
}
