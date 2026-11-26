using System.Data.Common;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace SqlPlayground;

/// <summary>
/// 数据源配置。由控制器通过环境变量 SQL_DB_CONFIG 传入（JSON）。
/// 未配置时全部回落默认值 —— 保持原来的本地 wms.db 行为不变。
/// </summary>
public sealed class DbConfig
{
    private static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web)
    {
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull
    };

    /// <summary>sqlite / mysql / sqlserver</summary>
    public string Provider { get; set; } = "sqlite";

    /// <summary>SQLite 文件路径；相对路径按后端工作目录解析。</summary>
    public string SqlitePath { get; set; } = "wms.db";

    public string Host { get; set; } = "127.0.0.1";
    public int Port { get; set; } = 3306;
    public string Database { get; set; } = "";
    public string User { get; set; } = "";
    public string Password { get; set; } = "";
    public bool Encrypt { get; set; } = true;
    public bool TrustServerCertificate { get; set; } = true;
    public int TimeoutSeconds { get; set; } = 5;
    public int MaxRows { get; set; } = 500;

    public static DbConfig Load(string? json, string contentRoot)
    {
        var cfg = new DbConfig();
        if (!string.IsNullOrWhiteSpace(json))
        {
            try
            {
                cfg = JsonSerializer.Deserialize<DbConfig>(json, Json) ?? cfg;
            }
            catch { /* 配置损坏就回落默认值，不让服务起不来 */ }
        }
        cfg.Provider = NormalizeProvider(cfg.Provider);
        if (cfg.Port <= 0) cfg.Port = cfg.Provider switch
        {
            "mysql" => 3306,
            "sqlserver" => 1433,
            _ => 0
        };
        if (cfg.TimeoutSeconds <= 0) cfg.TimeoutSeconds = 5;
        if (cfg.MaxRows <= 0) cfg.MaxRows = 500;
        if (!string.IsNullOrWhiteSpace(cfg.SqlitePath) && !Path.IsPathRooted(cfg.SqlitePath))
            cfg.SqlitePath = Path.Combine(contentRoot, cfg.SqlitePath);
        return cfg;
    }

    public string ToJson() => JsonSerializer.Serialize(this, Json);

    public static string NormalizeProvider(string? p) => (p ?? "").Trim().ToLowerInvariant() switch
    {
        "mysql" or "mariadb" => "mysql",
        "sqlserver" or "mssql" or "sql server" => "sqlserver",
        _ => "sqlite"
    };

    /// <summary>日志/前端展示用：绝不输出密码。</summary>
    public string MaskedTarget() => Provider switch
    {
        "sqlite" => "SQLite · " + Path.GetFileName(SqlitePath),
        "mysql" => $"MySQL · {Host}:{Port}/{Database} · {User}",
        "sqlserver" => $"SQL Server · {Host}:{Port}/{Database} · {User}",
        _ => "SQLite"
    };

    public string ConnectionString()
    {
        switch (Provider)
        {
            case "mysql":
            {
                var b = new MySqlConnector.MySqlConnectionStringBuilder
                {
                    Server = Host,
                    Port = (uint)Port,
                    Database = Database,
                    UserID = User,
                    Password = Password,
                    ConnectionTimeout = (uint)Math.Clamp(TimeoutSeconds, 1, 120),
                    DefaultCommandTimeout = (uint)Math.Clamp(TimeoutSeconds, 1, 120),
                    AllowUserVariables = false,
                    SslMode = MySqlConnector.MySqlSslMode.Preferred
                };
                return b.ConnectionString;
            }
            case "sqlserver":
            {
                var b = new Microsoft.Data.SqlClient.SqlConnectionStringBuilder
                {
                    DataSource = Port == 1433 ? Host : $"{Host},{Port}",
                    InitialCatalog = Database,
                    UserID = User,
                    Password = Password,
                    Encrypt = Encrypt,
                    TrustServerCertificate = TrustServerCertificate,
                    ConnectTimeout = Math.Clamp(TimeoutSeconds, 1, 120),
                    ApplicationIntent = Microsoft.Data.SqlClient.ApplicationIntent.ReadOnly
                };
                return b.ConnectionString;
            }
            default:
            {
                var b = new Microsoft.Data.Sqlite.SqliteConnectionStringBuilder
                {
                    DataSource = SqlitePath,
                    Mode = Microsoft.Data.Sqlite.SqliteOpenMode.ReadOnly,
                    Cache = Microsoft.Data.Sqlite.SqliteCacheMode.Shared,
                    Pooling = true,
                    DefaultTimeout = Math.Clamp(TimeoutSeconds, 1, 120)
                };
                return b.ConnectionString;
            }
        }
    }

    public DbConnection Open()
    {
        DbConnection con = Provider switch
        {
            "mysql" => new MySqlConnector.MySqlConnection(ConnectionString()),
            "sqlserver" => new Microsoft.Data.SqlClient.SqlConnection(ConnectionString()),
            _ => new Microsoft.Data.Sqlite.SqliteConnection(ConnectionString())
        };
        con.Open();

        // 二次防线：MySQL 会话级只读事务，真正的 UPDATE/INSERT 会被数据库拒绝。
        // 主防线仍是 SQL 白名单；生产环境务必使用只读账号。
        if (Provider == "mysql")
        {
            using var cmd = con.CreateCommand();
            cmd.CommandText = "SET SESSION TRANSACTION READ ONLY";
            cmd.ExecuteNonQuery();
        }
        return con;
    }
}
