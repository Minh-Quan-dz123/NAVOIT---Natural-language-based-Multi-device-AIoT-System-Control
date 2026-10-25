using DeviceRegistry.Api.Data;
using DeviceRegistry.Api.Services;

using Microsoft.EntityFrameworkCore;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.IdentityModel.Tokens;

using System.Text;


var builder = WebApplication.CreateBuilder(args);


// INTERNAL API KEY

// API nội bộ dùng chung với NLP Server.
//
// Key phải được cấu hình qua biến môi trường.
// Không ghi key thật trực tiếp vào source code.
var internalApiKey = builder.Configuration["InternalApiKey"];

if (string.IsNullOrWhiteSpace(internalApiKey) || Encoding.UTF8.GetByteCount(internalApiKey) < 32)
{
    throw new InvalidOperationException("Thiếu InternalApiKey hoặc key ngắn hơn 32 byte.");
}


// // Add services to the container.
// // Learn more about configuring OpenAPI at https://aka.ms/aspnet/openapi
// builder.Services.AddOpenApi();

// 1. CẤU HÌNH DATABASE
builder.Services.AddDbContext<AppDbContext>(options => options.UseNpgsql(builder.Configuration.GetConnectionString("DefaultConnection")));

// 2. CẤU HÌNH CONTROLLER VÀ SWAGGER
builder.Services.AddControllers();

builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();
// AddEndpointsApiExplorer(): đăng ký dịch vụ khám phá endpoint để tạo thông tin mô tả API.
// AddSwaggerGen(): đăng ký dịch vụ sinh tài liệu OpenAPI bằng Swagger.

// 3. ĐĂNG KÝ SERVICES
builder.Services.AddScoped<AuthService>();
builder.Services.AddScoped<UsersService>();
builder.Services.AddScoped<DeviceService>();
builder.Services.AddScoped<DeviceTypeService>();
builder.Services.AddScoped<MicrocontrollerService>();
builder.Services.AddScoped<ScheduleServices>();
builder.Services.AddScoped<ManageTagsService>();


// 4. buidl Service đặc biệt - JwT

// 4.1. lấy jwt ở appsetting.json
var jwt = builder.Configuration.GetSection("Jwt");
var jwtKey = jwt["Key"]?? throw new InvalidOperationException("Thiếu JWT Key.");
var issuer = jwt["Issuer"]?? throw new InvalidOperationException("Thiếu JWT Issuer.");
var audience = jwt["Audience"]?? throw new InvalidOperationException("Thiếu JWT Audience.");

// 4.2. Kiểm tra độ dài JWT Key
if (Encoding.UTF8.GetByteCount(jwtKey) < 32) throw new InvalidOperationException("JWT Key phải có ít nhất 32 byte.");

// 4.3. Đăng ký xác thực bằng JWT Bearer
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

// đăng ký hệ thống phân quyền, cho phép sử dụng [Authorize] tại Controller hoặc Action.
builder.Services.AddAuthorization();

// 5. BULDE APPLICATION
var app = builder.Build();

// 6. CẤU HÌNH MIDDLEWARE ( các Middleware)
// 6.1. Bật giao diện Swagger
app.UseSwagger();
app.UseSwaggerUI();

// 6.2. Middleware này chuyển hướng các request HTTP sang HTTPS khi cấu hình endpoint HTTPS phù hợp.
app.UseHttpsRedirection(); 

// 6.4. Middleware này đọc Bearer token và thiết lập HttpContext.User.
app.UseAuthentication(); 

// 6.5. Middleware này xử lý các yêu cầu phân quyền dựa trên metadata của endpoint và thông tin người dùng đã được xác thực.
app.UseAuthorization(); 

// 6.6. // ánh xạ Controller thành endpoint
app.MapControllers(); 


app.Run();

