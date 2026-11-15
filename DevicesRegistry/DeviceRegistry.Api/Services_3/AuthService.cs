
using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;
using System.Text.RegularExpressions;

using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;
using Microsoft.IdentityModel.Tokens;

using Npgsql;

using DeviceRegistry.Api.Data;
using DeviceRegistry.Api.DTOs;
using DeviceRegistry.Api.Models;
namespace DeviceRegistry.Api.Services;

public class AuthService
{
    private readonly AppDbContext _context;
    private readonly IConfiguration _configuration;
    private readonly SigningCredentials _signingCredentials;

    private readonly PasswordHasher<User> _passwordHasher = new();

    // 1. Constructor
    public AuthService(AppDbContext context, IConfiguration configuration, SigningCredentials signingCredentials)
    {
        _context = context;
        _configuration = configuration;
        _signingCredentials = signingCredentials;
    }

    // 2. ĐĂNG KÝ Tk
    public async Task<AuthResponseDto> RegisterAsync(CreateUserRequestDto dto)
    {
        // Chuẩn hóa thông tin
        string username = dto.Username?.Trim() ?? "";
        string password = dto.Password ?? "";

        string? phone = dto.Phone?.Trim();

        if (phone == "") phone = null;

        // 2.1. kiểm tra dữ liệu
        if (string.IsNullOrWhiteSpace(username))
        {
            throw new ArgumentException("Username không được để trống.");
        }

        if (password.Length < 8)
        {
            throw new ArgumentException("Password phải có ít nhất 8 ký tự.");
        }

        if (phone != null &&!Regex.IsMatch(phone, @"^[0-9]{10}$"))
        {
            throw new ArgumentException("Phone phải gồm đúng 10 chữ số.");
        }

        // 2.2. Kiểm tra Username đã tồn tại chưa
        bool usernameExists = await _context.Users.AnyAsync(u => u.Username == username);

        if (usernameExists)
        {
            throw new ArgumentException("Username đã tồn tại.");
        }

        // 2.3. Kiểm tra Phone đã tồn tại chưa
        if (phone != null)
        {
            bool phoneExists = await _context.Users.AnyAsync(u => u.Phone == phone);

            if (phoneExists)
            {
                throw new ArgumentException("Số điện thoại đã được sử dụng.");
            }
        }

        // 2.4. Khởi tạo tài khoản
        var user = new User
        {
            Username = username,
            Phone = phone,
            Role = "User",
            CreatedAt = DateTime.UtcNow
        };

        // Hash mật khẩu trước khi lưu
        user.Password = _passwordHasher.HashPassword(user, password);

        // 2.5. Lưu PostgreSQL
        _context.Users.Add(user);

        try
        {
            await _context.SaveChangesAsync();
        }
        catch (DbUpdateException ex) when (
            ex.InnerException is PostgresException pg &&
            pg.SqlState == PostgresErrorCodes.UniqueViolation)
        {
            throw new ArgumentException("Username hoặc số điện thoại đã tồn tại.");
        }

        // 2.6. Đăng ký thành công, trả JWT
        return GenerateToken(user);
    }

    // 3. ĐĂNG NHẬP
    public async Task<AuthResponseDto?> LoginAsync(LoginDto dto)
    {
        string username = dto.Username?.Trim() ?? "";
        string password = dto.Password ?? "";

        if (string.IsNullOrWhiteSpace(username) ||
            string.IsNullOrEmpty(password))
        {
            return null;
        }

        // 3.1. Tìm tài khoản
        var user = await _context.Users.FirstOrDefaultAsync(u => u.Username == username);

        if (user == null)
        {
            return null;
        }

        // 3.2. Kiểm tra mật khẩu
        var result = _passwordHasher.VerifyHashedPassword(
            user,
            user.Password,
            password
        );

        if (result == PasswordVerificationResult.Failed)
        {
            return null;
        }

        // 3.3. Nếu hash cũ cần nâng cấp
        if (result == PasswordVerificationResult.SuccessRehashNeeded)
        {
            user.Password = _passwordHasher.HashPassword(
                user,
                password
            );
            await _context.SaveChangesAsync();
        }

        // 3.4. Đăng nhập thành công
        return GenerateToken(user);
    }

    // 4. TẠO JWT
    private AuthResponseDto GenerateToken(User user)
    {
        // 4.1. Đọc thông tin cấu hình
        var jwt = _configuration.GetSection("Jwt");

        string issuer = jwt["Issuer"] ?? throw new InvalidOperationException("Thiếu JWT Issuer");

        string audience = jwt["Audience"] ?? throw new InvalidOperationException("Thiếu JWT Audience.");

        // 4.2. Thời gian tồn tại token: 1 giờ
        DateTime now = DateTime.UtcNow;
        DateTime expiresAt = now.AddHours(1);

        // 4.3. Tạo Claim
        var claims = new[]
        {
            new Claim(ClaimTypes.NameIdentifier, user.Id.ToString()),
            new Claim(ClaimTypes.Name,user.Username),
            new Claim(ClaimTypes.Role,user.Role)
        };

        // 4.4. Tạo JWT bằng khóa RSA
        // SigningCredentials được cấu hình trong Program.cs
        var token = new JwtSecurityToken(
            issuer: issuer,
            audience: audience,
            claims: claims,
            notBefore: now,
            expires: expiresAt,
            signingCredentials: _signingCredentials
        );

        // 4.5. Chuyển JWT thành chuỗi
        string accessToken = new JwtSecurityTokenHandler().WriteToken(token);

        // 4.6. Trả kết quả
        return new AuthResponseDto
        {
            AccessToken = accessToken,
            ExpiresAt = expiresAt,
            UserId = user.Id,
            Username = user.Username,
            Role = user.Role
        };
    }
}
