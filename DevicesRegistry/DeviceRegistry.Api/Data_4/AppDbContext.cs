using Microsoft.EntityFrameworkCore;
using DeviceRegistry.Api.Models;

namespace DeviceRegistry.Api.Data;

public class AppDbContext:DbContext // kế thừa 
{
    public AppDbContext(DbContextOptions<AppDbContext> options):base(options)
    {}
    // TODO:
    // DbSet<Device>
    // DbSet<DeviceTagGroup>
    // DbSet<DeviceType>
    // DbSet<Microcontroller>
    // DbSet<Schedule>
    // DbSet<Tag>
    // DbSet<TagGroup>
    // DbSet<User>

    // hàm khởi tạo relationship
    // User 1 -- N Microcontroller
    //Microcontroller 1 -- N Device
    // User 1 -- N Device
    // DeviceType 1 -- N Device
    // Schedule 1 -- 1 Device
    // TagGroup 1 -- N DeviceTagGroup
    // Device 1 -- N DeviceTagGroup
    // TagGroup 1 -- N Tag

    // DbSet
    public DbSet<Device> Devices { get; set; }
    public DbSet<DeviceTagGroup> DeviceTagGroups { get; set; }
    public DbSet<DeviceType> DeviceTypes { get; set; }
    public DbSet<Microcontroller> Microcontrollers { get; set; }
    public DbSet<Schedule> Schedules { get; set; }
    public DbSet<Tag> Tags { get; set; }
    public DbSet<TagGroup> TagGroups { get; set; }
    public DbSet<User> Users { get; set; }

    // CONFIGURE RELATIONSHIPS
    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        base.OnModelCreating(modelBuilder);

        // 1. User 1 -- N Microcontroller
        modelBuilder.Entity<User>()
            .HasMany(u => u.Microcontrollers)
            .WithOne(m => m.User)
            .HasForeignKey(m => m.UserId);

        // 2. Microcontroller 1 -- N Device
        modelBuilder.Entity<Microcontroller>()
            .HasMany(m => m.Devices)
            .WithOne(d => d.Microcontroller)
            .HasForeignKey(d => d.MicrocontrollerId)
            // Khi xóa MCU:
            // Device vẫn được giữ trong database.
            // Chỉ MicrocontrollerId chuyển thành null.
            .OnDelete(DeleteBehavior.SetNull);

        // 3. User 1 -- N Device
        modelBuilder.Entity<User>()
            .HasMany(u => u.Devices)
            .WithOne(d => d.User)
            .HasForeignKey(d => d.UserId);

        // 4. DeviceType 1 -- N Device
        modelBuilder.Entity<DeviceType>()
            .HasMany(dt => dt.Devices)
            .WithOne(d => d.DeviceType)
            .HasForeignKey(d => d.DeviceTypeId)
            // Không cho xóa DeviceType đang được Device sử dụng.
            .OnDelete(DeleteBehavior.Restrict);


        // 5. Device 1 -- 0.1 Schedule
        modelBuilder.Entity<Device>()
            .HasOne(d => d.Schedule)
            .WithOne(s => s.Device)
            .HasForeignKey<Schedule>(s => s.DeviceId)
            // Khi xóa Device, Schedule liên quan cũng bị xóa.
            .OnDelete(DeleteBehavior.Cascade);

        // 6. TagGroup 1 -- N DeviceTagGroup
        modelBuilder.Entity<TagGroup>()
            .HasMany(tg => tg.DeviceTagGroups)
            .WithOne(dtg => dtg.TagGroup)
            .HasForeignKey(dtg => dtg.TagGroupId)
            .OnDelete(DeleteBehavior.Cascade);

        // 7. Device 1 -- N DeviceTagGroup
        modelBuilder.Entity<Device>()
            .HasMany(d => d.DeviceTagGroups)
            .WithOne(dtg => dtg.Device)
            .HasForeignKey(dtg => dtg.DeviceId);

        // 8. TagGroup 1 -- N Tag
        modelBuilder.Entity<TagGroup>()
            .HasMany(tg => tg.Tags)
            .WithOne(t => t.TagGroup)
            .HasForeignKey(t => t.TagGroupId);

        // 9. UNIQUE TAG TRONG CÙNG TAGGROUP

        // Trong cùng một TagGroup, không cho phép
        // tạo hai Tag có Value giống hệt nhau.
        //
        // Ví dụ:
        // Group 1: ["phòng bếp", "phòng bếp"] -> không hợp lệ.
        //
        // Chú ý: ràng buộc này chưa ngăn cùng một Value
        // xuất hiện ở hai TagGroup khác nhau của cùng User.
        // Service sẽ kiểm tra điều kiện đó.
        modelBuilder.Entity<Tag>()
            .HasIndex(t => new
            {
                t.TagGroupId,
                t.Value
            })
            .IsUnique();

        // GIỚI HẠN ĐỘ DÀI TAG
        modelBuilder.Entity<Tag>()
            .Property(t => t.Value)
            .HasMaxLength(150);

        // Để tăng tốc truy vấn TagGroup của User.
        modelBuilder.Entity<TagGroup>()
            .HasIndex(tg => tg.UserId);



        // UNIQUE CONSTRAINTS
        // Không cho phép hai Device cùng sử dụng
        // một GPIO trên cùng Microcontroller.
        //
        // Ví dụ:
        // MCU 1 - GPIO 25: chỉ được một Device.
        // MCU 2 - GPIO 25: vẫn hợp lệ.
        modelBuilder.Entity<Device>()
        // Tạo một index kết hợp từ hai cột:
        // MicrocontrollerId: ID của vi điều khiển.
        // Gpio: Chân GPIO trên vi điều khiển.
            .HasIndex(d => new{d.MicrocontrollerId, d.Gpio }) 
            .IsUnique();


        // Một Device không được liên kết trùng
        // với cùng một TagGroup.
        modelBuilder.Entity<DeviceTagGroup>()
            .HasIndex(dtg => new{dtg.DeviceId, dtg.TagGroupId})
            .IsUnique();

        // Định danh MCU không được trùng trong cùng loại.
        // Cần chuẩn hóa Type và MacAddress tại Service
        // trước khi lưu để tránh sai khác chữ hoa/thường.
        modelBuilder.Entity<Microcontroller>()
            .HasIndex(m => new{m.Type, m.MacAddress})
            .IsUnique();

        // CONFIGURATION
        // Giới hạn độ dài trạng thái đồng bộ.
        modelBuilder.Entity<Device>()
            .Property(d => d.SyncStatus)
            .HasMaxLength(32)
            .HasDefaultValue("unassigned");

        // Trạng thái thiết bị.
        modelBuilder.Entity<Device>()
            .Property(d => d.CurrentStatus)
            .HasMaxLength(32)
            .HasDefaultValue("UNKNOWN");

    }
}