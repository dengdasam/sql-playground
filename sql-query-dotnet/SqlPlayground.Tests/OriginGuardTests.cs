using Microsoft.AspNetCore.Http;

namespace SqlPlayground.Tests;

/// <summary>
/// 跨站防护的回归测试。
///
/// 背景：/api/query 原来没有任何 Origin/Host 校验。恶意网页用 text/plain
/// 发一段 JSON 就是"简单请求"（不触发 CORS 预检），而 PostBody 只看请求体
/// 不看 Content-Type —— 于是任意网站都能读走本地数据库。已在真实进程上复现，
/// 这组用例把那条路堵死并钉住。
/// </summary>
public class OriginGuardTests
{
    private static HttpContext Request(
        string host = "127.0.0.1:5288",
        string? origin = null,
        string? fetchSite = null)
    {
        var ctx = new DefaultHttpContext();
        ctx.Request.Host = new HostString(host);
        if (origin is not null) ctx.Request.Headers.Origin = origin;
        if (fetchSite is not null) ctx.Request.Headers["Sec-Fetch-Site"] = fetchSite;
        return ctx;
    }

    // ---------- 必须放行：正常使用链路 ----------

    [Theory]
    [InlineData("127.0.0.1:5288")]        // 用户直接访问控制器
    [InlineData("localhost:5288")]
    [InlineData("127.0.0.1:5280")]        // 控制器反代到后端
    [InlineData("127.0.0.1:5180")]        // 单独调试后端
    public void Allows_loopback_host_without_origin(string host)
    {
        // 非浏览器客户端（curl、控制器内部代理）不带 Origin
        Assert.Null(OriginGuard.Check(Request(host).Request));
    }

    [Fact]
    public void Allows_same_origin_with_controller_port_mismatch()
    {
        // 浏览器 Origin 是 5288，控制器反代后后端看到 Host 是 5280 —— 正常链路
        var ctx = Request(host: "127.0.0.1:5280", origin: "http://127.0.0.1:5288");
        Assert.Null(OriginGuard.Check(ctx.Request));
    }

    [Fact]
    public void Allows_same_origin_exact_match()
    {
        var ctx = Request(host: "127.0.0.1:5288", origin: "http://127.0.0.1:5288");
        Assert.Null(OriginGuard.Check(ctx.Request));
    }

    [Fact]
    public void Allows_localhost_origin_to_loopback_host()
    {
        var ctx = Request(host: "127.0.0.1:5288", origin: "http://localhost:5288");
        Assert.Null(OriginGuard.Check(ctx.Request));
    }

    [Fact]
    public void Allows_same_origin_fetch_site()
    {
        var ctx = Request(origin: "http://127.0.0.1:5288", fetchSite: "same-origin");
        Assert.Null(OriginGuard.Check(ctx.Request));
    }

    [Fact]
    public void Allows_fetch_site_none_from_address_bar()
    {
        // 地址栏直接打开页面，部分浏览器给 none
        var ctx = Request(fetchSite: "none");
        Assert.Null(OriginGuard.Check(ctx.Request));
    }

    // ---------- 必须拒绝：跨站与 rebinding ----------

    [Fact]
    public void Rejects_cross_site_origin()
    {
        // 这就是实测复现的那条攻击：恶意页面带 Origin 发 text/plain 请求
        var ctx = Request(origin: "http://evil.example.com");
        var ex = OriginGuard.Check(ctx.Request);
        Assert.NotNull(ex);
        Assert.Equal("BAD_ORIGIN", ex!.Code);
    }

    [Fact]
    public void Rejects_cross_site_origin_with_same_style_port()
    {
        var ctx = Request(host: "127.0.0.1:5288", origin: "http://evil.example.com:5288");
        Assert.Equal("BAD_ORIGIN", OriginGuard.Check(ctx.Request)?.Code);
    }

    [Fact]
    public void Rejects_null_origin()
    {
        // sandbox iframe / file:// 页面，Origin 为字面量 "null"
        var ctx = Request(origin: "null");
        Assert.Equal("BAD_ORIGIN", OriginGuard.Check(ctx.Request)?.Code);
    }

    [Fact]
    public void Rejects_https_origin()
    {
        var ctx = Request(origin: "https://127.0.0.1:5288");
        Assert.Equal("BAD_ORIGIN", OriginGuard.Check(ctx.Request)?.Code);
    }

    [Fact]
    public void Rejects_origin_with_other_port()
    {
        var ctx = Request(host: "127.0.0.1:5288", origin: "http://127.0.0.1:9999");
        Assert.Equal("BAD_ORIGIN", OriginGuard.Check(ctx.Request)?.Code);
    }

    [Theory]
    [InlineData("evil.example.com")]         // DNS rebinding：Host 被改成攻击者域名
    [InlineData("evil.example.com:5288")]
    [InlineData("attacker.test")]
    [InlineData("192.168.1.50:5288")]        // 局域网地址也算非本机
    public void Rejects_non_loopback_host(string host)
    {
        var ex = OriginGuard.Check(Request(host).Request);
        Assert.NotNull(ex);
        Assert.Equal("BAD_HOST", ex!.Code);
    }

    [Fact]
    public void Rejects_cross_site_fetch_site()
    {
        var ctx = Request(fetchSite: "cross-site");
        Assert.Equal("BAD_FETCH_SITE", OriginGuard.Check(ctx.Request)?.Code);
    }

    [Fact]
    public void Rejects_same_site_fetch_site()
    {
        // 子域也算同站，仍然可能被冒用
        var ctx = Request(fetchSite: "same-site");
        Assert.Equal("BAD_FETCH_SITE", OriginGuard.Check(ctx.Request)?.Code);
    }

    [Fact]
    public void Rejects_garbage_origin()
    {
        var ctx = Request(origin: "not-a-valid-origin");
        Assert.Equal("BAD_ORIGIN", OriginGuard.Check(ctx.Request)?.Code);
    }
}
