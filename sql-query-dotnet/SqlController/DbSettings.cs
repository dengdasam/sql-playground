using System.Text.Json;
using System.Windows;

namespace SqlController;

/// <summary>
/// 数据源配置（GUI 设置窗口 ↔ 后端）。保存为 logs/db-settings.json，
/// 并在启动后端时通过环境变量 SQL_DB_CONFIG 传给 .NET 后端。
/// 密码单独存字段，界面用 PasswordBox，日志一律脱敏。
/// </summary>
public sealed class DbSettings
{
    private static readonly JsonSerializerOptions JsonOptions = new() { WriteIndented = true };

    public string Provider { get; set; } = "sqlite";
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

    public static string FilePathOf(string root) => Path.Combine(root, "logs", "db-settings.json");

    public static DbSettings Load(string root)
    {
        try
        {
            var path = FilePathOf(root);
            if (File.Exists(path))
            {
                var s = JsonSerializer.Deserialize<DbSettings>(File.ReadAllText(path), JsonOptions);
                if (s is not null) return s;
            }
        }
        catch { /* 配置损坏回落默认 SQLite */ }
        return new DbSettings();
    }

    public void Save(string root)
    {
        try
        {
            var path = FilePathOf(root);
            var dir = Path.GetDirectoryName(path);
            if (!string.IsNullOrEmpty(dir)) Directory.CreateDirectory(dir);
            File.WriteAllText(path, JsonSerializer.Serialize(this, JsonOptions));
        }
        catch (Exception ex)
        {
            System.Windows.MessageBox.Show("配置写入失败：" + ex.Message, "数据源设置", MessageBoxButton.OK, MessageBoxImage.Warning);
        }
    }

    /// <summary>序列化给后端 JSON 环境变量；密码明文只在本机进程间传递。</summary>
    public string ToJson() => JsonSerializer.Serialize(this, JsonOptions);

    public string MaskedTarget() => Provider switch
    {
        "mysql" => $"MySQL · {Host}:{Port}/{Database} · {User}",
        "sqlserver" => $"SQL Server · {Host}:{Port}/{Database} · {User}",
        _ => "SQLite · " + Path.GetFileName(SqlitePath)
    };

    public string ToEnvJson(string root)
    {
        // 相对 SQLite 路径按后端工作目录（SqlPlayground/）解析；GUI 里给的是相对该目录的路径
        return ToJson();
    }
}
