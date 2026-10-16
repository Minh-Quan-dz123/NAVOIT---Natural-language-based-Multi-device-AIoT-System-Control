using DeviceRegistry.Api.Data;
using Microsoft.EntityFrameworkCore;
using System.Text;
using DeviceRegistry.Api.Services;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.IdentityModel.Tokens;

var builder = WebApplication.CreateBuilder(args);

// // Add services to the container.
// // Learn more about configuring OpenAPI at https://aka.ms/aspnet/openapi
// builder.Services.AddOpenApi();

// 1. liên kết tới database
builder.Services.AddDbContext<AppDbContext>(options => options.UseNpgsql(builder.Configuration.GetConnectionString("DefaultConnection")));

// 2. build các Services
builder.Services.AddControllers();
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();
// Hai dòng này phục vụ việc khám phá và tài liệu hóa API.
// AddEndpointsApiExplorer(): đăng ký dịch vụ khám phá endpoint để tạo thông tin mô tả API.
// AddSwaggerGen(): đăng ký dịch vụ sinh tài liệu OpenAPI bằng Swagger.

// --- khởi tạo các instance ---
builder.Services.AddScoped<AuthService>();
builder.Services.AddScoped<UsersService>();
builder.Services.AddScoped<DeviceService>();
builder.Services.AddScoped<DeviceTypeService>();

// 3. buidl Service đặc biệt - JwT

// 3.1. lấy jwt ở appsetting.json
var jwt = builder.Configuration.GetSection("Jwt");
var jwtKey = jwt["Key"] ?? throw new InvalidOperationException("Thiếu JWT Key.");

// 3.2. Kiểm tra độ dài JWT Key
if (Encoding.UTF8.GetByteCount(jwtKey) < 32) throw new InvalidOperationException("JWT Key phải có ít nhất 32 byte.");

// 3.3. Cấu hình xác thực JWT
builder.Services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme) // AddAuthentication(...) Đăng ký cơ chế xác thực cho ứng dụng.
    .AddJwtBearer(options => // AddJwtBearer(...) Cấu hình xác thực bằng JWT gửi qua HTTP Bearer.
    {
        options.TokenValidationParameters = new TokenValidationParameters
        {
            ValidateIssuer = true,      // Yêu cầu kiểm tra bên phát hành token.
            ValidIssuer = jwt["Issuer"],// Xác định issuer hợp lệ lấy từ cấu hình.

            ValidateAudience = true,        // Yêu cầu kiểm tra đối tượng nhận token.
            ValidAudience = jwt["Audience"],// Xác định audience hợp lệ.

            ValidateIssuerSigningKey = true,    // Yêu cầu xác minh chữ ký JWT.
            IssuerSigningKey = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(jwtKey)), // Cung cấp khóa dùng để xác minh chữ ký, phải khớp với khóa đã ký token.

            ValidateLifetime = true,             // Kiểm tra thời hạn token.
            ClockSkew = TimeSpan.FromSeconds(30) // Cho phép sai lệch đồng hồ tối đa 30 giây khi kiểm tra thời hạn token.
        };
    });

builder.Services.AddAuthorization();

// 3. Build ứng dụng
var app = builder.Build();

// 4. Cấu hình xử lý HTTP ( các Middleware)
app.UseHttpsRedirection(); // Middleware này chuyển hướng các request HTTP sang HTTPS khi cấu hình endpoint HTTPS phù hợp.
app.UseAuthorization(); // Middleware này xử lý các yêu cầu phân quyền dựa trên metadata của endpoint và thông tin người dùng đã được xác thực.
app.MapControllers(); // ánh xạ Controller thành endpoint
app.UseAuthentication(); // Đưa bước xác thực vào pipeline xử lý HTTP request.
app.UseAuthorization(); // Đưa bước phân quyền vào pipeline xử lý HTTP request.

app.Run();

