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
builder.Services.AddDbContext<AppDbContext>(options =>
    options.UseNpgsql(
        builder.Configuration.GetConnectionString("DefaultConnection")
    )
);

// 2. build các Services
builder.Services.AddControllers();
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();
// Hai dòng này phục vụ việc khám phá và tài liệu hóa API.
// AddEndpointsApiExplorer(): đăng ký dịch vụ khám phá endpoint để tạo thông tin mô tả API.
// AddSwaggerGen(): đăng ký dịch vụ sinh tài liệu OpenAPI bằng Swagger.

builder.Services.AddScoped<AuthService>();
builder.Services.AddScoped<UsersService>();
builder.Services.AddScoped<DeviceService>();
builder.Services.AddScoped<DeviceTypeService>();

// JWT Authentication
var jwt = builder.Configuration.GetSection("Jwt");
var jwtKey = jwt["Key"]
    ?? throw new InvalidOperationException("Thiếu JWT Key.");

if (Encoding.UTF8.GetByteCount(jwtKey) < 32)
    throw new InvalidOperationException("JWT Key phải có ít nhất 32 byte.");

builder.Services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddJwtBearer(options =>
    {
        options.TokenValidationParameters = new TokenValidationParameters
        {
            ValidateIssuer = true,
            ValidIssuer = jwt["Issuer"],

            ValidateAudience = true,
            ValidAudience = jwt["Audience"],

            ValidateIssuerSigningKey = true,
            IssuerSigningKey = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(jwtKey)),

            ValidateLifetime = true,
            ClockSkew = TimeSpan.FromSeconds(30)
        };
    });

builder.Services.AddAuthorization();

// 3. Build ứng dụng
var app = builder.Build();

// 4. Cấu hình xử lý HTTP ( các Middleware)
app.UseHttpsRedirection(); // Middleware này chuyển hướng các request HTTP sang HTTPS khi cấu hình endpoint HTTPS phù hợp.
app.UseAuthorization(); // Middleware này xử lý các yêu cầu phân quyền dựa trên metadata của endpoint và thông tin người dùng đã được xác thực.
app.MapControllers(); // ánh xạ Controller thành endpoint
app.UseAuthentication();
app.UseAuthorization();

app.Run();

