using System.IO;
using Microsoft.AspNetCore.Http;

namespace SqlController.Tests;

/// <summary>
/// /control/* 鉴权的回归测试。
///
/// 背景：/control/stop 原来完全无鉴权，同机任何进程都能把主服务停掉。
/// 这组用例钉住三件事：没令牌拒、错令牌拒、对令牌放行。
/// </summary>
public class ControlAuthTests
{
    private static DefaultHttpContext WithToken(string? token)
    {
        var ctx = new DefaultHttpContext();
        if (token is not null) ctx.Request.Headers[ControlAuth.HeaderName] = token;
        return ctx;
    }

    [Fact]
    public void Token_is_long_and_url_safe()
    {
        var dir = NewTempDir();
        try
        {
            var auth = ControlAuth.Create(dir);
            // 32 字节 base64 去掉 padding = 43 字符
            Assert.Equal(43, auth.Token.Length);
            Assert.DoesNotContain('+', auth.Token);
            Assert.DoesNotContain('/', auth.Token);
            Assert.DoesNotContain('=', auth.Token);
        }
        finally { Cleanup(dir); }
    }

    [Fact]
    public void Rejects_missing_token()
    {
        var dir = NewTempDir();
        try
        {
            var auth = ControlAuth.Create(dir);
            Assert.False(auth.IsAuthorized(WithToken(null).Request));
        }
        finally { Cleanup(dir); }
    }

    [Fact]
    public void Rejects_empty_token()
    {
        var dir = NewTempDir();
        try
        {
            var auth = ControlAuth.Create(dir);
            Assert.False(auth.IsAuthorized(WithToken("").Request));
        }
        finally { Cleanup(dir); }
    }

    [Fact]
    public void Rejects_wrong_token()
    {
        var dir = NewTempDir();
        try
        {
            var auth = ControlAuth.Create(dir);
            Assert.False(auth.IsAuthorized(WithToken(new string('a', 43)).Request));
        }
        finally { Cleanup(dir); }
    }

    [Fact]
    public void Rejects_token_of_different_length()
    {
        var dir = NewTempDir();
        try
        {
            var auth = ControlAuth.Create(dir);
            Assert.False(auth.IsAuthorized(WithToken(auth.Token + "x").Request));
            Assert.False(auth.IsAuthorized(WithToken(auth.Token[..^1]).Request));
        }
        finally { Cleanup(dir); }
    }

    [Fact]
    public void Accepts_correct_token()
    {
        var dir = NewTempDir();
        try
        {
            var auth = ControlAuth.Create(dir);
            Assert.True(auth.IsAuthorized(WithToken(auth.Token).Request));
        }
        finally { Cleanup(dir); }
    }

    [Fact]
    public void Token_is_persisted_for_cross_process_use()
    {
        var dir = NewTempDir();
        try
        {
            var auth = ControlAuth.Create(dir);
            // 第二个实例靠这个文件拿到令牌去调 /control/show
            Assert.Equal(auth.Token, ControlAuth.TryReadExisting(dir));
        }
        finally { Cleanup(dir); }
    }

    [Fact]
    public void Restart_generates_new_token_and_invalidates_old()
    {
        var dir = NewTempDir();
        try
        {
            var first = ControlAuth.Create(dir);
            var second = ControlAuth.Create(dir);

            Assert.NotEqual(first.Token, second.Token);
            // 旧令牌必须失效
            Assert.False(second.IsAuthorized(WithToken(first.Token).Request));
            // 文件里是新令牌
            Assert.Equal(second.Token, ControlAuth.TryReadExisting(dir));
        }
        finally { Cleanup(dir); }
    }

    [Fact]
    public void Missing_file_returns_null()
    {
        var dir = NewTempDir();
        try
        {
            Assert.Null(ControlAuth.TryReadExisting(Path.Combine(dir, "nonexistent-sub")));
        }
        finally { Cleanup(dir); }
    }

    [Fact]
    public void Create_works_when_dir_is_created_lazily()
    {
        var dir = Path.Combine(Path.GetTempPath(), "ctrlauth-" + Guid.NewGuid().ToString("N"), "nested");
        try
        {
            var auth = ControlAuth.Create(dir);
            Assert.True(Directory.Exists(dir));
            Assert.True(auth.IsAuthorized(WithToken(auth.Token).Request));
        }
        finally { Cleanup(Path.GetDirectoryName(dir)!); }
    }

    [Fact]
    public void Reject_returns_401()
    {
        var result = ControlAuth.Reject();
        // Results.Json 返回泛型 JsonHttpResult<T>，T 是匿名类型，只能用接口取状态码
        var statusCode = result.GetType().GetProperty("StatusCode")?.GetValue(result);
        Assert.Equal(401, statusCode);
    }

    // ---------- 辅助 ----------

    private static string NewTempDir()
    {
        var dir = Path.Combine(Path.GetTempPath(), "ctrlauth-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(dir);
        return dir;
    }

    private static void Cleanup(string dir)
    {
        try { if (Directory.Exists(dir)) Directory.Delete(dir, recursive: true); }
        catch { /* 清理失败不影响断言 */ }
    }
}
