using System.Security.Claims;
using System.Security.Cryptography;
using System.Text;
using System.Text.Encodings.Web;

using Microsoft.AspNetCore.Authentication;
using Microsoft.Extensions.Options;

namespace DeviceRegistry.Api.Authentication;

public class InternalKeyAuthenticationHandler
    : AuthenticationHandler<AuthenticationSchemeOptions>
{
    private readonly IConfiguration _configuration;

    public InternalKeyAuthenticationHandler(
        IOptionsMonitor<AuthenticationSchemeOptions> options,
        ILoggerFactory logger,
        UrlEncoder encoder,
        IConfiguration configuration
    ) : base(options, logger, encoder)
    {
        _configuration = configuration;
    }

    protected override Task<AuthenticateResult> HandleAuthenticateAsync()
    {
        // 1. Lấy key do NLP Server gửi
        if (!Request.Headers.TryGetValue("X-Internal-Key", out var receivedKey)|| receivedKey.Count != 1)
        {
            return Task.FromResult(AuthenticateResult.Fail("Thiếu Internal Key."));
        }

        // 2. Lấy key được lưu trong Registry
        string savedKey = _configuration["InternalApi:Key"] ?? "";

        // 3. Chuyển hai key thành byte[]
        byte[] savedBytes = Encoding.UTF8.GetBytes(savedKey);
        byte[] receivedBytes = Encoding.UTF8.GetBytes(
            receivedKey.ToString()
        );

        // 4. So sánh hai key
        bool valid = CryptographicOperations.FixedTimeEquals(savedBytes,receivedBytes);

        if (!valid)
        {
            return Task.FromResult( AuthenticateResult.Fail("Internal Key không hợp lệ."));
        }

        // 5. Xác thực thành công
        var claims = new[]
        {
            new Claim(ClaimTypes.NameIdentifier, "nlp-server")
        };

        var identity = new ClaimsIdentity(claims, Scheme.Name);
        var principal = new ClaimsPrincipal(identity);
        var ticket = new AuthenticationTicket(principal, Scheme.Name);

        return Task.FromResult(AuthenticateResult.Success(ticket));
    }
}
