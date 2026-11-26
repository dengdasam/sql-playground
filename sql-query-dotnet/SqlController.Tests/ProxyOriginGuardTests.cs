using System.IO;
using Microsoft.AspNetCore.Http;

namespace SqlController.Tests;

/// <summary>
/// 反代入口跨站拦截的回归测试。
///
/// 背景：控制器转发请求时只拷贝白名单头，Origin 被丢掉，
/// 导致经 5288 进来的跨站请求能一路打到后端。这组用例钉住控制器这一层的判定。
/// </summary>
public class ProxyOriginGuardTests
{
    private static HttpRequest Request(string host = "127.0.0.1:5288", string? origin = null)
    {
        var ctx = new DefaultHttpContext();
        ctx.Request.Host = new HostString(host);
        if (origin is not null) ctx.Request.Headers.Origin = origin;
        return ctx.Request;
    }

    [Theory]
    [InlineData("127.0.0.1:5288")]
    [InlineData("localhost:5288")]
    public void Allows_loopback_without_origin(string host)
        => Assert.Null(ProxyOriginGuard.Check(Request(host)));

    [Fact]
    public void Allows_same_origin()
        => Assert.Null(ProxyOriginGuard.Check(Request(origin: "http://127.0.0.1:5288")));

    [Fact]
    public void Allows_localhost_origin()
        => Assert.Null(ProxyOriginGuard.Check(Request(origin: "http://localhost:5288")));

    [Theory]
    [InlineData("http://evil.example.com")]
    [InlineData("http://evil.example.com:5288")]
    [InlineData("https://127.0.0.1:5288")]
    [InlineData("null")]
    [InlineData("not-an-origin")]
    public void Rejects_cross_site_or_malformed_origin(string origin)
        => Assert.NotNull(ProxyOriginGuard.Check(Request(origin: origin)));

    [Theory]
    [InlineData("evil.example.com")]
    [InlineData("evil.example.com:5288")]
    [InlineData("192.168.1.9:5288")]
    public void Rejects_non_loopback_host(string host)
        => Assert.NotNull(ProxyOriginGuard.Check(Request(host)));

    [Fact]
    public void Rejects_origin_with_unexpected_port()
        => Assert.NotNull(ProxyOriginGuard.Check(Request(origin: "http://127.0.0.1:9999")));
}
