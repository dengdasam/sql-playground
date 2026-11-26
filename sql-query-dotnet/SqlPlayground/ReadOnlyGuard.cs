using System.Text;
using System.Text.RegularExpressions;

namespace SqlPlayground;

/// <summary>
/// 只读语句校验。
///
/// 旧的实现是拿一条黑名单正则扫全文（\b(INSERT|UPDATE|...|REPLACE|...)\b），
/// 它分不清“语句关键字”和“函数名 / 字符串内容 / 注释 / 标识符”，
/// 于是 <c>replace(name,' ','_')</c> 这种标准字符串函数、<c>where x = 'use'</c>
/// 这种字符串内容、<c>-- drop table x</c> 这种注释，都会被误判成写操作拒掉。
///
/// 现在的做法：
///   1. 先剥掉字符串字面量、引号标识符、注释，只留“真正的代码”；
///   2. 校验第一条有效关键字必须落在白名单（SELECT / WITH），其余一律拒绝；
///   3. 再对“代码部分”扫一次黑名单，挡住 <c>WITH x AS (DELETE ...)</c> 这类嵌套写入。
///
/// 剥离的关键是**保持字符位置不变**（被剥离的字符等长替换成空格），
/// 这样后续的正则与偏移量仍然对应原文，行为可预期。
/// </summary>
public static class ReadOnlyGuard
{
    /// <summary>允许作为查询起始的关键字。</summary>
    private static readonly HashSet<string> LeadingAllowed =
        new(StringComparer.OrdinalIgnoreCase) { "SELECT", "WITH" };

    /// <summary>出现在代码部分（字面量/注释已剥离）即视为写入或危险语句。</summary>
    private static readonly Regex Forbidden = new(
        @"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|ATTACH|DETACH|PRAGMA|VACUUM|REINDEX|BEGIN|COMMIT|ROLLBACK|SAVEPOINT|RELEASE|GRANT|REVOKE|EXEC|EXECUTE|OUTFILE|DUMPFILE|LOAD_FILE|SHUTDOWN|KILL)\b",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    /// <summary>语句开头的关键字（跳过前导空白、注释、括号）。</summary>
    private static readonly Regex LeadingKeyword = new(
        @"^[\s(]*([A-Za-z_][A-Za-z_0-9]*)",
        RegexOptions.Compiled);

    /// <summary>
    /// 校验并返回可执行的语句（已去掉首尾空白与结尾分号）。
    /// 不通过则抛 <see cref="ApiException"/>。
    /// </summary>
    public static string Validate(string? sql)
    {
        if (string.IsNullOrWhiteSpace(sql))
            throw new ApiException("EMPTY_SQL", "SQL 为空");

        var trimmed = sql.Trim().TrimEnd(';').Trim();
        if (trimmed.Length == 0)
            throw new ApiException("EMPTY_SQL", "SQL 为空");

        var code = StripNonCode(trimmed);

        // 只允许单条语句：剥离后残留的分号意味着语句串。
        if (code.Contains(';'))
            throw new ApiException("MULTI_STATEMENT", "一次只执行一条 SQL");

        // 首关键字白名单：注释、括号等已被剥离，这里拿到的是真正的起始关键字。
        var m = LeadingKeyword.Match(code);
        if (!m.Success)
            throw new ApiException("READONLY_VIOLATION", "只允许 SELECT / WITH 查询，检测到写入或危险语句");

        var leading = m.Groups[1].Value;
        if (!LeadingAllowed.Contains(leading))
            throw new ApiException("READONLY_VIOLATION",
                $"只允许 SELECT / WITH 查询，当前语句以 {leading.ToUpperInvariant()} 开头");

        // 代码部分再扫黑名单：挡住 CTE 里的 INSERT/UPDATE、SELECT ... INTO OUTFILE 等。
        var hit = Forbidden.Match(code);
        if (hit.Success)
            throw new ApiException("READONLY_VIOLATION",
                $"只允许 SELECT / WITH 查询，检测到写入或危险语句：{hit.Value.ToUpperInvariant()}");

        return trimmed;
    }

    /// <summary>
    /// 把字符串字面量、引号标识符、注释替换成等长空格，返回只剩“代码”的文本。
    /// 支持：'...'、N'...'、"..."、`...`、[...]、-- 行注释、/* */ 块注释。
    /// 字符串里用反斜杠转义或双写引号都按原样处理。
    /// </summary>
    public static string StripNonCode(string sql)
    {
        var sb = new StringBuilder(sql.Length);
        var i = 0;

        void Blank(int from, int to)
        {
            for (var k = from; k < to; k++) sb.Append(sql[k] == '\n' ? '\n' : ' ');
        }

        while (i < sql.Length)
        {
            var c = sql[i];

            // -- 行注释
            if (c == '-' && i + 1 < sql.Length && sql[i + 1] == '-')
            {
                var end = sql.IndexOf('\n', i);
                if (end < 0) end = sql.Length;
                Blank(i, end);
                i = end;
                continue;
            }

            // # 行注释（MySQL）
            if (c == '#')
            {
                var end = sql.IndexOf('\n', i);
                if (end < 0) end = sql.Length;
                Blank(i, end);
                i = end;
                continue;
            }

            // /* */ 块注释；SQLite/MySQL 的优化提示 /*+ ... */ 同样被剥掉
            if (c == '/' && i + 1 < sql.Length && sql[i + 1] == '*')
            {
                var end = sql.IndexOf("*/", i + 2, StringComparison.Ordinal);
                end = end < 0 ? sql.Length : end + 2;
                Blank(i, end);
                i = end;
                continue;
            }

            // '...' 字符串字面量；'' 表示一个单引号，\\ 作为转义（MySQL 默认行为）
            if (c == '\'')
            {
                var j = i + 1;
                while (j < sql.Length)
                {
                    if (sql[j] == '\\' && j + 1 < sql.Length) { j += 2; continue; }
                    if (sql[j] == '\'')
                    {
                        if (j + 1 < sql.Length && sql[j + 1] == '\'') { j += 2; continue; }
                        j++;
                        break;
                    }
                    j++;
                }
                Blank(i, j);
                i = j;
                continue;
            }

            // "..." 双引号：SQLite 里既是字符串也是标识符，统一按引用内容剥掉
            if (c == '"' || c == '`')
            {
                var quote = c;
                var j = i + 1;
                while (j < sql.Length)
                {
                    if (sql[j] == quote)
                    {
                        if (j + 1 < sql.Length && sql[j + 1] == quote) { j += 2; continue; }
                        j++;
                        break;
                    }
                    j++;
                }
                Blank(i, j);
                i = j;
                continue;
            }

            // [ ... ] SQL Server 标识符
            if (c == '[')
            {
                var end = sql.IndexOf(']', i + 1);
                end = end < 0 ? sql.Length : end + 1;
                Blank(i, end);
                i = end;
                continue;
            }

            sb.Append(c);
            i++;
        }

        return sb.ToString();
    }
}
