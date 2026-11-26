namespace SqlPlayground.Tests;

/// <summary>
/// 只读校验的回归测试。
///
/// 背景：旧实现用一条黑名单正则扫全文，把 REPLACE / USE / SET 等词一并当成写操作，
/// 导致 <c>replace(name,' ','_')</c>（题库 F6 的标准答案）在查询实验室里直接被拒。
/// 这组用例把"必须放行"和"必须拦截"两类边界都钉住。
/// </summary>
public class ReadOnlyGuardTests
{
    // ---------- 必须放行 ----------

    [Theory]
    // 最基本的正例
    [InlineData("SELECT 1")]
    [InlineData("select * from emp")]
    [InlineData("SELECT name FROM world LIMIT 3")]
    // 回归：replace() 是字符串函数，不是写操作（题库 F6 标准答案）
    [InlineData("SELECT name, replace(name, ' ', '_') AS code FROM world")]
    [InlineData("select REPLACE('a b',' ','_')")]
    // 回归：字符串字面量里的危险词不应触发拦截
    [InlineData("SELECT * FROM world WHERE name = 'use'")]
    [InlineData("SELECT 'drop table x' AS s")]
    [InlineData("SELECT * FROM world WHERE name = 'insert'")]
    // 回归：注释里的危险词不应触发拦截
    [InlineData("SELECT 1 -- drop table x")]
    [InlineData("SELECT 1 /* delete from emp */")]
    // 标识符里含危险词前缀，有词边界保护
    [InlineData("SELECT update_time, created_by FROM t")]
    [InlineData("SELECT last_update FROM t")]
    [InlineData("SELECT * FROM user_use")]
    // 常用语法
    [InlineData("SELECT name, RANK() OVER (ORDER BY salary DESC) FROM emp")]
    [InlineData("WITH x AS (SELECT 1 AS a) SELECT * FROM x")]
    [InlineData("SELECT * FROM emp WHERE dept_id IN (SELECT id FROM dept)")]
    [InlineData("SELECT CASE WHEN salary > 100 THEN 'high' ELSE 'low' END FROM emp")]
    // 结尾分号是允许的，会被去掉
    [InlineData("SELECT 1;")]
    public void Allows_read_only_queries(string sql)
    {
        var result = ReadOnlyGuard.Validate(sql);
        Assert.False(string.IsNullOrWhiteSpace(result));
        Assert.DoesNotContain(";", result);
    }

    [Fact]
    public void Trims_trailing_semicolon()
    {
        Assert.Equal("SELECT 1", ReadOnlyGuard.Validate("  SELECT 1 ;  "));
    }

    // ---------- 必须拦截 ----------

    [Theory]
    [InlineData("DELETE FROM emp")]
    [InlineData("delete from emp")]
    [InlineData("INSERT INTO emp VALUES (1,'a',1,1)")]
    [InlineData("UPDATE emp SET salary = 0")]
    [InlineData("DROP TABLE emp")]
    [InlineData("ALTER TABLE emp ADD COLUMN x INT")]
    [InlineData("CREATE TABLE t (id INT)")]
    [InlineData("TRUNCATE TABLE emp")]
    [InlineData("PRAGMA writable_schema = 1")]
    [InlineData("VACUUM")]
    [InlineData("ATTACH DATABASE 'x.db' AS x")]
    [InlineData("BEGIN TRANSACTION")]
    public void Blocks_write_statements(string sql)
    {
        var ex = Assert.Throws<ApiException>(() => ReadOnlyGuard.Validate(sql));
        Assert.Equal("READONLY_VIOLATION", ex.Code);
    }

    [Fact]
    public void Blocks_cte_with_nested_write()
    {
        // WITH 允许作为起始关键字，但内部藏了写入，必须靠第二道黑名单挡住
        var ex = Assert.Throws<ApiException>(() =>
            ReadOnlyGuard.Validate("WITH x AS (DELETE FROM emp RETURNING *) SELECT * FROM x"));
        Assert.Equal("READONLY_VIOLATION", ex.Code);
    }

    [Fact]
    public void Blocks_select_into_outfile()
    {
        var ex = Assert.Throws<ApiException>(() =>
            ReadOnlyGuard.Validate("SELECT * FROM emp INTO OUTFILE '/tmp/x'"));
        Assert.Equal("READONLY_VIOLATION", ex.Code);
    }

    [Theory]
    [InlineData("SELECT 1; SELECT 2")]
    [InlineData("SELECT 1;DROP TABLE emp")]
    public void Blocks_multiple_statements(string sql)
    {
        var ex = Assert.Throws<ApiException>(() => ReadOnlyGuard.Validate(sql));
        Assert.Equal("MULTI_STATEMENT", ex.Code);
    }

    [Theory]
    [InlineData("")]
    [InlineData("   ")]
    [InlineData(";")]
    [InlineData(null)]
    public void Blocks_empty_sql(string? sql)
    {
        var ex = Assert.Throws<ApiException>(() => ReadOnlyGuard.Validate(sql));
        Assert.Equal("EMPTY_SQL", ex.Code);
    }

    // ---------- 剥离逻辑本身 ----------

    [Fact]
    public void Strip_preserves_length()
    {
        const string sql = "SELECT 'drop', \"delete\", `update`, [insert] FROM t -- alter";
        Assert.Equal(sql.Length, ReadOnlyGuard.StripNonCode(sql).Length);
    }

    [Fact]
    public void Strip_keeps_keywords_outside_quotes()
    {
        var code = ReadOnlyGuard.StripNonCode("SELECT 'drop' FROM t");
        Assert.Contains("SELECT", code);
        Assert.DoesNotContain("drop", code);
    }

    [Fact]
    public void Strip_handles_escaped_quote()
    {
        // 'it''s' 是一个完整字面量，后面的 drop 是注释
        var code = ReadOnlyGuard.StripNonCode("SELECT 'it''s' FROM t -- drop");
        Assert.Contains("FROM", code);
        Assert.DoesNotContain("drop", code);
        Assert.DoesNotContain("it", code);
    }
}
