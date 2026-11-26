using System.Data.Common;

namespace SqlPlayground;

/// <summary>
/// SQL 查询服务：只读连接配置的数据库（SQLite / MySQL / SQL Server），
/// 执行 SELECT/WITH 并返回统一结果集。
/// </summary>
public sealed class QueryService
{
    private readonly DbConfig _cfg;

    public QueryService(IWebHostEnvironment env)
    {
        _cfg = DbConfig.Load(Environment.GetEnvironmentVariable("SQL_DB_CONFIG"), env.ContentRootPath);
    }

    public string DatabasePath => _cfg.Provider == "sqlite" ? _cfg.SqlitePath : _cfg.Database;
    public string Provider => _cfg.Provider;
    public string Engine => _cfg.Provider switch
    {
        "mysql" => "MySQL (MySqlConnector)",
        "sqlserver" => "SQL Server (Microsoft.Data.SqlClient)",
        _ => "SQLite (Microsoft.Data.Sqlite)"
    };
    public string Target => _cfg.MaskedTarget();
    public int MaxRows => _cfg.MaxRows;
    public TimeSpan QueryTimeout => TimeSpan.FromSeconds(_cfg.TimeoutSeconds);

    private DbConnection Open() => _cfg.Open();

    private string Quote(string name) => _cfg.Provider switch
    {
        "mysql" => "`" + name.Replace("`", "``") + "`",
        "sqlserver" => "[" + name.Replace("]", "]]") + "]",
        _ => "\"" + name.Replace("\"", "\"\"") + "\""
    };

    // ---------- 元数据 ----------

    public object Tables()
    {
        using var con = Open();
        var list = new List<object>();

        if (_cfg.Provider == "sqlite")
        {
            using var cmd = con.CreateCommand();
            cmd.CommandText = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name";
            using var reader = cmd.ExecuteReader();
            var names = new List<string>();
            while (reader.Read()) names.Add(reader.GetString(0));
            reader.Close();
            foreach (var name in names) list.Add(TableInfo(con, name, name, "", ""));
        }
        else if (_cfg.Provider == "mysql")
        {
            using var cmd = con.CreateCommand();
            cmd.CommandText = "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES "
                            + "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_TYPE = 'BASE TABLE' ORDER BY TABLE_NAME";
            using var reader = cmd.ExecuteReader();
            var names = new List<string>();
            while (reader.Read()) names.Add(reader.GetString(0));
            reader.Close();
            foreach (var name in names) list.Add(TableInfo(con, name, name, "", ""));
        }
        else
        {
            var schemaTable = "INFORMATION_SCHEMA.TABLES";
            using var cmd = con.CreateCommand();
            cmd.CommandText = $"SELECT TABLE_SCHEMA, TABLE_NAME FROM {schemaTable} "
                            + "WHERE TABLE_TYPE = 'BASE TABLE' "
                            + "AND TABLE_SCHEMA NOT IN ('sys','information_schema','PerformanceSchema') "
                            + "ORDER BY TABLE_SCHEMA, TABLE_NAME";
            using var reader = cmd.ExecuteReader();
            var found = new List<(string Schema, string Name)>();
            while (reader.Read()) found.Add((reader.GetString(0), reader.GetString(1)));
            reader.Close();
            foreach (var (schema, name) in found) list.Add(TableInfo(con, name, name, schema, schema));
        }
        return new { tables = list, provider = _cfg.Provider, target = Target };
    }

    /// <param name="display">展示给界面的表名</param>
    /// <param name="physical">SQL 中引用的物理表名</param>
    /// <param name="schema">schema 名（SQL Server / PostgreSQL 用）</param>
    /// <param name="columnFilterValue">INFORMATION_SCHEMA.COLUMNS 的 TABLE_SCHEMA 过滤值；空字符串表示不过滤</param>
    private object TableInfo(DbConnection con, string display, string physical, string schema, string columnFilterValue)
    {
        var cols = new List<object>();
        if (_cfg.Provider == "sqlite")
        {
            using var c2 = con.CreateCommand();
            c2.CommandText = $"PRAGMA table_info({Quote(physical)})";
            using var r2 = c2.ExecuteReader();
            while (r2.Read())
                cols.Add(new { cid = r2.GetInt32(0), name = r2.GetString(1), type = r2.GetString(2), pk = r2.GetInt32(5) > 0 });
        }
        else if (_cfg.Provider == "mysql")
        {
            using var c2 = con.CreateCommand();
            c2.CommandText = "SELECT COLUMN_NAME, DATA_TYPE, COLUMN_KEY, ORDINAL_POSITION "
                           + "FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = @t "
                           + "ORDER BY ORDINAL_POSITION";
            AddParam(c2, "@t", physical);
            using var r2 = c2.ExecuteReader();
            var i = 0;
            while (r2.Read())
                cols.Add(new { cid = i++, name = r2.GetString(0), type = r2.GetString(1), pk = r2.GetString(2) == "PRI" });
        }
        else
        {
            using var c2 = con.CreateCommand();
            c2.CommandText = "SELECT COLUMN_NAME, DATA_TYPE, ORDINAL_POSITION "
                           + "FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = @t AND TABLE_SCHEMA = @s "
                           + "ORDER BY ORDINAL_POSITION";
            AddParam(c2, "@t", physical);
            AddParam(c2, "@s", schema);
            using var r2 = c2.ExecuteReader();
            var i = 0;
            while (r2.Read())
                cols.Add(new { cid = i++, name = r2.GetString(0), type = r2.GetString(1), pk = false });
        }

        long rowCount;
        using (var c3 = con.CreateCommand())
        {
            var fullName = !string.IsNullOrEmpty(schema) ? Quote(schema) + "." + Quote(physical) : Quote(physical);
            c3.CommandText = $"SELECT COUNT(*) FROM {fullName}";
            rowCount = Convert.ToInt64(c3.ExecuteScalar());
        }
        return new { name = display, columns = cols, rows = rowCount, schema };
    }

    private static void AddParam(DbCommand cmd, string name, object value)
    {
        var p = cmd.CreateParameter();
        p.ParameterName = name;
        p.Value = value;
        cmd.Parameters.Add(p);
    }

    // ---------- 查询 ----------

    public object Query(string? sql)
    {
        // 只读校验集中在 ReadOnlyGuard：剥离字面量/注释后按首关键字白名单判定，
        // 不再全文扫黑名单（否则 replace() 这类标准函数会被误拦）。
        var trimmed = ReadOnlyGuard.Validate(sql);

        using var con = Open();
        using var cmd = con.CreateCommand();
        cmd.CommandText = trimmed;
        cmd.CommandTimeout = (int)QueryTimeout.TotalSeconds;

        var started = System.Diagnostics.Stopwatch.GetTimestamp();
        string[] columns;
        var rows = new List<object?[]>();
        using (var reader = cmd.ExecuteReader())
        {
            columns = Enumerable.Range(0, reader.FieldCount).Select(reader.GetName).ToArray();
            while (reader.Read() && rows.Count < MaxRows + 1)
            {
                var row = new object?[reader.FieldCount];
                for (var i = 0; i < reader.FieldCount; i++)
                {
                    var value = reader.IsDBNull(i) ? null : reader.GetValue(i);
                    // MySQL/MariaDB 的 DECIMAL 可能返回 byte[]；转成字符串避免 JSON 变成 base64
                    if (value is byte[] bytes && bytes.Length <= 256)
                    {
                        try { value = System.Text.Encoding.UTF8.GetString(bytes); }
                        catch { value = Convert.ToHexString(bytes); }
                    }
                    row[i] = value;
                }
                rows.Add(row);
            }
        }
        var truncated = rows.Count > MaxRows;
        if (truncated) rows.RemoveRange(MaxRows, rows.Count - MaxRows);
        var elapsed = Math.Round(System.Diagnostics.Stopwatch.GetElapsedTime(started).TotalMilliseconds, 2);
        return new { columns, rows, rowCount = rows.Count, truncated, elapsedMs = elapsed, sql = trimmed, provider = _cfg.Provider };
    }

    // ---------- 预置统计 ----------

    public object Stats()
    {
        var (dayExpr, daysAgo) = _cfg.Provider switch
        {
            "mysql" => ("DATE(creation_date)", "DATE_SUB(CURDATE(), INTERVAL 29 DAY)"),
            "sqlserver" => ("CAST(creation_date AS DATE)", "DATEADD(DAY, -29, CAST(GETDATE() AS DATE))"),
            _ => ("date(creation_date)", "date('now','-29 days')")
        };

        object Daily(string table)
        {
            try
            {
                using var con = Open();
                using var cmd = con.CreateCommand();
                cmd.CommandText = $"SELECT {dayExpr} AS d, COUNT(*) AS cnt FROM {Quote(table)} "
                                + $"WHERE {dayExpr} >= {daysAgo} GROUP BY {dayExpr} ORDER BY d";
                using var reader = cmd.ExecuteReader();
                var list = new List<object>();
                while (reader.Read())
                    list.Add(new { date = Convert.ToString(reader.GetValue(0)), count = Convert.ToInt32(reader.GetValue(1)) });
                return list;
            }
            catch (Exception ex)
            {
                // 连到别的库时这两张 WMS 表可能不存在，不要拖垮整个统计接口
                return new { error = ex.Message };
            }
        }
        return new
        {
            inbound = Daily("winv_inbound_order_lines"),
            batch = Daily("wmdm_batch"),
            provider = _cfg.Provider,
            target = Target
        };
    }

    // ---------- 连接测试（用调用方传入的配置，不依赖当前实例） ----------

    public static object Test(DbConfig cfg)
    {
        var started = System.Diagnostics.Stopwatch.GetTimestamp();
        try
        {
            using var con = cfg.Open();
            using var cmd = con.CreateCommand();
            cmd.CommandText = "SELECT 1";
            cmd.CommandTimeout = Math.Clamp(cfg.TimeoutSeconds, 1, 120);
            cmd.ExecuteScalar();
            string serverVersion;
            try { serverVersion = con.ServerVersion; }
            catch { serverVersion = ""; }
            return new
            {
                ok = true,
                provider = cfg.Provider,
                target = cfg.MaskedTarget(),
                version = serverVersion,
                elapsedMs = Math.Round(System.Diagnostics.Stopwatch.GetElapsedTime(started).TotalMilliseconds, 2)
            };
        }
        catch (Exception ex)
        {
            return new
            {
                ok = false,
                provider = cfg.Provider,
                target = cfg.MaskedTarget(),
                error = ex.Message,
                elapsedMs = Math.Round(System.Diagnostics.Stopwatch.GetElapsedTime(started).TotalMilliseconds, 2)
            };
        }
    }
}
