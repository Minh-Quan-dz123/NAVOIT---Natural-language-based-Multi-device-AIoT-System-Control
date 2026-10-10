using Microsoft.EntityFrameworkCore;
using DeviceRegistry.Api.Models;

namespace DeviceRegistry.Api.Data;

public class AppDbContext:DbContext // kế thừa 
{
    public AppDbContext(DbContextOptions<AppDbContext> options):base(options)
    {
    }
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

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        base.OnModelCreating(modelBuilder);

        // User 1 -- N Microcontroller
        modelBuilder.Entity<User>()
            .HasMany(u => u.Microcontrollers)
            .WithOne(m => m.User)
            .HasForeignKey(m => m.UserId);

        // Microcontroller 1 -- N Device
        modelBuilder.Entity<Microcontroller>()
            .HasMany(m => m.Devices)
            .WithOne(d => d.Microcontroller)
            .HasForeignKey(d => d.MicrocontrollerId);

        // User 1 -- N Device
        modelBuilder.Entity<User>()
            .HasMany(u => u.Devices)
            .WithOne(d => d.User)
            .HasForeignKey(d => d.UserId);

        // DeviceType 1 -- N Device
        modelBuilder.Entity<DeviceType>()
            .HasMany(dt => dt.Devices)
            .WithOne(d => d.DeviceType)
            .HasForeignKey(d => d.DeviceTypeId);

        // Device 1 -- 1 Schedule
        modelBuilder.Entity<Device>()
            .HasOne(d => d.Schedule)
            .WithOne(s => s.Device)
            .HasForeignKey<Schedule>(s => s.DeviceId);

        // TagGroup 1 -- N DeviceTagGroup
        modelBuilder.Entity<TagGroup>()
            .HasMany(tg => tg.DeviceTagGroups)
            .WithOne(dtg => dtg.TagGroup)
            .HasForeignKey(dtg => dtg.TagGroupId);

        // Device 1 -- N DeviceTagGroup
        modelBuilder.Entity<Device>()
            .HasMany(d => d.DeviceTagGroups)
            .WithOne(dtg => dtg.Device)
            .HasForeignKey(dtg => dtg.DeviceId);

        // TagGroup 1 -- N Tag
        modelBuilder.Entity<TagGroup>()
            .HasMany(tg => tg.Tags)
            .WithOne(t => t.TagGroup)
            .HasForeignKey(t => t.TagGroupId);
    }
}