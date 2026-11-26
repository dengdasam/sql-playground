using System.Text;
using SqlPlayground;

try { Console.OutputEncoding = Encoding.UTF8; } catch { }

var builder = WebApplication.CreateBuilder(args);

// 监听地址：控制器通过 API_URL 传入，单独调试默认 5180
var listenUrl = Environment.GetEnvironmentVariable("API_URL") ?? "http://127.0.0.1:5180";
if (!args.Any(a => a.StartsWith("--urls", StringComparison.OrdinalIgnoreCase)))
    builder.WebHost.UseUrls(listenUrl);
builder.WebHost.ConfigureKestrel(o => o.AddServerHeader = false);

// 单实例：同名端口只跑一个后端
static string MutexKey(string url) => new(url.Where(char.IsLetterOrDigit).ToArray());
var backendMutexName = @"Local\SqlPlaygroundBackend_" + MutexKey(listenUrl);
using var backendSingle = new Mutex(true, backendMutexName, out var isFirstBackend);
if (!isFirstBackend)
{
    Console.Error.WriteLine($"[{DateTime.Now:HH:mm:ss}] 监听地址 {listenUrl} 上已有主服务在运行，本次不重复启动。");
    Environment.ExitCode = 0;
    return;
}

builder.Services.AddSingleton<QueryService>();

// 响应压缩：页面与查询结果 JSON 都能压，本地回环也省一次拷贝与解析开销
builder.Services.AddResponseCompression(o =>
{
    o.EnableForHttps = true;
    o.Providers.Add<Microsoft.AspNetCore.ResponseCompression.BrotliCompressionProvider>();
    o.Providers.Add<Microsoft.AspNetCore.ResponseCompression.GzipCompressionProvider>();
    o.MimeTypes = Microsoft.AspNetCore.ResponseCompression.ResponseCompressionDefaults.MimeTypes
        .Concat(new[] { "application/json" });
});
builder.Services.Configure<Microsoft.AspNetCore.ResponseCompression.BrotliCompressionProviderOptions>(
    o => o.Level = System.IO.Compression.CompressionLevel.Fastest);
builder.Services.Configure<Microsoft.AspNetCore.ResponseCompression.GzipCompressionProviderOptions>(
    o => o.Level = System.IO.Compression.CompressionLevel.Fastest);

// 日志：单行、无颜色、默认 Warning（控制器传 API_LOG_LEVEL=Information 时看得到请求流水）
var logLevel = Enum.TryParse<LogLevel>(Environment.GetEnvironmentVariable("API_LOG_LEVEL"), ignoreCase: true, out var parsed)
    ? parsed : LogLevel.Warning;
builder.Logging.ClearProviders();
builder.Logging.AddSimpleConsole(o =>
{
    o.SingleLine = true;
    o.IncludeScopes = false;
    o.ColorBehavior = Microsoft.Extensions.Logging.Console.LoggerColorBehavior.Disabled;
});
builder.Logging.SetMinimumLevel(logLevel);

var app = builder.Build();
app.UseResponseCompression();
app.UseDefaultFiles();
app.UseStaticFiles();
app.UseRequestLog();

// 让控制器能拿到数据库真实路径
var queryService = app.Services.GetRequiredService<QueryService>();

app.MapGet("/api/health", () => ApiWrap.Run(() => new
{
    ok = true,
    service = "SqlPlayground",
    provider = queryService.Provider,
    db = Path.GetFileName(queryService.DatabasePath),
    target = queryService.Target,
    engine = queryService.Engine,
    maxRows = queryService.MaxRows
}));

// GUI 设置窗口「测试连接」用：用请求里带的配置试连，不影响当前正在使用的连接
app.MapPost("/api/connection/test", async (HttpRequest request) =>
    await ApiWrap.RunAsync(async () =>
    {
        var body = await PostBody.ReadObjectAsync(request);
        var json = body.Str("config");
        if (string.IsNullOrWhiteSpace(json))
            throw new ApiException("EMPTY_CONFIG", "缺少 config 参数");
        var cfg = DbConfig.Load(json, app.Environment.ContentRootPath);
        // 密码由 GUI 单独传；允许前端只给脱敏配置，避免密码出现在 history
        var password = body.Str("password");
        if (password is not null) cfg.Password = password;
        var result = QueryService.Test(cfg);
        // Test 返回匿名对象且带 ok 字段，用反射读；失败转成业务错误让前端统一显示
        var okProp = result?.GetType().GetProperty("ok");
        var ok = okProp?.GetValue(result) is true;
        if (!ok)
        {
            var error = result?.GetType().GetProperty("error")?.GetValue(result) as string;
            throw new ApiException("CONNECTION_FAILED", error ?? "连接失败");
        }
        return result;
    }));

app.MapGet("/api/tables", () => ApiWrap.Run(() =>
    app.Services.GetRequiredService<QueryService>().Tables()));

app.MapGet("/api/stats", () => ApiWrap.Run(() =>
    app.Services.GetRequiredService<QueryService>().Stats()));

app.MapPost("/api/query", async (HttpRequest request) =>
    await ApiWrap.RunAsync(async () =>
    {
        var body = await PostBody.ReadObjectAsync(request);
        var sql = body.Str("sql");
        return app.Services.GetRequiredService<QueryService>().Query(sql);
    }));

// 控制器优雅停止用
app.MapPost("/_internal/shutdown", () =>
{
    _ = Task.Run(async () => { await Task.Delay(200); app.Lifetime.StopApplication(); });
    return Results.Ok(new { stopping = true });
});

// 父进程看护：控制器被强杀时后端自杀，不留孤儿
if (int.TryParse(Environment.GetEnvironmentVariable("API_PARENT_PID"), out var parentPid) && parentPid > 0)
{
    _ = Task.Run(async () =>
    {
        while (true)
        {
            await Task.Delay(2000);
            try
            {
                var parent = System.Diagnostics.Process.GetProcessById(parentPid);
                parent.Dispose();
            }
            catch { app.Lifetime.StopApplication(); return; }
        }
    });
}

app.Logger.LogInformation("SqlPlayground 已就绪：{Url}，数据库 {Db}", listenUrl, queryService.DatabasePath);

try { app.Run(); }
catch (IOException ex)
{
    Console.Error.WriteLine($"启动失败：端口 {listenUrl} 可能被占用。{ex.Message}");
    Environment.ExitCode = 1;
}
