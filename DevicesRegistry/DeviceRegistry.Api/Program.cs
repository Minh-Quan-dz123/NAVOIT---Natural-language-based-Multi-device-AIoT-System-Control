using System.Security.Claims;
using System.Security.Cryptography;

using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.EntityFrameworkCore;
using Microsoft.IdentityModel.Tokens;

using DeviceRegistry.Api.Data;
using DeviceRegistry.Api.Services;

using System.Text;
using Microsoft.AspNetCore.Authentication;
using DeviceRegistry.Api.Authentication;

// đọc .env để lấy internal key chung với nlp server
if (File.Exists(".env"))
{
    DotNetEnv.Env.Load();
}

var builder = WebApplication.CreateBuilder(args);


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
builder.Services.AddScoped<MicrocontrollerTypeService>();

// 4. CẤU HÌNH JWT RS256

// 4.1. lấy jwt ở appsetting.json
var jwt = builder.Configuration.GetSection("Jwt");
string issuer = jwt["Issuer"]?? throw new InvalidOperationException("Thiếu JWT Issuer.");
string audience = jwt["Audience"]?? throw new InvalidOperationException("Thiếu JWT Audience.");
string privateKeyPath = jwt["PrivateKeyPath"]?? throw new InvalidOperationException("Thiếu JWT Key.");
string publicKeyPath = jwt["PublicKeyPath"]?? throw new InvalidOperationException("Thiếu JWT Key.");

// 4.2. Xác định đường dẫn đầy đủ
privateKeyPath = Path.GetFullPath(
    Path.Combine(builder.Environment.ContentRootPath, privateKeyPath)
);

publicKeyPath = Path.GetFullPath(
    Path.Combine(builder.Environment.ContentRootPath, publicKeyPath)
);

// 4.3. Kiểm tra file khóa có tồn tại không
if (!File.Exists(privateKeyPath))
{
    throw new InvalidOperationException("Không tìm thấy file JWT Private Key.");
}

if (!File.Exists(publicKeyPath))
{
    throw new InvalidOperationException("Không tìm thấy file JWT Public Key.");
}

// 4.4. Đọc Private Key
var privateRsa = RSA.Create();
privateRsa.ImportFromPem(File.ReadAllText(privateKeyPath));

// 4.5. Đọc Public Key
var publicRsa = RSA.Create();
publicRsa.ImportFromPem(File.ReadAllText(publicKeyPath));

// 4.6. Tạo RSA Security Key
var privateSecurityKey = new RsaSecurityKey(privateRsa);
var publicSecurityKey = new RsaSecurityKey(publicRsa);

// 4.7. Tạo thông tin ký JWT bằng RS256
var signingCredentials = new SigningCredentials(privateSecurityKey, SecurityAlgorithms.RsaSha256);

// Đăng ký SigningCredentials cho AuthService
builder.Services.AddSingleton(signingCredentials);

// 5. JWT AUTHENTICATION
builder.Services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme) // AddAuthentication(...) Đăng ký cơ chế xác thực cho ứng dụng.
    .AddJwtBearer(options => // AddJwtBearer(...) Cấu hình xác thực bằng JWT gửi qua HTTP Bearer.
    {
        // Giữ nguyên tên Claim trong JWT.
        // Ví dụ: ClaimTypes.NameIdentifier.
        options.MapInboundClaims = false;

        options.TokenValidationParameters = new TokenValidationParameters
        {
            ValidateIssuer = true,      // Yêu cầu kiểm tra bên phát hành token.
            ValidIssuer = issuer,  // Xác định issuer hợp lệ lấy từ cấu hình.

            ValidateAudience = true,        // Yêu cầu kiểm tra đối tượng nhận token.
            ValidAudience = audience,// Xác định audience hợp lệ.

            ValidateIssuerSigningKey = true,    // Yêu cầu xác minh chữ ký JWT.
            IssuerSigningKey = publicSecurityKey,

            // Chỉ chấp nhận RS256
            ValidAlgorithms = new[]
            {
                SecurityAlgorithms.RsaSha256
            },

            RequireSignedTokens = true,

            // Kiểm tra thời hạn
            RequireExpirationTime = true,
            ValidateLifetime = true,

            ClockSkew = TimeSpan.FromSeconds(30),

            // Ánh xạ thông tin người dùng
            NameClaimType = ClaimTypes.Name,
            RoleClaimType = ClaimTypes.Role
        };
    });


// 6. XÁC THỰC NLP SERVER BẰNG INTERNAL KEY
// 6.1. Đọc key từ cấu hình
string internalKey = builder.Configuration["InternalApi:Key"] ?? throw new InvalidOperationException("Thiếu Internal API Key.");

// 6.2. Kiểm tra key
if (Encoding.UTF8.GetByteCount(internalKey) < 32)
{
    throw new InvalidOperationException("Internal API Key phải dài ít nhất 32 byte.");
}

// 6.3. Đăng ký cơ chế xác thực Internal Key
// Không thay thế JWT Bearer đang có.
builder.Services.AddAuthentication().AddScheme<AuthenticationSchemeOptions, InternalKeyAuthenticationHandler>("InternalKey", options => { });

// 6.4. Đăng ký policy cho NLP Server
builder.Services.AddAuthorization(options =>
{
    options.AddPolicy("NlpServerOnly", policy =>
    {
        policy.AddAuthenticationSchemes("InternalKey");
        policy.RequireAuthenticatedUser();
    });
});


// 5. BULDE APPLICATION
var app = builder.Build();

// 6. CẤU HÌNH MIDDLEWARE ( các Middleware)
// 6.1. Bật giao diện Swagger
app.UseSwagger();
app.UseSwaggerUI();

// 6.2. Middleware này chuyển hướng các request HTTP sang HTTPS khi cấu hình endpoint HTTPS phù hợp.
app.UseHttpsRedirection(); 

// 6.3. Middleware này đọc Bearer token và thiết lập HttpContext.User.
app.UseAuthentication(); 

// 6.4. Middleware này xử lý các yêu cầu phân quyền dựa trên metadata của endpoint và thông tin người dùng đã được xác thực.
app.UseAuthorization(); 

// 6.5. // ánh xạ Controller thành endpoint
app.MapControllers(); 


app.Run();

