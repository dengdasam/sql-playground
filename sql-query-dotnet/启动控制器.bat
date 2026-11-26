@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================
echo   SQL 查询实验室 - .NET 全栈版
echo ============================================
echo.
echo 正在启动 WPF 托盘控制器...
echo 控制器页面: http://127.0.0.1:5288
echo 后端 API:   http://127.0.0.1:5280 （由托盘控制）
echo.
echo 启动后：
echo   1. 托盘图标（绿色=服务运行中）右键可启停/查看日志/设置
echo   2. 双击托盘图标唤回主窗口
echo   3. 浏览器打开 http://127.0.0.1:5288 写 SQL 查询
echo   4. 换数据库：设置 - 数据源 - 选 SQLite/MySQL/SQL Server - 测试连接 - 保存
echo      （保存后自动重启后端；配置存 logs\db-settings.json，密码不写日志）
echo.
dotnet run --project SqlController --no-build
if errorlevel 1 (
  echo.
  echo 启动失败。请先执行一次编译：
  echo   dotnet build SqlController\SqlController.csproj
  echo   dotnet build SqlPlayground\SqlPlayground.csproj
  pause
)
