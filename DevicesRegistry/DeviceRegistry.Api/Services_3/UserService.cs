using DeviceRegistry.Api.DTOs;
using DeviceRegistry.Api.Data;
using DeviceRegistry.Api.Models;
using Microsoft.EntityFrameworkCore;
using Microsoft.AspNetCore.Identity;


namespace DeviceRegistry.Api.Services;

public class UsersService
{
    // 0. Inject
    private readonly AppDbContext _context;
    private readonly PasswordHasher<User> _passwordHasher = new();
    public UsersService(AppDbContext context) {_context = context;}

    // 1. Thêm user
    // 2. Sửa 1 hoặc toàn bộ thông tin của user (name, password, phone)
    // 3. xóa user
    // 4. get infor của user như id, name, (password thì ko cần), phone 
    // rồi là các microcontroller (cũng lấy full thông tin), device... tóm lại là các thứ của user này để đưa lên dashboard

    // helper function
    // Chuyển Model sang Response DTO
    private static UserResponseDto MapToDto(User user)
    {
        return new UserResponseDto
        {
            Id = user.Id,
            Username = user.Username,
            Phone = user.Phone,
            CreatedAt = user.CreatedAt
        };
    } 
    // 1. thêm user (tạo user)
    public async Task<UserResponseDto> CreateUserAsync(CreateUserRequestDto dto)
    {
        // 1.1. check tồn tại
        if (await _context.Users.AnyAsync(u => u.Username == dto.Username))
            {throw new ArgumentException("Username đã tồn tại.");}

        // 1.2. tạo mới
        var user = new User
        {
            Username = dto.Username,
            Phone = dto.Phone,
            CreatedAt = DateTime.UtcNow
        };

        // 1.3. băm mật khẩu
        user.Password = _passwordHasher.HashPassword(user, dto.Password);

        // 1.4. lưu user vào database
        _context.Users.Add(user);
        await _context.SaveChangesAsync();

        return MapToDto(user);
    }

    // 2. Lấy thông tin User theo ID
    public async Task<UserResponseDto?> GetUserByIdAsync(int id)
    {
        // với GetUserByIdAsync thì bỏ AsNoTracking cx được, 
        var user = await _context.Users.AsNoTracking().FirstOrDefaultAsync(u => u.Id == id);
        return user == null ? null : MapToDto(user);
    }

    // 2.5. lấy thông tin User theo username
    public async Task<UserResponseDto?> GetUserByUsernameAsync(string username)
    {
        var user = await _context.Users.AsNoTracking().FirstOrDefaultAsync(u => u.Username == username);

        return user == null ? null : MapToDto(user);
    }

    // 3. Lấy danh sách User
    public async Task<List<UserResponseDto>> GetAllUsersAsync()
    {
        var users = await _context.Users
            .AsNoTracking()
            .Select(u => new UserResponseDto
            {
                Id = u.Id,
                Username = u.Username,
                Phone = u.Phone,
                CreatedAt = u.CreatedAt
            })
            .ToListAsync();

        return users;
    }


    // 4. Cập nhật Username và Phone
    public async Task<UserResponseDto?> UpdateUserAsync(int id, UpdateUserRequestDto dto)
    {
        // 4.1 lấy user ra
        var user = await _context.Users.FirstOrDefaultAsync(u => u.Id == id);
        if (user == null) return null;

        // 4.2. kiểm tra  name
        if (dto.Username != null)
        {
            if (string.IsNullOrWhiteSpace(dto.Username)) throw new ArgumentException("Username không được để trống.");

            // chỉ có 1 username thôi
            var exists = await _context.Users.AnyAsync(
                u => u.Id != id && u.Username == dto.Username
            );
            if (exists) throw new ArgumentException("Username đã tồn tại.");

            user.Username = dto.Username;
        }

        // kiểm tra điện thoại (điện thoại cũng là duy nhất)
        if (dto.Phone != null)
        {
            var phoneExists = await _context.Users.AnyAsync(
                u => u.Id != id && u.Phone == dto.Phone
            );

            if (phoneExists) throw new ArgumentException("Số điện thoại đã được sử dụng.");
            user.Phone = dto.Phone;
        }

        await _context.SaveChangesAsync();

        return MapToDto(user);
    }

    // 5. Đổi mật khẩu
    public async Task<bool> ChangePasswordAsync(int id, ChangePasswordRequestDto dto)
    {
        // lấy user ra
        var user = await _context.Users.FirstOrDefaultAsync(u => u.Id == id);
        if (user == null) return false;

        // 5.1. kiểm tra mật khẩu cũ có đúng ko
        var result = _passwordHasher.VerifyHashedPassword(
            user,
            user.Password,
            dto.OldPassword
        );

        if (result == PasswordVerificationResult.Failed)
            throw new UnauthorizedAccessException("Mật khẩu hiện tại không chính xác.");

        // 5.2. nếu oke thì lưu cái mới
        user.Password = _passwordHasher.HashPassword(user,dto.NewPassword);

        await _context.SaveChangesAsync();

        return true;
    }
    
    // 6. Xóa User
    public async Task<bool> DeleteUserAsync(int id)
    {
        var user = await _context.Users.FirstOrDefaultAsync(u => u.Id == id);

        if (user == null) return false;

        _context.Users.Remove(user);
        await _context.SaveChangesAsync();

        return true;
    }

}