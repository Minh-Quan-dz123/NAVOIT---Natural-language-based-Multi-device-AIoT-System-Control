using DeviceRegistry.Api.DTOs;
using DeviceRegistry.Api.Data;
using DeviceRegistry.Api.Models;
using Microsoft.EntityFrameworkCore;
using Npgsql;

namespace DeviceRegistry.Api.Services;
public class DeviceService
{
    // TODO: Inject AppDbContext 
    private readonly AppDbContext _context;
    public DeviceService(AppDbContext context)
    {
        _context = context;
    }

    // 2. QUERY DÙNG CHUNG
    private IQueryable<DeviceResponseDto> QueryDevices(int userId)
    {
        // Select trực tiếp sang DTO.
        // EF Core sẽ truy vấn các bảng liên quan
        // để lấy DeviceType và Microcontroller.
        //
        // Không cần Include nếu chỉ lấy dữ liệu
        // bằng Select 
        return _context.Devices
            .AsNoTracking()
            .Where(d => d.UserId == userId)
            .Select(d => new DeviceResponseDto
            {
                Id = d.Id,
                DeviceName = d.DeviceName,
                Description = d.Description,

                DeviceTypeId = d.DeviceTypeId,
                DeviceTypeName = d.DeviceType.TypeName,

                MicrocontrollerId = d.MicrocontrollerId,

                MicrocontrollerType = d.Microcontroller != null? d.Microcontroller.Type: null,

                MacAddress = d.Microcontroller != null ? d.Microcontroller.MacAddress: null,

                Gpio = d.Gpio,

                CurrentStatus = d.CurrentStatus,
                StatusUpdatedAt = d.StatusUpdatedAt,
                SyncStatus = d.SyncStatus,
                CreatedAt = d.CreateAt
            });
    }

   
    // 3. GET ALL DEVICES BY USER
    public async Task<List<DeviceResponseDto>> GetAllByUserIdAsync(int userId)
    {
        return await QueryDevices(userId)
            .OrderByDescending(d => d.Id)
            .ToListAsync();
    }

    // 4. GET DEVICE BY ID
    public async Task<DeviceResponseDto?> GetByIdAsync(int id, int userId)
    {
        // Chỉ tìm Device thuộc đúng User.
        return await QueryDevices(userId).FirstOrDefaultAsync(d => d.Id == id);
    }

    // 5. GET UNASSIGNED DEVICES
    public async Task<List<DeviceResponseDto>> GetUnassignedAsync(int userId)
    {
        // Device chưa liên kết MCU có MicrocontrollerId = null.
        //
        // Lưu ý: Gpio có thể vẫn chứa chân GPIO cũ
        // nếu trước đó MCU đã bị xóa khỏi database.
        return await QueryDevices(userId)
            .Where(d => d.MicrocontrollerId == null)
            .OrderByDescending(d => d.Id)
            .ToListAsync();
    }

    // 6. CREATE DEVICE
    public async Task<DeviceResponseDto> CreateAsync(int userId,CreateDeviceRequestDto dto)
    {
        // 6.1. Kiểm tra loại thiết bị.
        var deviceTypeExists = await _context.DeviceTypes.AnyAsync(dt => dt.Id == dto.DeviceTypeId);

        if (!deviceTypeExists)throw new ArgumentException("DeviceType không tồn tại.");

        // 6.2. Kiểm tra MCU và GPIO.
        //
        // Khi tạo Device, hai thông tin này phải
        // cùng có giá trị hoặc cùng null.
        //
        // Trường hợp một bên null, một bên có giá trị
        // được xem là cấu hình chưa hợp lệ.
        if (dto.MicrocontrollerId.HasValue != dto.Gpio.HasValue)
        {
            throw new ArgumentException("MicrocontrollerId và Gpio phải cùng có giá trị hoặc cùng null.");
        }

        if (dto.Gpio.HasValue && dto.Gpio.Value < 0)throw new ArgumentException("GPIO không hợp lệ.");

        if (dto.MicrocontrollerId.HasValue)
        {
            int mcuId = dto.MicrocontrollerId.Value;
            int gpio = dto.Gpio!.Value;

            // 6.3. Kiểm tra Microcontroller thuộc User.
            var mcu = await _context.Microcontrollers
                .AsNoTracking()
                .FirstOrDefaultAsync(m =>
                    m.Id == mcuId &&
                    m.UserId == userId
                );

            if (mcu == null) throw new ArgumentException("Microcontroller không tồn tại hoặc không thuộc User.");

            // 6.4. Kiểm tra chân GPIO chưa có Device sử dụng.
            var gpioUsed = await _context.Devices
                .AnyAsync(d =>
                    d.MicrocontrollerId == mcuId &&
                    d.Gpio == gpio
                );

            if (gpioUsed)throw new InvalidOperationException("GPIO này đã được một Device khác sử dụng.");

            // 6.5. Firmware ESP32 hiện tại chỉ quản lý
            // tối đa 6 DeviceTask trên một vi điều khiển.
            //
            // Đây là giới hạn của firmware ESP32 hiện tại,
            // không áp dụng cho tất cả loại MCU.
            if (mcu.Type.Equals("esp32", StringComparison.OrdinalIgnoreCase))
            {
                var deviceCount = await _context.Devices.CountAsync(d => d.MicrocontrollerId == mcuId);

                if (deviceCount >= 6) throw new InvalidOperationException("ESP32 hiện tại chỉ hỗ trợ tối đa 6 Device.");
            }

            // TODO:
            // Kiểm tra GPIO có hỗ trợ OUTPUT trên board thực tế.
            // Không phải GPIO nào cũng dùng làm output được.
        }

        // 6.6. Tạo Device.
        var device = new Device
        {
            UserId = userId,
            DeviceTypeId = dto.DeviceTypeId,

            MicrocontrollerId = dto.MicrocontrollerId,
            Gpio = dto.Gpio,

            DeviceName = string.IsNullOrWhiteSpace(dto.DeviceName) ? null : dto.DeviceName.Trim(),

            Description = string.IsNullOrWhiteSpace(dto.Description)? null: dto.Description.Trim(),

            CreateAt = DateTime.UtcNow,

            // Chưa có báo cáo trạng thái từ firmware.
            CurrentStatus = "UNKNOWN",
            StatusUpdatedAt = null,

            // Nếu chưa gắn MCU: unassigned.
            // Nếu có MCU: cần đồng bộ CREATE_DEVICE_REQUEST.
            //
            // pending KHÔNG có nghĩa MQTT đã được gửi.
            SyncStatus = dto.MicrocontrollerId.HasValue ? "pending": "unassigned"
        };

        _context.Devices.Add(device);

        try
        {
            await _context.SaveChangesAsync();
        }
        catch (DbUpdateException ex) when (
            ex.InnerException is PostgresException pg &&
            pg.SqlState == PostgresErrorCodes.UniqueViolation
        )
        {
            // Unique index trong AppDbContext là lớp bảo vệ
            // cuối cùng nếu hai request đồng thời cùng chọn GPIO.
            throw new InvalidOperationException("GPIO đã được sử dụng hoặc dữ liệu bị trùng.", ex );
        }

        // 6.7. Trả DTO đã lưu.
        // Id được PostgreSQL cấp sau SaveChangesAsync().
        return (await GetByIdAsync(device.Id, userId))!;
    }

    // ====

    // 7. UPDATE DEVICE INFORMATION
    public async Task<DeviceResponseDto?> UpdateAsync(int id, int userId, UpdateDeviceRequestDto dto)
    {
        // 7.1. Lấy Device thuộc User.
        var device = await _context.Devices
            .FirstOrDefaultAsync(d =>
                d.Id == id &&
                d.UserId == userId
            );

        if (device == null) return null;

        // 7.2. Kiểm tra request có trường cần cập nhật không.
        if (dto.DeviceName == null && dto.Description == null && dto.DeviceTypeId == null)
        {
            throw new ArgumentException("Không có thông tin nào cần cập nhật.");
        }

        // 7.3. Cập nhật tên.
        if (dto.DeviceName != null)
        {
            var newName = string.IsNullOrWhiteSpace(dto.DeviceName) ? null : dto.DeviceName.Trim();

            // Firmware hiện đang lưu device_name.
            // Chưa có UPDATE_DEVICE_REQUEST để đổi tên.
            //
            // Vì vậy không đổi tên của Device đã gắn MCU
            // nếu tên mới khác tên hiện tại.
            if (device.MicrocontrollerId != null &&newName != device.DeviceName)
            {
                throw new InvalidOperationException(
                    "Chưa hỗ trợ đổi tên Device đang gắn MCU. " +
                    "Cần thực hiện qua quy trình đồng bộ phần cứng."
                );
            }

            device.DeviceName = newName;
        }

        // 7.4. Cập nhật mô tả.
        if (dto.Description != null)
        {
            // Description chỉ lưu trên Registry,
            // không cần gửi xuống firmware.
            device.Description = string.IsNullOrWhiteSpace(dto.Description)? null : dto.Description.Trim();
        }

        // 7.5. Cập nhật DeviceType.
        if (dto.DeviceTypeId.HasValue)
        {
            int newTypeId = dto.DeviceTypeId.Value;

            if (newTypeId != device.DeviceTypeId)
            {
                var typeExists = await _context.DeviceTypes.AnyAsync(dt => dt.Id == newTypeId);

                if (!typeExists) throw new ArgumentException( "DeviceType không tồn tại.");

                // Không thay đổi loại của Device đã gắn MCU
                // vì DeviceTask có thể đang sử dụng loại cũ.
                if (device.MicrocontrollerId != null) throw new InvalidOperationException("Không thể đổi DeviceType khi Device đang gắn MCU.");

                device.DeviceTypeId = newTypeId;
            }
        }

        await _context.SaveChangesAsync();

        return await GetByIdAsync(id, userId);
    }

    // 8. DELETE DEVICE
    public async Task<bool> DeleteAsync(int id, int userId)
    {
        var device = await _context.Devices
            .FirstOrDefaultAsync(d =>
                d.Id == id &&
                d.UserId == userId
            );

        if (device == null) return false;

        // Device đã gắn MCU phải được xóa DeviceTask
        // khỏi firmware trước khi xóa bản ghi Registry.
        //
        // Tránh trường hợp xóa database nhưng GPIO
        // vẫn đang được firmware điều khiển.
        if (device.MicrocontrollerId != null)
        {
            throw new InvalidOperationException(
                "Device đang gắn Microcontroller. " +
                "Cần hủy liên kết phần cứng trước khi xóa."
            );
        }

        // Không tự xóa Schedule chưa được xử lý.
        //
        // Dù MCU đã bị xóa khỏi Registry,
        // Schedule cũ vẫn có thể tồn tại trên phần cứng.
        var hasSchedule = await _context.Schedules.AnyAsync(s => s.DeviceId == id);

        if (hasSchedule)
        {
            throw new InvalidOperationException(
                "Device còn Schedule. " +
                "Cần xử lý lịch trước khi xóa."
            );
        }
        // Những DeviceTagGroup liên kết với Device
        // sẽ bị xóa theo quan hệ cascade mặc định
        // của khóa ngoại bắt buộc, nếu schema đã áp dụng đúng.
        //
        // Bản thân TagGroup và Tag vẫn được giữ lại.
        _context.Devices.Remove(device);

        await _context.SaveChangesAsync();

        return true;

    }

        // 9. CÁC CHỨC NĂNG SẼ BỔ SUNG SAU
        // ==========================================

        // TODO: ResolveAsync() (có thể thực hiện trên server NLP)
        // Tìm Device dựa trên Tag -> TagGroup -> Device.

        // TODO: UpdateBindingAsync()
        // Thay đổi MCU hoặc GPIO, có đồng bộ MQTT.

        // TODO: UnbindAsync()
        // Bỏ liên kết MCU sau khi xử lý phần cứng.

        // TODO: UpdateReportedStatusAsync()
        // Chỉ dành cho luồng đồng bộ MQTT đáng tin cậy,
        // không cho người dùng tự sửa CurrentStatus.



}