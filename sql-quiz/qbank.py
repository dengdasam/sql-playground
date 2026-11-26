# -*- coding: utf-8 -*-
"""SQL 练习题库（与渲染层解耦，build.py 导入使用）。

数据结构
--------
TABLE_DICT: 表名 -> {label, desc, cols: [(字段, 类型, 含义, 示例值), ...]}
Q: 题目列表，每题一个 dict，字段：
    id / cat / level / title / desc / hint / sql / strict / note
    tables   : 本题涉及的表（前端据此渲染字段说明）
    explain  : 解题步骤（有序列表，讲清“为什么这么写”）
    keywords : 关键语法/函数标签
"""

# ---------------- 表字段字典 ----------------
TABLE_DICT = {
    "world": dict(
        label="国家表",
        desc="SQLZoo 经典国家数据，22 行，每国一行；适合练筛选、聚合、子查询、窗口函数。",
        cols=[
            ("name", "TEXT", "国家名（英文）", "China"),
            ("continent", "TEXT", "所属大洲", "Asia"),
            ("area", "INTEGER", "国土面积，单位平方公里", "9600000"),
            ("population", "INTEGER", "人口数", "1364270000"),
            ("gdp", "REAL", "GDP，单位美元", "10357200000000"),
        ]),
    "nobel": dict(
        label="诺贝尔奖表",
        desc="2000–2015 年诺奖获奖记录，105 行；同一年的同一学科可能有多位获奖者。",
        cols=[
            ("yr", "INTEGER", "获奖年份", "2015"),
            ("subject", "TEXT", "学科：Physics / Chemistry / Literature / Economics / Medicine", "Physics"),
            ("winner", "TEXT", "获奖者姓名", "Tu Youyou"),
        ]),
    "emp": dict(
        label="员工表",
        desc="8 名员工；dept_id 外键关联 dept.id。",
        cols=[
            ("id", "INTEGER", "员工编号（主键）", "1"),
            ("name", "TEXT", "员工姓名", "Joe"),
            ("salary", "INTEGER", "月薪，单位美元", "70000"),
            ("dept_id", "INTEGER", "所属部门 id，对应 dept.id", "1"),
        ]),
    "dept": dict(
        label="部门表",
        desc="4 个部门；其中 Finance 没有任何员工，常用来练 LEFT JOIN 找空关联。",
        cols=[
            ("id", "INTEGER", "部门编号（主键）", "1"),
            ("name", "TEXT", "部门名称", "IT"),
        ]),
    "winv_inbound_order_lines": dict(
        label="WMS 入库单行（简化）",
        desc="由脚本生成最近 40 天的样例数据；字段做了简化，只保留出题需要的列。",
        cols=[
            ("id", "INTEGER", "行主键", "1"),
            ("creation_date", "TEXT", "创建时间，文本格式 YYYY-MM-DD HH:MM:SS", "2026-11-20 09:15:00"),
            ("sku", "TEXT", "物料编码", "SKU-BEER-001"),
            ("owner_id", "INTEGER", "货主 id", "1"),
            ("plan_qty", "REAL", "计划数量", "320.5"),
            ("source_system_code", "TEXT", "来源系统编码：ERP / SRM / WMS", "ERP"),
            ("bill_status", "TEXT", "单据状态：COMPLETED / RECEIVING", "COMPLETED"),
            ("tenant_id", "INTEGER", "租户 id，本样例固定为 1", "1"),
        ]),
    "wmdm_batch": dict(
        label="WMS 批次档案（简化）",
        desc="由脚本生成最近 40 天的样例数据；sku 只覆盖前 3 个物料，另 2 个物料没有批次。",
        cols=[
            ("id", "INTEGER", "批次主键", "1"),
            ("creation_date", "TEXT", "创建时间，文本格式 YYYY-MM-DD HH:MM:SS", "2026-11-20 10:02:00"),
            ("sku", "TEXT", "物料编码", "SKU-BEER-001"),
            ("owner_id", "INTEGER", "货主 id", "1"),
            ("batch_code", "TEXT", "批次号，形如 B + 日期 + 三位序号", "B20261120001"),
            ("attribute7", "TEXT", "是否临期：'1' 是，'0' 否（对应原表 ATTRIBUTE7）", "1"),
            ("tenant_id", "INTEGER", "租户 id，本样例固定为 1", "1"),
        ]),
}

CATS = ["基础查询", "聚合分组", "多表连接", "子查询", "窗口函数", "条件字符串", "WMS实战"]
LEVELS = ["入门", "进阶", "困难"]


def q(**kw):
    """题目构造：补齐可选字段的默认值，减少重复书写。"""
    kw.setdefault("strict", False)
    kw.setdefault("note", "")
    kw.setdefault("hint", "")
    kw.setdefault("tables", [])
    kw.setdefault("explain", [])
    kw.setdefault("keywords", [])
    return kw


Q = [
    # ================= A 基础查询 =================
    q(id="A1", cat="基础查询", level="入门", title="人口超过一亿的国家",
      desc="从 world 表查出人口（population）超过 1 亿的国家名。",
      hint="population 是整数，直接和数字比较；1 亿 = 100000000。",
      sql="SELECT name FROM world WHERE population > 100000000",
      tables=["world"],
      explain=[
          "数据来源只有 world 一张表，题目只要国家名，所以 SELECT 列写 name。",
          "筛选条件是人口大于 1 亿，用 WHERE population > 100000000（注意是 8 个 0）。",
          "没有要求排序，结果返回全部符合条件的国家。",
      ],
      keywords=["SELECT", "WHERE", "比较运算"]),

    q(id="A2", cat="基础查询", level="入门", title="亚洲国家按面积降序",
      desc="列出亚洲（continent = 'Asia'）国家的 name 和 area，按面积从大到小排序。",
      hint="ORDER BY area DESC",
      sql="SELECT name, area FROM world WHERE continent = 'Asia' ORDER BY area DESC",
      strict=True, tables=["world"],
      explain=[
          "先确定要两列：name 和 area。",
          "用 WHERE continent = 'Asia' 过滤出亚洲国家（字符串要用单引号）。",
          "最后 ORDER BY area DESC 按面积降序；因为要求了顺序，判分按行序严格比较。",
      ],
      keywords=["WHERE", "字符串字面量", "ORDER BY", "DESC"],
      note="答案含 ORDER BY，判分按行顺序严格比较。"),

    q(id="A3", cat="基础查询", level="进阶", title="GDP 区间筛选",
      desc="查出 gdp 在 1 万亿到 5 万亿之间（含边界）的国家名和 gdp。",
      hint="用 BETWEEN ... AND ...，注意边界包含。",
      sql="SELECT name, gdp FROM world WHERE gdp BETWEEN 1000000000000 AND 5000000000000",
      tables=["world"],
      explain=[
          "BETWEEN a AND b 等价于 gdp >= a AND gdp <= b，两端都包含。",
          "1 万亿 = 1000000000000（12 个 0），5 万亿 = 5000000000000。",
          "也可以写成 gdp >= 1000000000000 AND gdp <= 5000000000000，结果一样。",
      ],
      keywords=["BETWEEN", "AND", "闭区间"]),

    q(id="A4", cat="基础查询", level="入门", title="名字以 A 开头",
      desc="查出名字以字母 A 开头的国家名。",
      hint="LIKE 'A%'",
      sql="SELECT name FROM world WHERE name LIKE 'A%'",
      tables=["world"],
      explain=[
          "模糊匹配用 LIKE，% 代表任意多个字符（包括 0 个）。",
          "'A%' 表示以大写 A 开头，后面接任意内容。",
          "SQLite 的 LIKE 默认对 ASCII 大小写不敏感，'a%' 也会匹配到 A 开头。",
      ],
      keywords=["LIKE", "% 通配符"]),

    q(id="A5", cat="基础查询", level="进阶", title="人口最多的 5 个国家",
      desc="查出人口最多的 5 个国家名和人口，按人口降序。",
      hint="ORDER BY population DESC LIMIT 5",
      sql="SELECT name, population FROM world ORDER BY population DESC LIMIT 5",
      strict=True, tables=["world"],
      explain=[
          "要“最多”，先按人口降序排列：ORDER BY population DESC。",
          "只要前 5 条，用 LIMIT 5 截断结果。",
          "LIMIT 在 ORDER BY 之后生效，两者顺序不能颠倒。",
      ],
      keywords=["ORDER BY", "DESC", "LIMIT"]),

    q(id="A6", cat="基础查询", level="进阶", title="人口密度计算",
      desc="计算每个国家的人口密度（population / area），只显示密度大于 300 的国家名和密度。",
      hint="SQLite 里整数相除可能得到整数；乘 1.0 转成小数，可给表达式起别名。",
      sql="SELECT name, population * 1.0 / area AS density FROM world WHERE population * 1.0 / area > 300",
      tables=["world"],
      explain=[
          "人口密度 = 人口 ÷ 面积，写成 population / area。",
          "两者都是整数时某些数据库会做整除，乘 1.0 强制转成浮点，避免精度丢失。",
          "用 AS density 给表达式起别名，便于阅读。",
          "WHERE 里不能直接用 SELECT 中定义的别名（标准 SQL 的执行顺序决定），所以把表达式再写一遍。",
      ],
      keywords=["算术运算", "AS 别名", "类型转换", "WHERE 执行顺序"]),

    q(id="A7", cat="基础查询", level="入门", title="人口最少的 3 个国家",
      desc="查出人口最少的 3 个国家名和人口，按人口升序。",
      hint="ORDER BY population ASC LIMIT 3；ASC 是默认方向，可省略。",
      sql="SELECT name, population FROM world ORDER BY population ASC LIMIT 3",
      strict=True, tables=["world"],
      explain=[
          "“最少”就是升序排列，ORDER BY population（默认 ASC，可省略不写）。",
          "取前 3 条用 LIMIT 3。",
          "结果里会出现 Andorra 这类人口只有几万的小国。",
      ],
      keywords=["ORDER BY", "ASC", "LIMIT"]),

    q(id="A8", cat="基础查询", level="入门", title="面积较小的国家",
      desc="查出国土面积小于 30 万平方公里的国家名和面积，按面积升序。",
      hint="WHERE area < 300000，再 ORDER BY area。",
      sql="SELECT name, area FROM world WHERE area < 300000 ORDER BY area ASC",
      strict=True, tables=["world"],
      explain=[
          "30 万写成 300000，用 area < 300000 过滤。",
          "按面积升序排列，最小的国家（Andorra，468 平方公里）排在最前面。",
          "注意区分“面积”和“人口”两个字段，别写错列名。",
      ],
      keywords=["WHERE", "ORDER BY", "ASC"]),

    q(id="A9", cat="基础查询", level="进阶", title="名字第二个字母是 a",
      desc="查出名字第二个字母为 a 的国家名。",
      hint="_ 匹配单个字符，所以模式是 '_a%'。",
      sql="SELECT name FROM world WHERE name LIKE '_a%'",
      tables=["world"],
      explain=[
          "LIKE 里 _ 匹配恰好一个字符，% 匹配任意长度。",
          "'_a%' 读作：第一个字符任意，第二个字符是 a，后面随意。",
          "答案包含 Canada、Japan 等（首字母后紧跟 a）。",
      ],
      keywords=["LIKE", "_ 单字符通配"]),

    # ================= B 聚合分组 =================
    q(id="B1", cat="聚合分组", level="入门", title="各大洲国家数量",
      desc="统计每个大洲的国家数量，显示 continent 和 cnt。",
      hint="GROUP BY continent, COUNT(*)",
      sql="SELECT continent, COUNT(*) AS cnt FROM world GROUP BY continent",
      tables=["world"],
      explain=[
          "要“每个大洲”一个数字，就按 continent 分组：GROUP BY continent。",
          "COUNT(*) 数每组有多少行，即国家数量。",
          "SELECT 里只能出现分组列和聚合函数，写别的列在严格模式下会报错。",
      ],
      keywords=["GROUP BY", "COUNT(*)"]),

    q(id="B2", cat="聚合分组", level="进阶", title="人口过亿的大洲",
      desc="统计各大洲的总人口，只显示总人口超过 1 亿的大洲及总人口。",
      hint="分组后过滤用 HAVING，不能用 WHERE。",
      sql="SELECT continent, SUM(population) AS total FROM world GROUP BY continent HAVING SUM(population) > 100000000",
      tables=["world"],
      explain=[
          "先 GROUP BY continent 分组，再 SUM(population) 求每组总人口。",
          "过滤的是“聚合之后的结果”，必须用 HAVING；WHERE 在分组前执行，拿不到 SUM。",
          "HAVING 里可以直接写 SUM(population)，也可以重复聚合表达式。",
      ],
      keywords=["GROUP BY", "SUM", "HAVING", "WHERE vs HAVING"]),

    q(id="B3", cat="聚合分组", level="入门", title="全球总人口与总 GDP",
      desc="查出全球人口总数和 GDP 总和，列名为 total_pop 和 total_gdp。",
      hint="聚合函数可以直接作用于全表，不需要 GROUP BY。",
      sql="SELECT SUM(population) AS total_pop, SUM(gdp) AS total_gdp FROM world",
      tables=["world"],
      explain=[
          "没有“每个 XX”的分组需求，就不写 GROUP BY，聚合函数会把整张表当成一组。",
          "SUM(population) 求人口合计，SUM(gdp) 求 GDP 合计。",
          "用 AS 起中文题干要求的列名 total_pop / total_gdp（判分虽不比列名，但养成好习惯）。",
      ],
      keywords=["SUM", "全表聚合", "AS 别名"]),

    q(id="B4", cat="聚合分组", level="入门", title="各学科诺奖人数",
      desc="统计 nobel 表中每个学科的获奖人数，显示 subject 和 cnt。",
      hint="GROUP BY subject",
      sql="SELECT subject, COUNT(*) AS cnt FROM nobel GROUP BY subject",
      tables=["nobel"],
      explain=[
          "按学科分组：GROUP BY subject。",
          "COUNT(*) 数每组的记录条数，即该学科获奖人数（多人共享奖项时每人一行）。",
          "结果通常有 5 个学科：Physics / Chemistry / Literature / Economics / Medicine。",
      ],
      keywords=["GROUP BY", "COUNT(*)"]),

    q(id="B5", cat="聚合分组", level="进阶", title="高产年份",
      desc="找出诺贝尔奖颁发人数超过 8 人的年份及人数（yr, cnt）。",
      hint="HAVING COUNT(*) > 8",
      sql="SELECT yr, COUNT(*) AS cnt FROM nobel GROUP BY yr HAVING COUNT(*) > 8",
      tables=["nobel"],
      explain=[
          "先按年份分组 GROUP BY yr。",
          "再数每年多少人：COUNT(*)。",
          "筛选“人数超过 8”是聚合后的条件，用 HAVING COUNT(*) > 8。",
      ],
      keywords=["GROUP BY", "HAVING", "COUNT(*)"]),

    q(id="B6", cat="聚合分组", level="进阶", title="各大洲平均人口",
      desc="统计每个大洲的平均人口，显示 continent 和 avg_pop，按平均人口降序。",
      hint="AVG(population)，排序按别名或聚合表达式。",
      sql="SELECT continent, AVG(population) AS avg_pop FROM world GROUP BY continent ORDER BY avg_pop DESC, continent",
      strict=True, tables=["world"],
      explain=[
          "按大洲分组后，AVG(population) 算组内平均人口。",
          "ORDER BY 可以直接引用 SELECT 里的别名 avg_pop。",
          "额外加 continent 作为第二排序键，保证平均值并列时顺序也是确定的（严格比较需要）。",
      ],
      keywords=["AVG", "GROUP BY", "ORDER BY 别名"]),

    q(id="B7", cat="聚合分组", level="进阶", title="国家数超过 3 的大洲",
      desc="统计国家数量超过 3 个的大洲及其国家数（continent, cnt），按数量降序。",
      hint="HAVING COUNT(*) > 3",
      sql="SELECT continent, COUNT(*) AS cnt FROM world GROUP BY continent HAVING COUNT(*) > 3 ORDER BY cnt DESC, continent",
      strict=True, tables=["world"],
      explain=[
          "GROUP BY continent 分组，COUNT(*) 得到每洲国家数。",
          "HAVING COUNT(*) > 3 过滤掉国家太少的洲（如 Oceania 只有澳大利亚）。",
          "ORDER BY cnt DESC, continent 让并列数量的洲也有稳定顺序。",
      ],
      keywords=["GROUP BY", "HAVING", "多列排序"]),

    q(id="B8", cat="聚合分组", level="进阶", title="获奖人数最多的年份",
      desc="找出诺贝尔奖获奖人数最多的年份及人数（yr, cnt）。",
      hint="ORDER BY COUNT(*) DESC 后 LIMIT 1。",
      sql="SELECT yr, COUNT(*) AS cnt FROM nobel GROUP BY yr ORDER BY cnt DESC LIMIT 1",
      tables=["nobel"],
      explain=[
          "按年份分组并计数，得到每年的获奖人数。",
          "按人数降序排序，取第一条即人数最多的年份。",
          "LIMIT 1 在排序之后执行，所以拿到的是最大值那一行。",
      ],
      keywords=["GROUP BY", "COUNT(*)", "ORDER BY", "LIMIT"]),

    # ================= C 多表连接 =================
    q(id="C1", cat="多表连接", level="入门", title="员工与部门",
      desc="查出每个员工的姓名、工资和部门名称（name, salary, dept_name）。",
      hint="emp.dept_id = dept.id",
      sql="SELECT e.name, e.salary, d.name AS dept_name FROM emp e JOIN dept d ON e.dept_id = d.id",
      tables=["emp", "dept"],
      explain=[
          "员工信息在 emp，部门名称在 dept，需要两表连接。",
          "连接条件是 emp.dept_id = dept.id（外键指向主键）。",
          "两张表都有 name 列，必须用表别名区分：e.name 是员工名，d.name 是部门名。",
      ],
      keywords=["JOIN", "ON", "表别名", "同名列冲突"]),

    q(id="C2", cat="多表连接", level="进阶", title="没有员工的部门",
      desc="查出没有任何员工的部门名称。",
      hint="LEFT JOIN + 右表主键 IS NULL",
      sql="SELECT d.name FROM dept d LEFT JOIN emp e ON e.dept_id = d.id WHERE e.id IS NULL",
      tables=["dept", "emp"],
      explain=[
          "要找“没有匹配”的行，用左连接：保留 dept 全部行，匹配不上的右表列是 NULL。",
          "匹配不上时 emp.id 为 NULL，因此 WHERE e.id IS NULL 正好筛出空部门。",
          "本题答案是 Finance。也可以用 NOT EXISTS 写（见 D4 的反向思路）。",
      ],
      keywords=["LEFT JOIN", "IS NULL", "反连接"]),

    q(id="C3", cat="多表连接", level="进阶", title="部门人数与平均工资",
      desc="统计每个部门的部门名、员工人数和平均工资（只统计有员工的部门）。",
      hint="JOIN + GROUP BY d.name",
      sql="SELECT d.name, COUNT(*) AS cnt, AVG(e.salary) AS avg_sal FROM emp e JOIN dept d ON e.dept_id = d.id GROUP BY d.name",
      tables=["emp", "dept"],
      explain=[
          "先连接两表拿到部门名，再按部门名分组。",
          "COUNT(*) 是人数，AVG(e.salary) 是平均工资。",
          "这里用内连接 JOIN，没员工的部门不会出现，正好满足“只统计有员工的部门”。",
      ],
      keywords=["JOIN", "GROUP BY", "COUNT", "AVG"]),

    q(id="C4", cat="多表连接", level="困难", title="高于部门均薪的员工",
      desc="查出工资高于其所在部门平均工资的员工姓名和工资。",
      hint="先用子查询算每个部门的平均工资，再 JOIN 回员工表比较。",
      sql="SELECT e.name, e.salary FROM emp e JOIN (SELECT dept_id, AVG(salary) AS av FROM emp GROUP BY dept_id) t ON e.dept_id = t.dept_id WHERE e.salary > t.av",
      tables=["emp"],
      explain=[
          "先写子查询：按 dept_id 分组求 AVG(salary)，得到每个部门的平均线。",
          "把这个子查询当成一张临时表 t，用 dept_id 和 emp 连接。",
          "最后 WHERE e.salary > t.av 只留下高于本部门平均线的员工。",
          "也可以用相关子查询实现（见 D6），思路相同但写法不同。",
      ],
      keywords=["子查询", "派生表", "JOIN", "AVG"]),

    q(id="C5", cat="多表连接", level="进阶", title="每个部门的最高工资",
      desc="查出每个有员工的部门名称和该部门最高工资（dept_name, max_sal），按部门名升序。",
      hint="JOIN 后 GROUP BY，用 MAX(salary)。",
      sql="SELECT d.name AS dept_name, MAX(e.salary) AS max_sal FROM emp e JOIN dept d ON e.dept_id = d.id GROUP BY d.name ORDER BY d.name ASC",
      strict=True, tables=["emp", "dept"],
      explain=[
          "连接 emp 和 dept，得到带部门名的明细。",
          "按部门名分组，MAX(e.salary) 取组内最高工资。",
          "ORDER BY d.name 让结果按部门名字母序输出，方便比对。",
      ],
      keywords=["JOIN", "GROUP BY", "MAX", "ORDER BY"]),

    q(id="C6", cat="多表连接", level="进阶", title="员工按部门与工资排序",
      desc="查出员工姓名、部门名和工资（name, dept_name, salary），按部门名升序、同部门内工资降序。",
      hint="ORDER BY 可以跟多个键：ORDER BY d.name, e.salary DESC。",
      sql="SELECT e.name, d.name AS dept_name, e.salary FROM emp e JOIN dept d ON e.dept_id = d.id ORDER BY d.name ASC, e.salary DESC",
      strict=True, tables=["emp", "dept"],
      explain=[
          "先连接两表拿到部门名。",
          "多列排序：第一键部门名升序，第二键工资降序。",
          "每个排序键可以单独指定 ASC / DESC，默认是 ASC。",
      ],
      keywords=["JOIN", "多列排序", "ASC/DESC"]),

    q(id="C7", cat="多表连接", level="困难", title="部门人数（含零人部门）",
      desc="列出每个部门的名称和员工人数（dept_name, cnt），没有员工的部门显示 0，按部门名升序。",
      hint="LEFT JOIN 后用 COUNT(e.id) 而不是 COUNT(*)。",
      sql="SELECT d.name AS dept_name, COUNT(e.id) AS cnt FROM dept d LEFT JOIN emp e ON e.dept_id = d.id GROUP BY d.name ORDER BY d.name ASC",
      strict=True, tables=["dept", "emp"],
      explain=[
          "要保留所有部门，必须用 dept LEFT JOIN emp。",
          "关键点：COUNT(*) 会把“匹配不上的那一行 NULL”也算 1，得到错误的 1；COUNT(e.id) 只数非 NULL，空部门才是 0。",
          "按部门名分组并排序，Finance 会以 0 出现在结果里。",
      ],
      keywords=["LEFT JOIN", "COUNT(列) vs COUNT(*)", "NULL 语义"],
      note="这是 LEFT JOIN 统计最容易踩的坑：空关联时 COUNT(*) = 1，COUNT(右表列) = 0。"),

    # ================= D 子查询 =================
    q(id="D1", cat="子查询", level="进阶", title="比某国人口多",
      desc="查出人口比 Russia 多的国家名和人口。",
      hint="标量子查询：(SELECT population FROM world WHERE name = 'Russia')",
      sql="SELECT name, population FROM world WHERE population > (SELECT population FROM world WHERE name = 'Russia')",
      tables=["world"],
      explain=[
          "内层子查询先查出 Russia 的人口，返回单个值（标量）。",
          "外层用它作为比较基准：population > 那个值。",
          "结果里不包含 Russia 本身（条件是严格大于）。",
      ],
      keywords=["标量子查询", "比较运算"]),

    q(id="D2", cat="子查询", level="进阶", title="同洲国家",
      desc="查出与 China 或 India 同一大洲的国家名和 continent（排除中国和印度本身）。",
      hint="IN + 子查询，再用 NOT IN 排除自身。",
      sql="SELECT name, continent FROM world WHERE continent IN (SELECT continent FROM world WHERE name IN ('China','India')) AND name NOT IN ('China','India')",
      tables=["world"],
      explain=[
          "子查询先取出 China 和 India 所在的大洲（都是 Asia），可能返回多行。",
          "外层用 continent IN (...) 判断某国是否属于这些大洲。",
          "再用 name NOT IN ('China','India') 把这两个国家自己排除掉。",
      ],
      keywords=["IN 子查询", "NOT IN", "多行子查询"]),

    q(id="D3", cat="子查询", level="入门", title="工资最高的员工",
      desc="查出工资等于全公司最高工资的员工姓名和工资。",
      hint="salary = (SELECT MAX(salary) FROM emp)",
      sql="SELECT name, salary FROM emp WHERE salary = (SELECT MAX(salary) FROM emp)",
      tables=["emp"],
      explain=[
          "子查询 SELECT MAX(salary) 得到全公司最高工资。",
          "外层用 salary = 这个值去匹配，能处理最高工资并列的情况（本题 Jim 和 Max 都是 90000）。",
          "不要写成 ORDER BY salary DESC LIMIT 1，那样并列时只会返回一个人。",
      ],
      keywords=["标量子查询", "MAX", "并列值"]),

    q(id="D4", cat="子查询", level="进阶", title="有员工的部门（EXISTS）",
      desc="用 EXISTS 写：查出自有员工的部门名称。",
      hint="SELECT name FROM dept d WHERE EXISTS (...)",
      sql="SELECT d.name FROM dept d WHERE EXISTS (SELECT 1 FROM emp e WHERE e.dept_id = d.id)",
      tables=["dept", "emp"],
      explain=[
          "EXISTS 只判断子查询有没有返回行，不关心返回什么内容，所以写 SELECT 1 即可。",
          "子查询里用 e.dept_id = d.id 引用外层的 d，这叫相关子查询：每行 dept 都会执行一次。",
          "有匹配行的部门保留，没有的（Finance）被过滤掉。",
      ],
      keywords=["EXISTS", "相关子查询", "半连接"]),

    q(id="D5", cat="子查询", level="进阶", title="工资高于平均工资的员工",
      desc="查出工资高于全公司平均工资的员工姓名和工资。",
      hint="salary > (SELECT AVG(salary) FROM emp)",
      sql="SELECT name, salary FROM emp WHERE salary > (SELECT AVG(salary) FROM emp)",
      tables=["emp"],
      explain=[
          "子查询算出全公司平均工资（8 人合计 614000，平均 76750）。",
          "外层筛选 salary 大于该平均值的人。",
          "本题结果是 Jim、Henry、Max、Randy 四人。",
      ],
      keywords=["标量子查询", "AVG"]),

    q(id="D6", cat="子查询", level="困难", title="人口高于本洲平均的国家",
      desc="查出人口高于其所在大洲平均人口的国家名、大洲和人口。",
      hint="相关子查询：内层用 x.continent = w.continent 关联外层。",
      sql="SELECT name, continent, population FROM world w WHERE population > (SELECT AVG(population) FROM world x WHERE x.continent = w.continent)",
      tables=["world"],
      explain=[
          "外层给 world 起别名 w，逐行处理。",
          "内层子查询算“该行所属大洲”的平均人口，用 x.continent = w.continent 把内外层关联起来。",
          "外层比较 population > 本洲平均值，保留高于平均的国家。",
          "相关子查询会对每一行执行一次内层查询，逻辑直观但数据量大时较慢。",
      ],
      keywords=["相关子查询", "AVG", "别名关联"]),

    q(id="D7", cat="子查询", level="困难", title="每个大洲人口最多的国家",
      desc="查出每个大洲人口最多的国家：continent, name, population。",
      hint="population = (SELECT MAX(...) FROM world x WHERE x.continent = w.continent)",
      sql="SELECT continent, name, population FROM world w WHERE population = (SELECT MAX(population) FROM world x WHERE x.continent = w.continent)",
      tables=["world"],
      explain=[
          "对每一行，用相关子查询算出同洲的最大人口。",
          "外层保留人口等于本洲最大值的国家，即该洲第一名。",
          "用 = 而不是 ORDER BY + LIMIT，可以正确处理人口并列第一的情况。",
      ],
      keywords=["相关子查询", "MAX", "分组取极值"]),

    # ================= E 窗口函数 =================
    q(id="E1", cat="窗口函数", level="进阶", title="全球人口排名",
      desc="查出所有国家名、人口及人口排名（人口多的排前面，并列同名次），列名 rk。",
      hint="RANK() OVER (ORDER BY population DESC)",
      sql="SELECT name, population, RANK() OVER (ORDER BY population DESC) AS rk FROM world",
      strict=True, tables=["world"],
      explain=[
          "窗口函数在结果集上计算排名，不改变行数。",
          "RANK() OVER (ORDER BY population DESC)：按人口降序给每行一个名次。",
          "RANK 遇并列会给相同名次并跳号（1,2,2,4）；若不想跳号用 DENSE_RANK。",
      ],
      keywords=["窗口函数", "RANK()", "OVER", "PARTITION"]),

    q(id="E2", cat="窗口函数", level="困难", title="各大洲人口前二",
      desc="查出每个大洲人口排名前 2 的国家，显示 continent, name, population。",
      hint="ROW_NUMBER() OVER (PARTITION BY continent ORDER BY population DESC)，外层 WHERE rn <= 2。",
      sql="SELECT continent, name, population FROM (SELECT continent, name, population, ROW_NUMBER() OVER (PARTITION BY continent ORDER BY population DESC) AS rn FROM world) WHERE rn <= 2 ORDER BY continent, rn",
      strict=True, tables=["world"],
      explain=[
          "PARTITION BY continent 把数据按大洲分成若干组，排名在每个组内独立进行。",
          "ROW_NUMBER() 在组内按人口降序编号 1、2、3…（不并列不跳号）。",
          "窗口函数不能直接写在 WHERE 里，所以套一层子查询，再在外层 WHERE rn <= 2 过滤。",
          "外层 ORDER BY continent, rn 让输出顺序确定，便于严格比对。",
      ],
      keywords=["ROW_NUMBER()", "PARTITION BY", "子查询过滤", "分组 TopN"]),

    q(id="E3", cat="窗口函数", level="进阶", title="工资密集排名",
      desc="查出员工姓名、工资及工资的稠密排名（并列同名次且名次连续），列名 dr。",
      hint="DENSE_RANK()",
      sql="SELECT name, salary, DENSE_RANK() OVER (ORDER BY salary DESC) AS dr FROM emp",
      strict=True, tables=["emp"],
      explain=[
          "DENSE_RANK 与 RANK 的区别：并列后不跳号（1,2,2,3）。",
          "OVER (ORDER BY salary DESC) 指定排名依据。",
          "本题 90000 两人并列第 1，下一个工资 85000 是第 2。",
      ],
      keywords=["DENSE_RANK()", "OVER", "并列处理"]),

    q(id="E4", cat="窗口函数", level="困难", title="相邻工资差",
      desc="按工资降序，查出每个员工姓名、工资，以及比前一名员工少多少（diff），第一行 diff 为 NULL。",
      hint="LAG(salary) OVER (ORDER BY salary DESC) - salary",
      sql="SELECT name, salary, LAG(salary) OVER (ORDER BY salary DESC) - salary AS diff FROM emp ORDER BY salary DESC",
      strict=True, tables=["emp"],
      explain=[
          "LAG(salary) 取“上一行”的工资，OVER 里定义上一行是谁（按工资降序）。",
          "用上一行工资减去当前行工资，得到比前一名少多少。",
          "第一行没有上一行，LAG 返回 NULL，NULL 参与减法结果仍是 NULL。",
      ],
      keywords=["LAG()", "偏移函数", "NULL 传播"]),

    q(id="E5", cat="窗口函数", level="进阶", title="部门内工资排名",
      desc="查出员工所属部门 id、姓名、工资及部门内工资排名（rk），按部门 id 升序、排名升序。",
      hint="RANK() OVER (PARTITION BY dept_id ORDER BY salary DESC)",
      sql="SELECT dept_id, name, salary, RANK() OVER (PARTITION BY dept_id ORDER BY salary DESC) AS rk FROM emp ORDER BY dept_id, rk",
      strict=True, tables=["emp"],
      explain=[
          "PARTITION BY dept_id 让排名在每个部门内部独立计算。",
          "组内按工资降序给 RANK，得到部门内名次。",
          "外层 ORDER BY dept_id, rk 把结果按部门聚在一起并保持名次顺序。",
      ],
      keywords=["RANK()", "PARTITION BY", "组内排名"]),

    q(id="E6", cat="窗口函数", level="困难", title="人口累计值",
      desc="按人口降序，查出国家名、人口，以及从头到当前行的累计人口（running）。",
      hint="SUM(population) OVER (ORDER BY population DESC)",
      sql="SELECT name, population, SUM(population) OVER (ORDER BY population DESC) AS running FROM world ORDER BY population DESC",
      strict=True, tables=["world"],
      explain=[
          "把 SUM 加上 OVER (ORDER BY ...) 就从“全表求和”变成“累计求和”。",
          "默认窗口范围是 ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW，即从头累加到当前行。",
          "第一行累计值等于它自己的人口，最后一行等于全球总人口。",
      ],
      keywords=["SUM() OVER", "累计聚合", "窗口范围"]),

    q(id="E7", cat="窗口函数", level="困难", title="各大洲人口第二多的国家",
      desc="查出每个大洲人口排第二的国家：continent, name, population，按大洲名升序。",
      hint="ROW_NUMBER() 分区编号后取 rn = 2。",
      sql="SELECT continent, name, population FROM (SELECT continent, name, population, ROW_NUMBER() OVER (PARTITION BY continent ORDER BY population DESC) AS rn FROM world) WHERE rn = 2 ORDER BY continent",
      strict=True, tables=["world"],
      explain=[
          "分区编号思路与 E2 相同，只是取第 2 名而不是前 2 名。",
          "只有 1 个国家的洲（如 Oceania）没有第 2 名，会自然消失。",
          "外层按大洲名排序，保证结果顺序稳定。",
      ],
      keywords=["ROW_NUMBER()", "PARTITION BY", "Nth 取值"]),

    # ================= F 条件与字符串 =================
    q(id="F1", cat="条件字符串", level="入门", title="2010 年物理奖得主",
      desc="查出 2010 年 Physics 奖项的获奖者姓名。",
      hint="两个条件用 AND 连接。",
      sql="SELECT winner FROM nobel WHERE yr = 2010 AND subject = 'Physics'",
      tables=["nobel"],
      explain=[
          "年份条件是 yr = 2010（数字不加引号）。",
          "学科条件是 subject = 'Physics'（字符串要加单引号，且大小写要和数据一致）。",
          "两个条件必须同时满足，用 AND 连接。",
      ],
      keywords=["AND", "数值 vs 字符串"]),

    q(id="F2", cat="条件字符串", level="进阶", title="人口分级（CASE）",
      desc="查出国家名和人口等级：人口 >= 1 亿显示 'BIG'，否则 'SMALL'，列名 level。",
      hint="CASE WHEN ... THEN ... ELSE ... END",
      sql="SELECT name, CASE WHEN population >= 100000000 THEN 'BIG' ELSE 'SMALL' END AS level FROM world",
      tables=["world"],
      explain=[
          "CASE 表达式按顺序判断 WHEN 条件，命中就返回对应 THEN 的值。",
          "所有条件都不满足时走 ELSE；省略 ELSE 会返回 NULL。",
          "整个 CASE ... END 是一个表达式，可以用 AS 起别名 level。",
      ],
      keywords=["CASE WHEN", "ELSE", "表达式别名"]),

    q(id="F3", cat="条件字符串", level="入门", title="名字含 an 的国家数",
      desc="统计名字中包含 'an' 的国家数量，列名 cnt。",
      hint="LIKE '%an%' + COUNT(*)",
      sql="SELECT COUNT(*) AS cnt FROM world WHERE name LIKE '%an%'",
      tables=["world"],
      explain=[
          "包含子串要用两侧都带 % 的模式：'%an%'。",
          "COUNT(*) 统计符合条件的行数。",
          "因为要的是“数量”而不是名单，所以 SELECT 里只有聚合函数。",
      ],
      keywords=["LIKE", "% 通配符", "COUNT(*)"]),

    q(id="F4", cat="条件字符串", level="进阶", title="拼接国家与大洲",
      desc="查出国家名和大洲拼接成的字符串（格式：中国-Asia 这种“名字-大洲”），列名 label。",
      hint="SQLite 用 || 拼接字符串。",
      sql="SELECT name || '-' || continent AS label FROM world",
      tables=["world"],
      explain=[
          "SQLite / PostgreSQL / Oracle 用 || 做字符串拼接。",
          "MySQL 要用 CONCAT(name, '-', continent)，SQL Server 用 +，这是方言差异。",
          "中间夹一个 '-' 常量，拼成“国家-大洲”的格式。",
      ],
      keywords=["|| 拼接", "字符串常量", "方言差异"],
      note="MySQL 对照：CONCAT(name, '-', continent)。"),

    q(id="F5", cat="条件字符串", level="进阶", title="工资分档",
      desc="查出员工姓名、工资和工资档位（band）：>= 90000 为 'HIGH'，>= 75000 为 'MID'，否则 'LOW'。",
      hint="CASE 从上到下依次判断，条件顺序很关键。",
      sql="SELECT name, salary, CASE WHEN salary >= 90000 THEN 'HIGH' WHEN salary >= 75000 THEN 'MID' ELSE 'LOW' END AS band FROM emp",
      tables=["emp"],
      explain=[
          "CASE 按书写顺序短路判断，第一个命中的 WHEN 就返回。",
          "必须先判断 >= 90000 再判断 >= 75000；顺序颠倒的话 90000 会先落进 MID。",
          "都不满足走 ELSE 'LOW'。",
      ],
      keywords=["CASE WHEN", "条件顺序", "短路求值"]),

    q(id="F6", cat="条件字符串", level="进阶", title="名字里的空格换成下划线",
      desc="查出国家名，以及把名字中空格替换为下划线后的编码（name, code）。",
      hint="replace(字段, ' ', '_')",
      sql="SELECT name, replace(name, ' ', '_') AS code FROM world",
      tables=["world"],
      explain=[
          "replace(原字符串, 被替换内容, 替换成什么) 是 SQLite 的内置字符串函数。",
          "第二个参数是单个空格 ' '，第三个是下划线 '_'。",
          "没有空格的国家（如 China）替换后不变。",
      ],
      keywords=["replace()", "字符串函数"],
      note="MySQL 的 REPLACE 用法相同；SQL Server 也支持 REPLACE。"),

    q(id="F7", cat="条件字符串", level="入门", title="国家名长度",
      desc="查出每个国家的名字和名字长度（name, len）。",
      hint="length(name)",
      sql="SELECT name, length(name) AS len FROM world",
      tables=["world"],
      explain=[
          "length() 返回字符串的字符数（SQLite 对 TEXT 返回字符数，不是字节数）。",
          "AS len 给结果列起名。",
          "注意 len 不是 SQL 关键字，但为了避免某些方言冲突可以写成 name_len。",
      ],
      keywords=["length()", "字符串函数"]),

    # ================= G WMS 实战 =================
    q(id="G1", cat="WMS实战", level="进阶", title="入库单行：最近 30 天按天统计",
      desc="统计 winv_inbound_order_lines 表最近 30 天（含今天）每天创建的 ID 个数，返回 create_date, cnt，按日期升序。",
      hint="SQLite 用 date('now','-29 days')；今天算第 1 天，共 30 天。",
      sql="SELECT date(creation_date) AS create_date, COUNT(id) AS cnt FROM winv_inbound_order_lines WHERE date(creation_date) >= date('now','-29 days') AND date(creation_date) <= date('now') GROUP BY date(creation_date) ORDER BY create_date",
      strict=True, tables=["winv_inbound_order_lines"],
      explain=[
          "creation_date 是带时分秒的文本，先用 date() 截成日期部分。",
          "窗口下界 date('now','-29 days')：含今天共 30 天；上界 date('now') 排除未来数据。",
          "按 date(creation_date) 分组并 COUNT(id)，最后按日期升序，得到每日新增曲线。",
          "给 date(creation_date) 起了别名 create_date，GROUP BY 里仍要写完整表达式（SQLite 也接受别名，但完整写更通用）。",
      ],
      keywords=["date()", "date('now','-29 days')", "GROUP BY", "时间窗口"],
      note="MySQL 对照：DATE(creation_date) >= DATE_SUB(CURDATE(), INTERVAL 29 DAY)，分组用 DATE(creation_date)。"),

    q(id="G2", cat="WMS实战", level="进阶", title="批次档案：最近 30 天按天统计",
      desc="统计 wmdm_batch 表最近 30 天（含今天）每天创建的 ID 个数，返回 create_date, cnt，按日期升序。",
      hint="与上一题同构，只换表名。",
      sql="SELECT date(creation_date) AS create_date, COUNT(id) AS cnt FROM wmdm_batch WHERE date(creation_date) >= date('now','-29 days') AND date(creation_date) <= date('now') GROUP BY date(creation_date) ORDER BY create_date",
      strict=True, tables=["wmdm_batch"],
      explain=[
          "结构与 G1 完全相同，只是数据源换成 wmdm_batch。",
          "实际工作里两张表常要放在一起对照看趋势（见 G3）。",
          "注意 COUNT(id) 与 COUNT(*) 的区别：id 理论上可能为 NULL，要数行数就用 COUNT(*)。",
      ],
      keywords=["date()", "COUNT(id)", "GROUP BY"],
      note="MySQL 写法见 G1。"),

    q(id="G3", cat="WMS实战", level="困难", title="两表按天合并对照",
      desc="把两张表最近 30 天每天的新增数合并成一张表：create_date, src, cnt，按日期升序、同日 'INBOUND' 在 'BATCH' 前。",
      hint="两个 SELECT 用 UNION ALL 纵向拼接，src 用常量字符串标记来源。",
      sql="SELECT date(creation_date) AS create_date, 'INBOUND' AS src, COUNT(id) AS cnt FROM winv_inbound_order_lines WHERE date(creation_date) >= date('now','-29 days') GROUP BY date(creation_date) UNION ALL SELECT date(creation_date), 'BATCH', COUNT(id) FROM wmdm_batch WHERE date(creation_date) >= date('now','-29 days') GROUP BY date(creation_date) ORDER BY create_date, src",
      strict=True, tables=["winv_inbound_order_lines", "wmdm_batch"],
      explain=[
          "两段查询各自按天聚合，列数和类型必须一一对应。",
          "第二列用常量字符串 'INBOUND' / 'BATCH' 标记来源，这是 UNION 里区分数据来源的常用手法。",
          "用 UNION ALL 而不是 UNION：这里不存在重复行，UNION 反而多做一次去重排序。",
          "最外层 ORDER BY create_date, src 让同一天的两条按 INBOUND、BATCH 字母序排列（I 在 B 后面？注意：'BATCH' < 'INBOUND'，若要 INBOUND 在前需自定义排序）。",
      ],
      keywords=["UNION ALL", "常量列", "ORDER BY", "纵向拼接"],
      note="本题按 src 字母序排列，'BATCH' 会排在 'INBOUND' 之前；若业务要求 INBOUND 在前，可加 CASE 生成排序列或改用 UNION 后在外层排序。"),

    q(id="G4", cat="WMS实战", level="入门", title="入库来源系统分布",
      desc="统计入库单行表中各来源系统（source_system_code）的行数，列名 cnt。",
      hint="GROUP BY source_system_code",
      sql="SELECT source_system_code, COUNT(*) AS cnt FROM winv_inbound_order_lines GROUP BY source_system_code",
      tables=["winv_inbound_order_lines"],
      explain=[
          "按来源系统编码分组，COUNT(*) 数每组的行数。",
          "结果可以用来做来源占比的饼图。",
          "如果某个来源为 NULL，GROUP BY 会把 NULL 单独归成一组。",
      ],
      keywords=["GROUP BY", "COUNT(*)", "NULL 分组"]),

    q(id="G5", cat="WMS实战", level="困难", title="有入库行但无批次档案的 SKU",
      desc="查出在入库单行表中出现过、但在批次档案表中完全没有批次的 SKU（去重）。",
      hint="NOT IN 或 NOT EXISTS 子查询。",
      sql="SELECT DISTINCT sku FROM winv_inbound_order_lines WHERE sku NOT IN (SELECT DISTINCT sku FROM wmdm_batch)",
      tables=["winv_inbound_order_lines", "wmdm_batch"],
      explain=[
          "内层先取批次表里出现过的所有 SKU。",
          "外层用 NOT IN 排除这些 SKU，剩下的就是“有入库、没批次”的物料。",
          "SELECT DISTINCT 去重，因为同一 SKU 可能有多条入库行。",
          "注意 NOT IN 遇到子查询里的 NULL 会整体失效；生产环境更稳妥的是 NOT EXISTS。",
      ],
      keywords=["NOT IN", "NOT EXISTS", "DISTINCT", "NULL 陷阱"],
      note="样例数据里 SKU-LABEL-A、SKU-CAP-01 没有批次，会出现在结果中。"),

    q(id="G6", cat="WMS实战", level="进阶", title="各货主入库计划量",
      desc="按货主（owner_id）统计入库单行的计划数量合计，列名 total_qty，按合计降序。",
      hint="SUM(plan_qty) + GROUP BY + ORDER BY",
      sql="SELECT owner_id, SUM(plan_qty) AS total_qty FROM winv_inbound_order_lines GROUP BY owner_id ORDER BY total_qty DESC",
      strict=True, tables=["winv_inbound_order_lines"],
      explain=[
          "plan_qty 是 REAL 类型，SUM 会返回小数合计。",
          "按 owner_id 分组，得到每个货主的计划总量。",
          "ORDER BY total_qty DESC 按合计从大到小排，方便找出量最大的货主。",
      ],
      keywords=["SUM", "GROUP BY", "ORDER BY 别名"]),

    q(id="G7", cat="WMS实战", level="进阶", title="临期批次数",
      desc="统计批次档案中 attribute7 = '1'（临期）的批次数，列名 cnt。",
      hint="注意字段是文本类型，要写 '1' 而不是 1。",
      sql="SELECT COUNT(*) AS cnt FROM wmdm_batch WHERE attribute7 = '1'",
      tables=["wmdm_batch"],
      explain=[
          "attribute7 在样例表里是 TEXT，值是字符串 '1' / '0'。",
          "写 = '1'（带引号）；写 = 1（数字）在 SQLite 的弱类型比较下可能也能命中，但不严谨。",
          "COUNT(*) 统计满足条件的行数，即临期批次数量。",
      ],
      keywords=["COUNT(*)", "文本 vs 数字", "弱类型比较"],
      note="用户原表中 ATTRIBUTE7 注释为「是否临期:1是,0否」，实际存储可能是字符型，需按库里的真实类型写。"),

    q(id="G8", cat="WMS实战", level="进阶", title="按 SKU 统计行数与计划量",
      desc="按 SKU 统计入库行数和计划量合计（sku, cnt, total_qty），按 total_qty 降序、sku 升序。",
      hint="一个 GROUP BY 里可以同时用 COUNT(*) 和 SUM(plan_qty)。",
      sql="SELECT sku, COUNT(*) AS cnt, SUM(plan_qty) AS total_qty FROM winv_inbound_order_lines GROUP BY sku ORDER BY total_qty DESC, sku",
      strict=True, tables=["winv_inbound_order_lines"],
      explain=[
          "按 sku 分组，一组就是一个物料。",
          "COUNT(*) 数这个物料有多少入库行，SUM(plan_qty) 汇总计划量。",
          "多列排序保证合计并列时也有稳定顺序（严格比较需要）。",
      ],
      keywords=["GROUP BY", "COUNT", "SUM", "多列排序"]),

    q(id="G9", cat="WMS实战", level="进阶", title="最近 7 天入库行数",
      desc="统计最近 7 天（含今天）每天入库单行的数量，返回 create_date, cnt，按日期升序。",
      hint="把 30 天窗口改成 date('now','-6 days')。",
      sql="SELECT date(creation_date) AS create_date, COUNT(*) AS cnt FROM winv_inbound_order_lines WHERE date(creation_date) >= date('now','-6 days') GROUP BY date(creation_date) ORDER BY create_date",
      strict=True, tables=["winv_inbound_order_lines"],
      explain=[
          "最近 7 天含今天，所以下界是 date('now','-6 days')（今天减 6 天，共 7 个自然日）。",
          "按日期分组计数，得到每天的入库行数。",
          "与 G1 相比窗口更短，适合做近期波动监控。",
      ],
      keywords=["date('now','-6 days')", "GROUP BY", "短窗口统计"],
      note="MySQL 对照：DATE_SUB(CURDATE(), INTERVAL 6 DAY)。"),

    q(id="G10", cat="WMS实战", level="进阶", title="单据状态分布与占比",
      desc="统计入库单行各单据状态（bill_status）的行数 cnt 和占比 pct（百分比，保留 1 位小数）。",
      hint="占比 = 本组行数 * 100.0 / 总行数，用 ROUND 保留小数。",
      sql="SELECT bill_status, COUNT(*) AS cnt, ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM winv_inbound_order_lines), 1) AS pct FROM winv_inbound_order_lines GROUP BY bill_status",
      tables=["winv_inbound_order_lines"],
      explain=[
          "分子是本状态的行数 COUNT(*)，分母是标量子查询里的全表行数。",
          "乘 100.0 而不是 100，强制走浮点除法，避免整除丢精度。",
          "ROUND(x, 1) 保留 1 位小数，得到类似 66.7 的百分比。",
      ],
      keywords=["ROUND", "标量子查询", "百分比计算", "浮点除法"]),

    q(id="G11", cat="WMS实战", level="入门", title="临期且批次号为 B 开头",
      desc="统计批次档案中批次号（batch_code）以 B 开头、且 attribute7 = '1' 的批次数，列名 cnt。",
      hint="LIKE 'B%' AND attribute7 = '1'",
      sql="SELECT COUNT(*) AS cnt FROM wmdm_batch WHERE batch_code LIKE 'B%' AND attribute7 = '1'",
      tables=["wmdm_batch"],
      explain=[
          "LIKE 'B%' 匹配以 B 开头的批次号（样例数据全部以 B 开头）。",
          "attribute7 = '1' 筛出临期批次。",
          "两个条件是“且”的关系，用 AND 连接，COUNT(*) 数结果行数。",
      ],
      keywords=["LIKE", "AND", "COUNT(*)"]),

    q(id="G12", cat="WMS实战", level="困难", title="SKU 的入库行数与批次数对照",
      desc="以入库单行为主，列出每个 SKU 的入库行数 inbound_cnt 和批次数 batch_cnt（没有批次的显示 0），按 sku 升序。",
      hint="LEFT JOIN 后分别 COUNT(DISTINCT l.id) 和 COUNT(DISTINCT b.id)。",
      sql="SELECT l.sku, COUNT(DISTINCT l.id) AS inbound_cnt, COUNT(DISTINCT b.id) AS batch_cnt FROM winv_inbound_order_lines l LEFT JOIN wmdm_batch b ON b.sku = l.sku GROUP BY l.sku ORDER BY l.sku ASC",
      strict=True, tables=["winv_inbound_order_lines", "wmdm_batch"],
      explain=[
          "以入库行为主表 LEFT JOIN 批次表，保证没有批次的 SKU 也能出现。",
          "直接 COUNT(*) 会因为一对多连接把行数放大（一个 SKU 的 3 条入库 × 2 条批次 = 6 行）。",
          "用 COUNT(DISTINCT l.id) 数入库行、COUNT(DISTINCT b.id) 数批次，避免笛卡尔积放大。",
          "没有批次的 SKU，b.id 全为 NULL，COUNT(DISTINCT b.id) = 0。",
      ],
      keywords=["LEFT JOIN", "COUNT(DISTINCT)", "一对多放大", "NULL 处理"],
      note="多表连接后计数一定要想清楚“连接会不会放大行数”，这是最容易出错的场景之一。"),
]
