# SQL 工具箱

一个本地跑的全栈 SQL 工作台，三块互补的功能打成一个整体：

| 模块 | 用途 | 形态 |
| --- | --- | --- |
| **查询实验室** | 写 SQL 查真实数据库，结果自动出表格和图表 | .NET 后端 + 浏览器页面 |
| **SQL 练习场** | 57 道题，答题 / 速查双模式，写完即判分 | 单文件 HTML |
| **SQL 闯关** | 同样 57 道题，SQLZoo 式分步引导，通过自动进下一关 | 单文件 HTML |

三个页面顶部共用一条导航，随时互跳：

```
SQL 工具箱   [查询实验室]  练习场  闯关
```

题库页面是**真正的离线应用**——内嵌 SQLite 引擎（sql.js + wasm）和全部样例数据，双击就能做题，不联网、不装任何东西。查询实验室才需要本机后端。

---

## 快速开始

### 只想刷题（零依赖，30 秒）

双击仓库里这两个文件之一：

```
sql-quiz/SQL练习场.html    答题 + 速查
sql-quiz/SQL闯关.html      分步引导
```

单文件约 1MB，SQL 在浏览器里用 SQLite 真实执行、与标准答案比对结果集，进度存 localStorage。

### 想查数据库（需要 .NET 10 SDK）

```bash
git clone https://github.com/dengdasam/sql-playground.git
cd sql-playground/sql-query-dotnet

dotnet build SqlPlayground/SqlPlayground.csproj
dotnet build SqlController/SqlController.csproj
dotnet run --project SqlController --no-build
```

然后打开 <http://127.0.0.1:5288/>。

### 跑测试

```bash
cd sql-query-dotnet
dotnet test SqlPlayground.Tests/SqlPlayground.Tests.csproj   # 只读校验 + 真实库查询，46 个用例
dotnet test SqlController.Tests/SqlController.Tests.csproj   # /control/* 鉴权，11 个用例
```

全部离线执行，不连外部服务。

### 想要双击即用的 exe

```bat
cd sql-query-dotnet
发布.bat          :: 便携版，约 154MB，免装运行时，拷到任何 Win10/11 x64 直接跑
发布.bat lite     :: 轻量版，约 13MB，需本机已装 .NET 10 桌面运行时
```

产物在 `dist\` 或 `dist-lite\`，双击其中的 `SqlController.exe`。仓库不提交 exe（体积大），需要自己发布一次。

---

## 架构

```
浏览器  http://127.0.0.1:5288
   │     查询实验室（写 SQL / 表格 / 图表）
   │     练习场、闯关（/quiz/*.html）
   ▼
SqlController  :5288   WPF 托盘 GUI
   │  · 托管静态页面
   │  · /control/{start,stop,status,show}
   │  · /api/*、/quiz/* 反向代理
   ▼  子进程（控制器退出即停）
SqlPlayground  :5280   只监听本机
   │  · /api/query  /api/tables  /api/stats
   │  · /api/connection/test
   │  · 只读连接 + 语句白名单
   ▼
SQLite  /  MySQL  /  SQL Server
```

- **5288**：对外唯一入口。页面、控制接口、API 全走它。
- **5280**：主服务，由控制器拉起。退出控制器时主服务一起退出，不留后台常驻进程。
  > 单独调试后端（不经过控制器）时监听的是 **5180**：控制器会通过 `API_URL` 环境变量把端口传下去，未设置时 `Program.cs` 回落到 `http://127.0.0.1:5180`。
- **托盘图标**：绿色=运行中，灰色=已停止，红色=异常退出。右键可启停服务、重看日志、改设置；双击唤回主窗口。
- **点 × 关闭窗口**只最小化到托盘，服务继续跑（可在「设置」里改成「退出并停止服务」）。

### 控制接口的鉴权

`/control/*` 会改变进程状态（起停主服务、唤窗口），因此全部要求请求头 `X-Control-Token`，否则返回 **401**。

- 令牌在控制器每次启动时随机生成（32 字节），写入 `logs/control-token.txt`，并把该文件 ACL 收紧到**仅当前用户**（`icacls` 可见只剩一个账户）。
- 重启控制器即换新令牌，旧令牌立刻失效。
- 之所以落盘而非纯内存：`/control/show` 是**跨进程**用的——重复双击 exe 时第二个实例要靠它把已有实例的窗口调到前台。
- 页面上没有任何按钮调用这些接口，日常使用无需关心令牌。

> 边界：这挡的是「同机其他账户」和「网页脚本」，不挡「同一用户下的恶意程序」——后者能读你的文件，本机凭据都拦不住，最终得靠系统账号隔离。

---

## 查询实验室

写 SQL → 后端真实执行 → 结果表格 + 自动图表。

**数据源可配**：主窗口「设置」→ 数据源，三选一：

| 类型 | 配置项 |
| --- | --- |
| SQLite | 数据库文件路径（支持相对/绝对） |
| MySQL / MariaDB | 主机、端口（默认 3306）、库名、用户名、密码 |
| SQL Server | 主机、端口（默认 1433）、库名、用户名、密码、Encrypt、TrustServerCertificate |

点「测试连接」先用当前填写值真连一次（不落盘、不影响正在运行的连接），成功显示版本与耗时；点「保存」后自动重启后端，配置立即生效。配置存 `logs/db-settings.json`，**密码只在本机文件与进程环境变量间传递，日志一律脱敏**。

**只读防护**分三层：

1. 连接层：SQLite 用 `mode=ro`；MySQL 加会话级只读事务；SQL Server 用 `ApplicationIntent=ReadOnly`
2. 语句层：`SELECT` / `WITH` 白名单，拦截 `INSERT/UPDATE/DELETE/DROP/...`
3. 执行层：单条语句校验、5 秒超时、500 行上限

> 连生产库时请单独建**只读账号**，这是最后一道保险。

**自动图表**（纯 SVG 手绘，无 CDN 依赖）：结果里有日期列 → 折线图；单指标分类 → 柱状图；占比数据 → 饼图。

**其它**：编辑器草稿自动保存（切到题库再回来不丢）、查询历史、表结构浏览、6 条示例查询。

---

## SQL 题库

57 道题，7 个知识点，每题都带**表字段说明**和**解题步骤**：

| 分类 | 题数 | 覆盖内容 |
| --- | --- | --- |
| 基础查询 | 9 | WHERE / LIKE / BETWEEN / ORDER BY / LIMIT / 别名 / 算术 |
| 聚合分组 | 8 | GROUP BY / HAVING / COUNT / SUM / AVG / 极值 |
| 多表连接 | 7 | JOIN / LEFT JOIN / 反连接 / `COUNT(列)` 与 `COUNT(*)` 的坑 |
| 子查询 | 7 | 标量、IN、EXISTS、相关子查询、分组取极值 |
| 窗口函数 | 7 | RANK / DENSE_RANK / ROW_NUMBER / LAG / 累计求和 / 分组 TopN |
| 条件字符串 | 7 | CASE / 字符串拼接 / replace / length / 条件顺序 |
| WMS 实战 | 12 | 按天统计、UNION 合并、占比、一对多计数放大、NOT IN 的 NULL 陷阱 |

每道题打开就能看到：

- **相关表字段**：本题涉及哪几张表、每个字段的中文含义、类型、示例值——不用猜该写什么字段
- **解题思路**：编号步骤，讲清「先做什么、为什么这么写」，而不是只丢一段 SQL
- **关键语法点**：如 `LEFT JOIN`、`COUNT(DISTINCT)`、`HAVING`
- **完整表结构**：页面底部「样例数据表」逐字段列出 6 张表

判分是**真实执行后比对结果集**：你的 SQL 和标准答案在同一份数据上跑，逐单元格比较（NULL 视为空串），默认忽略行顺序。标注「严格」的题按返回顺序比。

样例数据：`world` / `nobel` / `emp` / `dept` 四张经典表，外加两张简化版 WMS 表（脚本生成最近 40 天数据）。

---

## 目录结构

```
.
├── sql-query-dotnet/          .NET 全栈应用
│   ├── SqlPlayground/         后端（ASP.NET Core，:5280）
│   │   ├── Program.cs         端点注册、压缩、父进程看护
│   │   ├── QueryService.cs    只读查询、元数据、预置统计
│   │   ├── DbConfig.cs        三种数据源的连接串与服务
│   │   ├── wwwroot/           查询页 + quiz/（题库副本）
│   │   └── wms.db             样例 SQLite 库
│   ├── SqlController/         GUI（WPF 托盘，:5288）
│   │   ├── Program.cs         布局探测、反代、控制接口
│   │   ├── BackendProcess.cs  后端进程启停与日志
│   │   └── SettingsWindow.*   设置窗口（启动偏好 + 数据源）
│   ├── README.md              应用详细说明
│   └── 发布.bat               一键打包（默认便携版，lite 出轻量版）
│
└── sql-quiz/                  题库与构建
    ├── SQL练习场.html          成品（可直接双击）
    ├── SQL闯关.html            成品
    ├── qbank.py               题库：TABLE_DICT + 57 道题
    ├── build.py               校验答案 → 生成 HTML → 同步给应用
    └── src/*.template.html     源模板
```

---

## 性能

| 优化 | 效果 |
| --- | --- |
| Brotli / Gzip 响应压缩 | 首页 28,068 B → 12,001 B（**-57%**） |
| ReadyToRun 预编译 | 便携版控制器 **85 ms** 就绪，后端 1 秒内上线 |
| 极简 Host（`CreateSlimBuilder`） | 控制器私有内存 246 MB → **153 MB** |
| 工作站 GC（关服务器 GC） | 桌面单用户场景再省约 11% |
| 页面宽屏自适应 | 移除 1400px / 1000px 双重限宽，1920 屏右侧空白 414px → **0** |

两个 exe 的取舍：

| | 便携版 `dist\` | 轻量版 `dist-lite\` |
| --- | --- | --- |
| 体积 | 154 MB | 13 MB |
| 控制器私有内存 | 260 MB | **136 MB** |
| 启动到可点 | **85 ms** | 416 ms |
| 需要 .NET 运行时 | 不需要 | 需要 .NET 10 桌面运行时 |

---

## 加题 / 改题

```bash
# 编辑 qbank.py 后
python sql-quiz/build.py
```

脚本会先逐题在 SQLite 上执行验证（结果不能为空、必须标注涉及的表和解题步骤），通过后生成两个 HTML，并自动同步到 `sql-query-dotnet/SqlPlayground/wwwroot/quiz/`。

只校验不生成：

```bash
set VALIDATE_ONLY=1        # Windows
VALIDATE_ONLY=1 python build.py
```

---

## 已知限制

- **浏览器内只能跑 SQLite**。题库用 SQLite 方言，MySQL 差异（如 `DATE_SUB(CURDATE(), INTERVAL 29 DAY)` ↔ `date('now','-29 days')`）在题目备注里给了对照写法。
- **查询实验室需要本机后端**。用 GitHub Pages 之类的纯静态托管只能看界面，查不了库。
- **exe 未做代码签名**。首次运行 Windows 可能提示「已保护你的电脑」，点「更多信息 → 仍要运行」即可。
- **数据库请给只读账号**。程序侧的三层防护能挡住误操作，但挡不住有意的越权。

---

## 许可

[MIT License](LICENSE) © 2026 dengdasam

可自由使用、修改、分发、商用，保留版权声明即可。

### 第三方组件

| 组件 | 用途 | 许可 |
| --- | --- | --- |
| SQLite | 数据库引擎 | Public Domain |
| sql.js | 浏览器内运行 SQLite（题库判分） | MIT |
| Microsoft.Data.Sqlite | .NET 的 SQLite 驱动 | MIT |
| MySqlConnector | MySQL 驱动 | MIT |
| Microsoft.Data.SqlClient | SQL Server 驱动 | MIT |
