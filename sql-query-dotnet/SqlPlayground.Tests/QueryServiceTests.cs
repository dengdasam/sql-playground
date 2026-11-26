using Microsoft.AspNetCore.Hosting;
using Microsoft.Extensions.FileProviders;

namespace SqlPlayground.Tests;

/// <summary>
/// 端到端用例：真正连上仓库自带的 wms.db 执行 SQL，
/// 确认「校验通过」之后数据库这一层也确实能返回结果。
/// </summary>
public class QueryServiceTests
{
    private static string ContentRoot
    {
        get
        {
            // 测试程序集在 ...\sql-query-dotnet\SqlPlayground.Tests\bin\<cfg>\net10.0\
            // 向上逐级找同时含 SqlPlayground.csproj 的兄弟目录
            var dir = new DirectoryInfo(AppContext.BaseDirectory);
            while (dir is not null)
            {
                var candidate = Path.Combine(dir.FullName, "SqlPlayground");
                if (File.Exists(Path.Combine(candidate, "SqlPlayground.csproj")))
                    return candidate;
                dir = dir.Parent;
            }
            throw new InvalidOperationException("找不到 SqlPlayground 项目目录");
        }
    }

    private static QueryService CreateService()
    {
        var root = ContentRoot;
        Environment.SetEnvironmentVariable("SQL_DB_CONFIG",
            $"{{\"provider\":\"sqlite\",\"sqlitePath\":{System.Text.Json.JsonSerializer.Serialize(Path.Combine(root, "wms.db"))}}}");
        return new QueryService(new FakeEnv(root));
    }

    [Fact]
    public void Replace_function_now_works()
    {
        // 旧实现在这里抛 READONLY_VIOLATION，这正是本次修复的核心
        var svc = CreateService();
        var json = System.Text.Json.JsonSerializer.Serialize(
            svc.Query("SELECT name, replace(name, ' ', '_') AS code FROM world LIMIT 3"));

        Assert.Contains("\"rowCount\":3", json);
        Assert.DoesNotContain("READONLY_VIOLATION", json);
    }

    [Fact]
    public void String_literal_with_keyword_now_works()
    {
        var svc = CreateService();
        var json = System.Text.Json.JsonSerializer.Serialize(
            svc.Query("SELECT name FROM world WHERE name = 'use'"));
        Assert.Contains("\"rowCount\":0", json);
    }

    [Fact]
    public void Write_statement_still_blocked()
    {
        var svc = CreateService();
        var ex = Assert.Throws<ApiException>(() => svc.Query("DELETE FROM emp"));
        Assert.Equal("READONLY_VIOLATION", ex.Code);
    }

    [Fact]
    public void Basic_query_returns_rows()
    {
        var svc = CreateService();
        var json = System.Text.Json.JsonSerializer.Serialize(
            svc.Query("SELECT name, salary FROM emp ORDER BY salary DESC LIMIT 5"));
        Assert.Contains("\"columns\":[\"name\",\"salary\"]", json);
        Assert.Contains("Jim", json);
    }

    private sealed class FakeEnv(string root) : IWebHostEnvironment
    {
        public string ApplicationName { get; set; } = "SqlPlayground.Tests";
        public IFileProvider WebRootFileProvider { get; set; } = new NullFileProvider();
        public string WebRootPath { get; set; } = Path.Combine(root, "wwwroot");
        public string EnvironmentName { get; set; } = "Development";
        public string ContentRootPath { get; set; } = root;
        public IFileProvider ContentRootFileProvider { get; set; } = new NullFileProvider();
    }
}
