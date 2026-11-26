# 题库源文件与构建 —— 目录说明

这个目录是 `sql-query-dotnet` 的一部分，负责生成两套离线题库页面。

## 要打开的（构建后双击即可）

| 文件 | 说明 |
|---|---|
| **`SQL练习场.html`** | 答题 + 速查双模式，78 道题 |
| **`SQL闯关.html`** | SQLZoo 式分步引导，78 关 |

两个都是单文件（约 1MB），内嵌 SQLite 引擎和样例数据，双击直接跑，不需要装任何东西、不需要联网。

> **这两份是构建产物，不入库**（见仓库根 `.gitignore`）。新克隆下来目录里没有它们，
> 先在 `sql-query-dotnet/` 下跑一次 `python build.py`（或 `python quiz-src/build.py`）即可生成。

## 源文件（真正入库的）

| 路径 | 说明 |
|---|---|
| `qbank.py` | 题库：78 题，含每题的表字段、解题步骤、关键语法点 |
| `build.py` | 构建脚本：先验证每道题答案，再把引擎+数据内嵌进两个 HTML |
| `src/*.template.html` | **源模板**，题库和引擎是占位符。直接打开会显示「这是源模板」的提示页，属正常 |
| `assets/sql-wasm.js` / `.wasm` | 内嵌进 HTML 的 SQLite 引擎 |
| `wms.db` | 样例 SQLite 数据库（6 张表），.NET 版查询服务也用它 |

## 其他

| 路径 | 说明 |
|---|---|
| `test_content.py` / `test_page.py` / `test_zone.py` | 页面回归测试（Playwright） |
| `legacy-python/` | 已弃用的 Python 版查询服务（端口 8765），现由 .NET 版取代。**不入库** |

## 加题 / 改题

编辑 `qbank.py` → 在 `sql-query-dotnet/` 下运行 `python quiz-src/build.py`。
脚本会逐个执行验证、生成两个 HTML，并自动同步到 `SqlPlayground/wwwroot/quiz/`（发布 exe 时要用）。

如果只想校验不生成：

```bat
set VALIDATE_ONLY=1
python quiz-src/build.py
```
