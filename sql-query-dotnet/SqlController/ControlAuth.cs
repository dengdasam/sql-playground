using System.Security.AccessControl;
using System.Security.Cryptography;
using System.Security.Principal;
using System.Text;
using Microsoft.AspNetCore.Http;

// 只读校验与令牌逻辑走单测，允许测试项目访问 internal 类型
[assembly: System.Runtime.CompilerServices.InternalsVisibleTo("SqlController.Tests")]

namespace SqlController;

/// <summary>
/// 控制接口（/control/*）的访问令牌。
///
/// 背景：控制器监听在本机回环端口 5288 上，但同一台机器上的任何进程——包括浏览器页面
/// 里跑的脚本、其他程序——都能 POST /control/stop 把主服务停掉、POST /control/start
/// 反复拉起进程。这些是无鉴权的状态变更接口，需要一道门槛。
///
/// 为什么令牌要落盘而不是纯内存：
///   /control/show 是**跨进程**用的——用户重复双击 exe 时，第二个实例要靠它把已有实例
///   的窗口调到前台。令牌只在内存里的话第二个进程拿不到，功能就废了。
///
/// 安全性边界：
///   · 令牌文件放在 logs/ 下，写入后把 ACL 收紧到「仅当前用户」，其他 Windows 账户读不到。
///   · 每次控制器启动重新生成并覆盖，旧令牌立即失效。
///   · 只防「同机其他用户 / 网页脚本」这类越权，不防「同一用户下的恶意程序」——
///     后者能够读你的文件，任何本机凭据都挡不住，最终要靠系统账号隔离。
///
/// 传递方式：请求头 <c>X-Control-Token</c>，不放 query string（URL 会进日志与历史）。
/// </summary>
internal sealed class ControlAuth
{
    public const string HeaderName = "X-Control-Token";
    private const string FileName = "control-token.txt";

    private ControlAuth(string token) => Token = token;

    /// <summary>本次控制器实例的令牌。</summary>
    public string Token { get; }

    /// <summary>
    /// 生成新令牌并写入 <paramref name="logsDir"/>，权限收紧到当前用户。
    /// 写文件失败时仍返回可用对象（本次会话内鉴权照常生效，只是跨进程 show 会失效）。
    /// </summary>
    public static ControlAuth Create(string logsDir)
    {
        // 32 字节随机数；Base64Url 后 43 字符，不含 + / = 免转义麻烦
        var raw = RandomNumberGenerator.GetBytes(32);
        var token = Convert.ToBase64String(raw).TrimEnd('=').Replace('+', '-').Replace('/', '_');

        try
        {
            Directory.CreateDirectory(logsDir);
            var path = Path.Combine(logsDir, FileName);
            File.WriteAllText(path, token, new UTF8Encoding(false));
            RestrictToCurrentUser(path);
        }
        catch { /* 只读目录等：退化为仅本进程可用 */ }

        return new ControlAuth(token);
    }

    /// <summary>
    /// 读取已有控制器留下的令牌（第二个实例用它去调 /control/show）。
    /// 读不到返回 null。
    /// </summary>
    public static string? TryReadExisting(string logsDir)
    {
        try
        {
            var path = Path.Combine(logsDir, FileName);
            if (!File.Exists(path)) return null;
            var text = File.ReadAllText(path).Trim();
            return text.Length > 0 ? text : null;
        }
        catch { return null; }
    }

    /// <summary>把文件 ACL 收紧到当前用户，其他账户无法读取令牌。</summary>
    private static void RestrictToCurrentUser(string path)
    {
        if (!OperatingSystem.IsWindows()) return;
        try
        {
            var user = WindowsIdentity.GetCurrent().User;
            if (user is null) return;

            var info = new FileInfo(path);
            var security = info.GetAccessControl();
            // 断开继承，只留当前用户完全控制
            security.SetAccessRuleProtection(isProtected: true, preserveInheritance: false);
            security.AddAccessRule(new FileSystemAccessRule(
                user, FileSystemRights.FullControl, AccessControlType.Allow));
            info.SetAccessControl(security);
        }
        catch { /* 文件系统不支持 ACL 时保持默认，不影响功能 */ }
    }

    /// <summary>
    /// 校验请求是否带正确令牌。固定时间比较，避免时序侧信道。
    /// </summary>
    public bool IsAuthorized(HttpRequest request)
    {
        var provided = request.Headers[HeaderName].ToString();
        return Matches(provided, Token);
    }

    /// <summary>与任意给定令牌比较（跨进程场景用）。</summary>
    public static bool Matches(string? provided, string? expected)
    {
        if (string.IsNullOrEmpty(provided) || string.IsNullOrEmpty(expected)) return false;
        var a = Encoding.UTF8.GetBytes(provided);
        var b = Encoding.UTF8.GetBytes(expected);
        // FixedTimeEquals 要求长度一致才能比，长度不同直接拒
        return a.Length == b.Length && CryptographicOperations.FixedTimeEquals(a, b);
    }

    /// <summary>带令牌的 HttpClient，控制器内部调用 /control/* 用。调用方负责释放。</summary>
    public static HttpClient CreateClient(string token, TimeSpan timeout)
    {
        var client = new HttpClient(new HttpClientHandler { UseProxy = false }) { Timeout = timeout };
        client.DefaultRequestHeaders.Add(HeaderName, token);
        return client;
    }

    /// <summary>统一拒绝响应：401 + 原因，不回显令牌。</summary>
    public static IResult Reject()
        => Results.Json(new
        {
            ok = false,
            error = "UNAUTHORIZED",
            message = $"缺少或错误的 {HeaderName} 请求头。控制接口只允许本机同一用户调用。"
        }, statusCode: StatusCodes.Status401Unauthorized);
}
