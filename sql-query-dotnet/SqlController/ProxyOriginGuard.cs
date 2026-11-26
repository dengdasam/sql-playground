using Microsoft.AspNetCore.Http;

namespace SqlController;

/// <summary>
/// 反代入口的跨站拦截。
///
/// 为什么控制器也要拦一遍，而不是只靠后端：
///   · 控制器是 <see cref="HttpRequestMessage"/> 逐项拷贝请求头的（白名单式），
///     早先只转发 X-Forwarded-*，Origin 被丢弃，后端因此看不到来源、
///     会把跨站请求当成正常的非浏览器调用放行。
///   · 即使现在补上了 Origin 转发，也应该在这里先拒——不把可疑请求送进内网端口，
///     也不必依赖后端版本是否最新。
///
/// 判定规则与后端的 OriginGuard 一致，只是端口固定为本控制器实际监听的 5288。
/// </summary>
internal static class ProxyOriginGuard
{
    private static readonly HashSet<string> AllowedHosts =
        new(StringComparer.OrdinalIgnoreCase) { "127.0.0.1", "localhost", "[::1]", "::1" };

    /// <summary>拒绝原因；通过返回 null。</summary>
    public static string? Check(HttpRequest request)
    {
        var host = request.Host.Host;
        if (string.IsNullOrEmpty(host) || !AllowedHosts.Contains(host))
            return "只接受本机访问";

        var origin = request.Headers.Origin.ToString();
        if (string.IsNullOrEmpty(origin)) return null;   // 非浏览器客户端，无冒用风险

        if (origin.Equals("null", StringComparison.OrdinalIgnoreCase))
            return "拒绝来自沙箱页面的请求";

        if (!Uri.TryCreate(origin, UriKind.Absolute, out var uri)) return "Origin 格式非法";
        if (!uri.Scheme.Equals("http", StringComparison.OrdinalIgnoreCase)) return "只接受 http 来源";
        if (!AllowedHosts.Contains(uri.Host)) return "拒绝跨站请求";

        // 控制器只监听 5288，页面来源也应是 5288
        var originPort = uri.IsDefaultPort ? 80 : uri.Port;
        if (originPort != 5288 && originPort != 5280 && originPort != 5180)
            return $"拒绝非本机端口的请求（Origin 端口 {originPort}）";

        return null;
    }
}
