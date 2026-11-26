# SQL 练习场 / 闯关 —— 目录说明

## 要打开的（双击即可）

| 文件 | 说明 |
|---|---|
| **`SQL练习场.html`** | 答题 + 速查双模式，57 道题 |
| **`SQL闯关.html`** | SQLZoo 式分步引导，57 关 |

两个都是单文件（约 1MB），内嵌 SQLite 引擎和样例数据，双击直接跑，不需要装任何东西、不需要联网。

## 不用打开的

| 路径 | 说明 |
|---|---|
| `src/*.template.html` | **源模板**，题库和引擎是占位符。直接打开会显示“这是源模板”的提示页，属正常 |
| `legacy-python/` | 已弃用的 Python 版查询服务（配 `server.py`，端口 8765），现由 .NET 版取代 |

## 其他文件

| 文件 | 用途 |
|---|---|
| `qbank.py` | 题库（57 题，含每题的表字段、解题步骤、关键语法点） |
| `build.py` | 构建脚本：先验证每道题答案，再把引擎+数据内嵌进两个 HTML |
| `wms.db` | 样例 SQLite 数据库（6 张表），.NET 版查询服务也用它 |
| `test_content.py` | 页面回归测试（Playwright） |

## 加题 / 改题

编辑 `qbank.py` → 运行 `python build.py`，两个 HTML 会同步重建，并自动校验每道题的结果集不为空。

如果只想校验不生成：

```bat
set VALIDATE_ONLY=1
python build.py
```
