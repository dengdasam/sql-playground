using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.Logging;

namespace SqlPlayground;

/// <summary>
/// 跨站防护中间件：挂在所有 /api 请求之前。
///
/// 为什么用中间件而不是每个端点各写一行：端点会随功能增加，
/// 只要有人新加一个 /api/xxx 忘了校验，防护就形同虚设。中间件保证不漏。
/// </summary>
public static class OriginGuardMiddleware
{
    public static IApplicationBuilder UseOriginGuard(this IApplicationBuilder app)
    {
        var log = app.ApplicationServices.GetService<ILoggerFactory>()?.CreateLogger("OriginGuard");

        return app.Use(async (ctx, next) =>
        {
            // 只管 /api；静态页面本身要能被任意方式打开
            if (!ctx.Request.Path.StartsWithSegments("/api"))
            {
                await next();
                return;
            }

            var rejection = OriginGuard.Check(ctx.Request);
            if (rejection is null)
            {
                await next();
                return;
            }

            log?.LogWarning("拒绝可疑请求 {Method} {Path}：{Code} {Message}（Origin={Origin}，Host={Host}）",
                ctx.Request.Method, ctx.Request.Path, rejection.Code, rejection.Message,
                ctx.Request.Headers.Origin.ToString(), ctx.Request.Host.ToString());

            ctx.Response.StatusCode = StatusCodes.Status403Forbidden;
            ctx.Response.ContentType = "application/json; charset=utf-8";
            await ctx.Response.WriteAsJsonAsync(new
            {
                success = false,
                data = (object?)null,
                error = new { code = rejection.Code, message = rejection.Message },
                elapsedMs = 0.0,
                timestamp = DateTimeOffset.Now.ToString("O")
            });
        });
    }
}
