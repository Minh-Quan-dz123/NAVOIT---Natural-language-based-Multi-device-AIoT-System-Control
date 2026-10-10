using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;
using System.Text;
using DeviceRegistry.Api.Data;
using DeviceRegistry.Api.DTOs;
using DeviceRegistry.Api.Models;
using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;
using Microsoft.IdentityModel.Tokens;

namespace DeviceRegistry.Api.Services;

public class AuthService
{
    private readonly AppDbContext _context;
    private readonly IConfiguration _configuration;
    private readonly PasswordHasher<User> _passwordHasher = new();

    public AuthService(AppDbContext context, IConfiguration configuration)
    {
        _context = context;
        _configuration = configuration;
    }

    // 1. Đăng ký
    public async Task<AuthResponseDto> RegisterAsync(CreateUserRequestDto dto)
    {
        if (string.IsNullOrWhiteSpace(dto.Username))
            throw new ArgumentException("Username không được để trống.");

        if (string.IsNullOrWhiteSpace(dto.Password))
            throw new ArgumentException("Password không được để trống.");

        if (await _context.Users.AnyAsync(u => u.Username == dto.Username))
        {
            throw new ArgumentException("Username đã tồn tại.");
        }

        if (dto.Phone != null && await _context.Users.AnyAsync(u => u.Phone == dto.Phone))
        {
            throw new ArgumentException("Số điện thoại đã được sử dụng.");
        }

        var user = new User
        {
            Username = dto.Username,
            Phone = dto.Phone,
            CreatedAt = DateTime.UtcNow
        };

        user.Password = _passwordHasher.HashPassword(user, dto.Password);

        _context.Users.Add(user);
        await _context.SaveChangesAsync();

        // Đăng ký thành công thì trả token luôn
        return GenerateToken(user);
    }

    // 2. Đăng nhập
    public async Task<AuthResponseDto?> LoginAsync(LoginDto dto)
    {
        var user = await _context.Users.FirstOrDefaultAsync(u => u.Username == dto.Username);

        if (user == null) return null;

        var result = _passwordHasher.VerifyHashedPassword(
            user,
            user.Password,
            dto.Password);

        if (result == PasswordVerificationResult.Failed) return null;

        if (result == PasswordVerificationResult.SuccessRehashNeeded)
        {
            user.Password = _passwordHasher.HashPassword(user, dto.Password);
            await _context.SaveChangesAsync();
        }

        return GenerateToken(user);
    }

    // 3. Tạo JWT
    private AuthResponseDto GenerateToken(User user)
    {
        var jwt = _configuration.GetSection("Jwt");

        var key = jwt["Key"] ?? throw new InvalidOperationException("Thiếu JWT Key.");

        if (Encoding.UTF8.GetByteCount(key) < 32) throw new InvalidOperationException("JWT Key phải có ít nhất 32 byte.");

        var issuer = jwt["Issuer"] ?? throw new InvalidOperationException("Thiếu JWT Issuer.");

        var audience = jwt["Audience"] ?? throw new InvalidOperationException("Thiếu JWT Audience.");

        var expiresAt = DateTime.UtcNow.AddHours(1);

        var claims = new[]
        {
            new Claim(ClaimTypes.NameIdentifier, user.Id.ToString()),
            new Claim(ClaimTypes.Name, user.Username)
        };

        var securityKey = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(key));

        var credentials = new SigningCredentials(securityKey, SecurityAlgorithms.HmacSha256);

        var token = new JwtSecurityToken(
            issuer: issuer,
            audience: audience,
            claims: claims,
            expires: expiresAt,
            signingCredentials: credentials);

        return new AuthResponseDto
        {
            AccessToken = new JwtSecurityTokenHandler().WriteToken(token),
            ExpiresAt = expiresAt,
            UserId = user.Id,
            Username = user.Username
        };
    }
}