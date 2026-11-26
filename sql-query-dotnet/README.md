# SQL 查询实验室 · .NET 版

浏览器里写 SQL，本机 .NET 后端执行，结果自动出表格与图表。**运行时全部是 .NET**，不依赖 Python，也不用敲任何命令。

## 两个版本，按场景选

| | **便携版 `dist\`** | **轻量版 `dist-lite\`** |
|---|---|---|
| 体积 | 154 MB | 10 MB |
| 控制器内存（私有） | 约 260 MB | 约 136 MB |
| 启动到可点页面 | 约 0.1–0.4 秒 | 约 0.4–0.8 秒 |
| 需要装 .NET 运行时 | **不需要** | 需要 .NET 10 桌面运行时 |
| 适用场景 | 换电脑、拷给别人、不想折腾环境 | 本机长期用，想要体积小、内存低 |

**本机已装 .NET 10（你这台就装了）→ 直接用 `dist-lite\SqlController.exe`，更省资源。**
**要拷到没装 .NET 的电脑 → 用 `dist\SqlController.exe`，双击即用。**

## 启动后

- 托盘图标变绿 = 后端已就绪，浏览器打开 `http://127.0.0.1:5288`
- 双击托盘图标唤回主窗口；右键可启停服务、看日志、改设置
- 首次运行若提示"Windows 已保护你的电脑"，点「更多信息」→「仍要运行」（exe 未做代码签名，属正常）

## 目录说明

| 文件 | 作用 |
|---|---|
| `SqlController.exe` | GUI 主程序（WPF + 托盘），托管页面并反代 API |
| `SqlPlayground.exe` | 后端服务（ASP.NET Core），由 GUI 自动拉起，不用手动开 |
| `wms.db` | 默认数据源（SQLite，样例 6 张表） |
| `logs\` | 运行日志、界面偏好、数据源配置 |
| `wwwroot\` | 前端页面 |

两个 exe 独立打包；GUI 启动时会自动找同目录的 `SqlPlayground.exe`，日志里写明「便携版（启动 SqlPlayground.exe）」。

## 改数据源

主窗口「设置」→「数据源」：选类型（SQLite / MySQL / SQL Server）→ 填连接信息 → **测试连接** → **保存**（自动重启后端生效）。

配置存 `logs\db-settings.json`，密码只在本机文件与进程环境变量间传递，**日志一律脱敏**。生产库建议单独建只读账号。

## 题库入口

查询页**顶部横幅**和**左侧栏**都有「SQL 题库」入口，点击在新标签打开：

| 链接 | 页面 |
|---|---|
| `/quiz/practice.html` | 练习场：答题 + 速查双模式，57 题 |
| `/quiz/challenge.html` | 闯关：SQLZoo 式分步引导，57 关 |

这两个页面由 `sql-quiz\build.py` 构建时自动同步到 `SqlPlayground\wwwroot\quiz\`，发布 exe 时随 `wwwroot` 一起打进产物——所以便携版拷到别的电脑，题库入口照样能用。

改题流程：编辑 `sql-quiz\qbank.py` → 运行 `python sql-quiz\build.py`（会自动同步）→ 需要更新 exe 时再跑 `发布.bat`。

## 重新打包

```bat
发布.bat          :: 便携版 → dist\
发布.bat lite     :: 轻量版 → dist-lite\
```

会先停掉运行中的实例、备份 `wms.db`，发布完再恢复，不会丢你改过的数据。

## 性能相关的实现与实测

| 优化 | 效果 |
|---|---|
| Brotli/Gzip 响应压缩 | 首页 28,068 B → 12,001 B（**-57%**），gzip 12,847 B |
| 工作站 GC（关服务器 GC） | 本地单用户不再按核数多留几套堆，控制器内存降约 11% |
| ReadyToRun 预编译（仅便携版） | 控制器 **85 ms** 就绪 |
| 极简 Host（`CreateSlimBuilder`） | 不做 IIS 集成等多余装配，私有内存从约 246 MB 降到 **153 MB**（同配置 Debug 对比） |
| 只读连接 + 500 行上限 | 大表查询不会把页面拖死 |

> 注：框架依赖的单文件**不能**同时开 `PublishReadyToRun`（实测启动即退出），所以轻量版启动比便携版慢一些，这是有意取舍。

## 源码方式（开发调试）

```bat
dotnet build SqlPlayground\SqlPlayground.csproj
dotnet build SqlController\SqlController.csproj
dotnet run --project SqlController --no-build
```

源码模式用 `dotnet SqlPlayground.dll` 启动后端；打包后自动切成直接启动 exe。
