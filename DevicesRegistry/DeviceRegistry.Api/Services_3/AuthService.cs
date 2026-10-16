using System.IdentityModel.Tokens.Jwt;  // Tạo JWT và chuyển JWT thành chuỗi bằng JwtSecurityTokenHandler.
using System.Security.Claims;           // Làm việc với Claim — các thông tin được nhúng vào token, ví dụ UserId, Username, Role.
using System.Text;                      // Cung cấp Encoding, dùng Encoding.UTF8.GetBytes(key) để chuyển chuỗi khóa bí mật thành mảng byte.
using Microsoft.AspNetCore.Identity;    // Cung cấp các công cụ quản lý mật khẩu và người dùng, ví dụ PasswordHasher<TUser> để băm và kiểm tra mật khẩu.
using Microsoft.EntityFrameworkCore;    // Cung cấp ORM để truy vấn và thao tác database bằng C#, ví dụ Where(),
using Microsoft.IdentityModel.Tokens;   // Cung cấp các thành phần bảo mật token, ví dụ SymmetricSecurityKey, SigningCredentials, SecurityAlgorithms để ký JWT.

using DeviceRegistry.Api.Data;
using DeviceRegistry.Api.DTOs;
using DeviceRegistry.Api.Models;

namespace DeviceRegistry.Api.Services;

public class AuthService
{
    private readonly AppDbContext _context; // Làm việc với database
    private readonly IConfiguration _configuration; // là đối tượng IConfiguration, dùng để đọc cấu hình của ứng dụng, chẳng hạn JWT Key, Issuer và Audience.
    private readonly PasswordHasher<User> _passwordHasher = new(); // Hash và xác minh mật khẩu

    // 1. Khởi tạo service
    public AuthService(AppDbContext context, IConfiguration configuration)
    {
        _context = context;
        _configuration = configuration;
    }

    // 2. Đăng ký
    public async Task<AuthResponseDto> RegisterAsync(CreateUserRequestDto dto)
    {
        // 2.1. các lớp kiểu tra
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


        // 2.2. kiểm tra oke thì gán và tiến hành tạo user thôi
        var user = new User
        {
            Username = dto.Username,
            Phone = dto.Phone,
            CreatedAt = DateTime.UtcNow
        };

        user.Password = _passwordHasher.HashPassword(user, dto.Password);

        // 2.3. gọi database để thêm và lưu vào
        _context.Users.Add(user);           // Đánh dấu cần thêm dữ liệu
        await _context.SaveChangesAsync();  //Thực hiện lưu dữ liệu

        // Đăng ký thành công thì trả token luôn (hàm này định nghĩa ở dưới)
        return GenerateToken(user);
    }

    // 3. Đăng nhập
    public async Task<AuthResponseDto?> LoginAsync(LoginDto dto)
    {
        // 3.1. kiểm tra xem có tồn tại trong db ko
        var user = await _context.Users.FirstOrDefaultAsync(u => u.Username == dto.Username);

        // 3.2. nếu ko thì là user chưa tồn tại => đăng nhập xịt
        if (user == null) return null;

        // 3.3. nếu user oke thì bắt đầu kiểm tra mật khẩu của user này
        var result = _passwordHasher.VerifyHashedPassword(user, user.Password, dto.Password);

        // 3.4. failed thì tôi
        if (result == PasswordVerificationResult.Failed) return null;

        // 3.5. mật khẩu đúng nhưng cần nâng cấp (hash lại thôi, do đó user ko cần quan tâm)
        if (result == PasswordVerificationResult.SuccessRehashNeeded)
        {
            user.Password = _passwordHasher.HashPassword(user, dto.Password);
            await _context.SaveChangesAsync();
        }

        // login thành công thì trả token luôn (hàm này định nghĩa ở dưới)
        return GenerateToken(user);
    }

    // 4. Tạo JWT
    private AuthResponseDto GenerateToken(User user)
    {
        // các bước kiểm tra trước khi sinh token cho user
        // 4.1. lấy ra object Jwt ở appsettings.json
        var jwt = _configuration.GetSection("Jwt"); // hàm GetSection Nó lấy nhóm cấu hình có tên "Jwt" trong file appsettings.json.

        // 4.2. lấy key ra, nếu ko có thì ném lỗi
        var key = jwt["Key"] ?? throw new InvalidOperationException("Thiếu JWT Key.");

        // 4.3. kiểm tra JWT key có đủ độ dài tối thiểu 32 byte ko
        if (Encoding.UTF8.GetByteCount(key) < 32) throw new InvalidOperationException("JWT Key phải có ít nhất 32 byte.");

        // 4.4 kiểm tra có bên phát hành và bên client ko
        var issuer = jwt["Issuer"] ?? throw new InvalidOperationException("Thiếu JWT Issuer.");
        var audience = jwt["Audience"] ?? throw new InvalidOperationException("Thiếu JWT Audience.");

        // nếu tất cả oke hết thì bắt đầu sinh token

        // 4.5 từ thời điểm hiện tại, cộng thêm 1 giờ
        var expiresAt = DateTime.UtcNow.AddHours(1);

        // 4.6. lưu username và userId vào claim để lưu lâu dài
        var claims = new[]
        {
            new Claim(ClaimTypes.NameIdentifier, user.Id.ToString()),
            new Claim(ClaimTypes.Name, user.Username)
            // Claim dùng để lấy "bên phải" để lưu vào "bên trái"
        };

        // 4.7. tạo khóa bảo mật từ chuỗi key, phục vụ việc ký JWT. 
        // Encoding.UTF8.GetBytes(key): chuyển chuỗi key thành mảng byte (byte[]).
        // SymmetricSecurityKey(...): tạo đối tượng khóa đối xứng từ mảng byte đó.
        var securityKey = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(key));

        // 4.8. tạo thông tin ký JWT, gồm khóa bí mật và thuật toán ký HS256.
        // Một khóa bí mật chung	
        // Đơn giản, cùng khóa để ký và xác minh
        var credentials = new SigningCredentials(securityKey, SecurityAlgorithms.HmacSha256);

        // 4.9. cuối cùng tạo Jwt thật chứa các thông tin cần thiết
        // tạo một JWT (JSON Web Token) từ các thông tin đã chuẩn bị trước đó.
        var token = new JwtSecurityToken(
            issuer: issuer,
            audience: audience,
            claims: claims,
            expires: expiresAt,
            signingCredentials: credentials);

        // 4.10. trả về DTO đúng
        return new AuthResponseDto
        {
            AccessToken = new JwtSecurityTokenHandler().WriteToken(token),
            ExpiresAt = expiresAt,
            UserId = user.Id,
            Username = user.Username
        };
    }
}