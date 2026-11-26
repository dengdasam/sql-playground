using System.Diagnostics;
using System.IO;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using Microsoft.Win32;

namespace SqlController;

/// <summary>
/// 设置弹窗（A 冷调文档感）：启动偏好 + 数据源配置 + 「关于」。
/// 数据源的「测试连接」通过控制器反代调后端 /api/connection/test，
/// 用当前填写的参数试连（不落盘、不影响正在运行的连接）。
/// </summary>
public partial class SettingsWindow : Window
{
    private readonly string _noticePath;
    private readonly string _controllerUrl;
    private readonly DbSettings _db;
    private bool _busy;

    public SettingsWindow(bool autoOpenBrowser, bool exitOnClose,
                          string iconCredit, string noticePath,
                          DbSettings db, string controllerUrl)
    {
        InitializeComponent();
        _noticePath = noticePath;
        _controllerUrl = controllerUrl;
        _db = db;

        ChkAutoOpen.IsChecked = autoOpenBrowser;
        CmbClose.SelectedIndex = exitOnClose ? 1 : 0;
        CreditText.Text = "应用图标：" + iconCredit;

        // 回填数据源
        var provider = DbProvider.Normalize(db.Provider);
        CmbProvider.SelectedIndex = provider switch { "mysql" => 1, "sqlserver" => 2, _ => 0 };
        TxtSqlitePath.Text = db.SqlitePath;
        TxtHost.Text = db.Host;
        TxtPort.Text = db.Port.ToString();
        TxtDatabase.Text = db.Database;
        TxtUser.Text = db.User;
        PwdBox.Password = db.Password;
        ChkEncrypt.IsChecked = db.Encrypt;
        ChkTrustCert.IsChecked = db.TrustServerCertificate;
        TxtTimeout.Text = db.TimeoutSeconds.ToString();
        TxtMaxRows.Text = db.MaxRows.ToString();
        ApplyProviderVisibility();

        CmbClose.SelectionChanged += (_, _) => UpdateCloseHint();
        UpdateCloseHint();

        BtnSave.Click += BtnSave_Click;
        BtnCancel.Click += (_, _) => { DialogResult = false; Close(); };
        BtnNotice.Click += (_, _) => OpenNotice();
    }

    /// <summary>把界面上的数据源值写回配置对象；调用方负责 Save 与重启后端。</summary>
    public void CollectDb(DbSettings target)
    {
        target.Provider = DbProvider.Normalize((CmbProvider.SelectedItem as ComboBoxItem)?.Tag?.ToString());
        target.SqlitePath = TxtSqlitePath.Text.Trim();
        if (string.IsNullOrWhiteSpace(target.SqlitePath)) target.SqlitePath = "wms.db";
        target.Host = TxtHost.Text.Trim();
        if (string.IsNullOrWhiteSpace(target.Host)) target.Host = "127.0.0.1";
        target.Port = int.TryParse(TxtPort.Text.Trim(), out var port) ? port : 0;
        target.Database = TxtDatabase.Text.Trim();
        target.User = TxtUser.Text.Trim();
        target.Password = PwdBox.Password;
        target.Encrypt = ChkEncrypt.IsChecked == true;
        target.TrustServerCertificate = ChkTrustCert.IsChecked == true;
        target.TimeoutSeconds = int.TryParse(TxtTimeout.Text.Trim(), out var t) ? t : 5;
        target.MaxRows = int.TryParse(TxtMaxRows.Text.Trim(), out var m) ? m : 500;
    }

    // ---------- 界面事件 ----------

    private void ProviderChanged(object sender, SelectionChangedEventArgs e)
    {
        if (CmbProvider is null || PanelSqlite is null) return;  // InitializeComponent 期间的回调
        ApplyProviderVisibility();
    }

    private void ApplyProviderVisibility()
    {
        var p = DbProvider.Normalize((CmbProvider.SelectedItem as ComboBoxItem)?.Tag?.ToString());
        PanelSqlite.Visibility = p == "sqlite" ? Visibility.Visible : Visibility.Collapsed;
        PanelNetwork.Visibility = p == "sqlite" ? Visibility.Collapsed : Visibility.Visible;
        PanelSqlServer.Visibility = p == "sqlserver" ? Visibility.Visible : Visibility.Collapsed;
        TestResult.Text = "";

        // 切换类型时给一个合理的默认端口
        var expected = p switch { "mysql" => "3306", "sqlserver" => "1433", _ => TxtPort.Text };
        if (p != _lastProvider) { TxtPort.Text = expected; _lastProvider = p; }
    }
    private string _lastProvider = "sqlite";

    private void BrowseSqlite(object sender, RoutedEventArgs e)
    {
        var dlg = new Microsoft.Win32.OpenFileDialog
        {
            Title = "选择 SQLite 数据库文件",
            Filter = "SQLite 数据库 (*.db;*.sqlite;*.sqlite3)|*.db;*.sqlite;*.sqlite3|所有文件 (*.*)|*.*",
            FileName = TxtSqlitePath.Text
        };
        if (dlg.ShowDialog() == true) TxtSqlitePath.Text = dlg.FileName;
    }

    private async void BtnTest_Click(object sender, RoutedEventArgs e) => await TestAsync();

    private async Task TestAsync()
    {
        if (_busy) return;
        _busy = true;
        BtnTest.IsEnabled = false;
        TestResult.Foreground = Brush("#8A959C");
        TestResult.Text = "正在连接…";
        try
        {
            var probe = new DbSettings();
            CollectDb(probe);

            using var http = new HttpClient(new HttpClientHandler { UseProxy = false }) { Timeout = TimeSpan.FromSeconds(12) };
            var json = JsonSerializer.Serialize(new { config = probe.ToJson(), password = probe.Password });
            using var content = new StringContent(json, Encoding.UTF8, "application/json");
            using var resp = await http.PostAsync(_controllerUrl.TrimEnd('/') + "/api/connection/test", content);
            var text = await resp.Content.ReadAsStringAsync();
            using var doc = JsonDocument.Parse(text);
            var root = doc.RootElement;
            var success = root.TryGetProperty("success", out var s) && s.GetBoolean();

            if (success && root.TryGetProperty("data", out var data) && data.ValueKind == JsonValueKind.Object)
            {
                var target = data.TryGetProperty("target", out var t) ? t.GetString() : probe.MaskedTarget();
                var ms = data.TryGetProperty("elapsedMs", out var el) ? el.GetDouble() : 0;
                var version = data.TryGetProperty("version", out var v) ? v.GetString() : "";
                TestResult.Foreground = Brush("#2E7D4F");
                TestResult.Text = $"✓ 连接成功 · {target} · {ms:0} ms" + (string.IsNullOrEmpty(version) ? "" : $" · {version}");
            }
            else
            {
                string msg = "连接失败";
                if (root.TryGetProperty("error", out var err) && err.ValueKind == JsonValueKind.Object
                    && err.TryGetProperty("message", out var m)) msg = m.GetString() ?? msg;
                TestResult.Foreground = Brush("#C0392B");
                TestResult.Text = "✖ " + msg;
            }
        }
        catch (Exception ex)
        {
            TestResult.Foreground = Brush("#C0392B");
            TestResult.Text = "✖ " + ex.Message;
        }
        finally
        {
            _busy = false;
            BtnTest.IsEnabled = true;
        }
    }

    private void BtnSave_Click(object sender, RoutedEventArgs e)
    {
        // 保存前先校验数值范围，避免后端启动时回落默认值造成困惑
        if (!int.TryParse(TxtTimeout.Text.Trim(), out var t) || t < 1 || t > 120)
        {
            System.Windows.MessageBox.Show("超时需为 1~120 之间的整数。", "数据源设置", MessageBoxButton.OK, MessageBoxImage.Warning);
            return;
        }
        if (!int.TryParse(TxtMaxRows.Text.Trim(), out var m) || m < 1 || m > 10000)
        {
            System.Windows.MessageBox.Show("最大返回行数需为 1~10000 之间的整数。", "数据源设置", MessageBoxButton.OK, MessageBoxImage.Warning);
            return;
        }
        var provider = DbProvider.Normalize((CmbProvider.SelectedItem as ComboBoxItem)?.Tag?.ToString());
        if (provider != "sqlite")
        {
            if (string.IsNullOrWhiteSpace(TxtDatabase.Text.Trim()))
            {
                System.Windows.MessageBox.Show("请填写数据库名。", "数据源设置", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }
            if (!int.TryParse(TxtPort.Text.Trim(), out var p) || p < 1 || p > 65535)
            {
                System.Windows.MessageBox.Show("端口需为 1~65535 之间的整数。", "数据源设置", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }
        }
        DialogResult = true;
        Close();
    }

    // ---------- 偏好 ----------

    public bool AutoOpenBrowser => ChkAutoOpen.IsChecked == true;
    public bool ExitOnClose => CmbClose.SelectedIndex == 1;

    private void UpdateCloseHint() => CloseHint.Text = ExitOnClose
        ? "点 × 会优雅停止主服务并退出控制器，端口全部释放；托盘菜单「退出」行为不变。"
        : "点 × 只隐藏窗口，主服务继续运行；双击托盘图标或再次双击 exe 可唤回窗口。";

    private static System.Windows.Media.SolidColorBrush Brush(string hex)
    {
        var h = hex.TrimStart('#');
        var color = System.Windows.Media.Color.FromRgb(
            Convert.ToByte(h.Substring(0, 2), 16),
            Convert.ToByte(h.Substring(2, 2), 16),
            Convert.ToByte(h.Substring(4, 2), 16));
        return new System.Windows.Media.SolidColorBrush(color);
    }

    private void OpenNotice()
    {
        try
        {
            if (!File.Exists(_noticePath)) { CloseHint.Text = "许可文件不存在：" + _noticePath; return; }
            Process.Start(new ProcessStartInfo(_noticePath) { UseShellExecute = true });
        }
        catch (System.Exception ex)
        {
            CloseHint.Text = "无法打开许可文件：" + ex.Message;
        }
    }
}

internal static class DbProvider
{
    public static string Normalize(string? p) => (p ?? "").Trim().ToLowerInvariant() switch
    {
        "mysql" or "mariadb" => "mysql",
        "sqlserver" or "mssql" or "sql server" => "sqlserver",
        _ => "sqlite"
    };
}
