using System.Net;

namespace SqlPlayground;

/// <summary>
/// 本机 API 的跨站防护：校验请求的 Host 与 Origin。
///
/// 要防的两类攻击：
///
/// 1. **跨站请求（CSRF 式）**——你浏览器里开着任意网页，页面脚本向 127.0.0.1:5288
///    发请求读走你的数据库。前端用的是 application/json，会触发 CORS 预检，
///    但 <c>text/plain</c> 属于"简单请求"，**不预检**；而 PostBody 只解析 JSON 体、
///    不看 Content-Type —— 所以恶意页面用 text/plain 发一段 JSON 就能拿到真实结果。
///    （已实测复现，故此处必须校验 Origin。）
///
/// 2. **DNS rebinding**——攻击者把域名先解析到自己服务器（页面加载完），
///    再改成 127.0.0.1，此时脚本与目标"同源"，预检也拦不住。
///    典型的 Host 白名单能挡住它：Host 会是攻击者域名，不在允许列表里。
///
/// 兼容性：控制器反向代理时，后端的 Host 是 127.0.0.1:5280（用户访问的是 :5288），
/// 因此允许列表必须同时覆盖两个端口；控制器的页面自身不发跨源请求，Origin 与 Host 同源。
/// </summary>
public static class OriginGuard
{
    /// <summary>允许的 Host（不含端口）。只认回环，本服务本就只绑本机。</summary>
    private static readonly HashSet<string> AllowedHosts =
        new(StringComparer.OrdinalIgnoreCase) { "127.0.0.1", "localhost", "[::1]", "::1" };

    /// <summary>
    /// 校验通过返回 null；否则返回应回给调用方的拒绝原因。
    /// </summary>
    public static ApiException? Check(HttpRequest request)
    {
        // ---------- Host：挡 DNS rebinding ----------
        var host = request.Host.Host;
        if (string.IsNullOrEmpty(host) || !AllowedHosts.Contains(host))
            return new ApiException("BAD_HOST",
                $"只接受本机访问，收到 Host: {request.Host}。请用 http://127.0.0.1:5288/ 打开页面。");

        // ---------- Origin：挡跨站请求 ----------
        // 没有 Origin 头的情况：非浏览器客户端（curl、脚本、控制器内部代理）不会带，
        // 这类请求没有"被别的网站冒用"的风险，放行。
        var origin = request.Headers.Origin.ToString();
        if (!string.IsNullOrEmpty(origin) && !IsSameOrigin(origin, request.Host))
            return new ApiException("BAD_ORIGIN",
                $"拒绝跨站请求，收到 Origin: {origin}。本接口只允许页面自身调用。");

        // ---------- Sec-Fetch-Site：现代浏览器的额外信号 ----------
        // 有 Origin 已足够，但同源 GET 有些浏览器不带 Origin，用这个补一道。
        var fetchSite = request.Headers["Sec-Fetch-Site"].ToString();
        if (!string.IsNullOrEmpty(fetchSite)
            && !fetchSite.Equals("same-origin", StringComparison.OrdinalIgnoreCase)
            && !fetchSite.Equals("none", StringComparison.OrdinalIgnoreCase))
            return new ApiException("BAD_FETCH_SITE",
                $"拒绝跨站请求（Sec-Fetch-Site: {fetchSite}）。本接口只允许页面自身调用。");

        return null;
    }

    /// <summary>
    /// Origin 是否可接受。要求 scheme=http、host 在允许列表、端口在允许列表。
    ///
    /// 端口不要求与请求 Host 完全一致：控制器反代时后端看到的是 :5280，
    /// 而浏览器 Origin 是 :5288，这是正常链路。只要两端都落在本机已知端口即可。
    /// </summary>
    private static bool IsSameOrigin(string origin, HostString requestHost)
    {
        if (origin.Equals("null", StringComparison.OrdinalIgnoreCase)) return false;
        if (!Uri.TryCreate(origin, UriKind.Absolute, out var uri)) return false;

        // 本服务只提供 http
        if (!uri.Scheme.Equals("http", StringComparison.OrdinalIgnoreCase)) return false;

        if (!AllowedHosts.Contains(uri.Host)) return false;

        var originPort = uri.IsDefaultPort ? 80 : uri.Port;
        var requestPort = requestHost.Port ?? 80;
        return originPort == requestPort || (IsAllowedPort(originPort) && IsAllowedPort(requestPort));
    }

    /// <summary>本机已知端口：5288 控制器、5280 控制器拉起的后端、5180 单独调试的后端。</summary>
    private static bool IsAllowedPort(int port) => port is 5288 or 5280 or 5180;
}
