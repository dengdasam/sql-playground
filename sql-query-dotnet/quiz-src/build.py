# -*- coding: utf-8 -*-
"""SQL 练习场构建脚本：验证题库答案 -> 生成单文件 HTML（内嵌 sql.js + wasm + 数据）。"""
import base64, json, sqlite3, datetime, random, os, shutil

BASE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(BASE, "assets")
HTML_PATH = os.path.join(BASE, "SQL练习场.html")

# ---------------- 样例数据（SQLite 方言，所有题目答案都在这上面跑） ----------------
STATIC_SCHEMA = """
CREATE TABLE world(name TEXT, continent TEXT, area INTEGER, population INTEGER, gdp REAL);
INSERT INTO world VALUES
('Afghanistan','Asia',647857,25500100,20343000000),
('Albania','Europe',28748,2831741,12960000000),
('Algeria','Africa',2381741,37100000,188681000000),
('Andorra','Europe',468,78115,3712000000),
('Angola','Africa',1246700,20609294,100990000000),
('Argentina','South America',2780400,41324992,632000000000),
('Australia','Oceania',7692065,23312700,1454000000000),
('Austria','Europe',83855,8754400,428900000000),
('Brazil','South America',8515767,205962976,2259100000000),
('Canada','North America',9984670,35427524,1785000000000),
('China','Asia',9600000,1364270000,10357200000000),
('France','Europe',551695,66350000,2473000000000),
('Germany','Europe',357022,81830700,3868000000000),
('India','Asia',3287590,1251697540,2034500000000),
('Indonesia','Asia',1904569,252801700,1024700000000),
('Japan','Asia',377972,127550000,5210000000000),
('Mexico','North America',1964375,121736809,1151200000000),
('Nigeria','Africa',923768,177155000,568800000000),
('Russia','Europe',17098242,143439290,2090000000000),
('South Africa','Africa',1221037,53898000,377800000000),
('United Kingdom','Europe',243610,63810000,2949000000000),
('United States','North America',9833517,321783533,17968000000000);

CREATE TABLE nobel(yr INTEGER, subject TEXT, winner TEXT);
INSERT INTO nobel VALUES
(2000,'Chemistry','Alan J. Heeger'),(2000,'Chemistry','Alan G. MacDiarmid'),(2000,'Chemistry','Hideki Shirakawa'),
(2000,'Physics','Zhores Alferov'),(2000,'Physics','Herbert Kroemer'),(2000,'Physics','Jack Kilby'),
(2000,'Literature','Gao Xingjian'),(2000,'Economics','James Heckman'),(2000,'Economics','Daniel McFadden'),
(2000,'Medicine','Arvid Carlsson'),(2000,'Medicine','Paul Greengard'),(2000,'Medicine','Eric Kandel'),
(2001,'Physics','Eric A. Cornell'),(2001,'Physics','Carl E. Wieman'),(2001,'Physics','Wolfgang Ketterle'),
(2001,'Chemistry','William S. Knowles'),(2001,'Chemistry','Ryoji Noyori'),(2001,'Chemistry','K. Barry Sharpless'),
(2001,'Literature','V. S. Naipaul'),(2001,'Economics','George A. Akerlof'),(2001,'Economics','A. Michael Spence'),
(2001,'Economics','Joseph E. Stiglitz'),(2001,'Medicine','Leland H. Hartwell'),(2001,'Medicine','Tim Hunt'),
(2001,'Medicine','Sir Paul Nurse'),(2002,'Physics','Raymond Davis Jr.'),(2002,'Physics','Masatoshi Koshiba'),
(2002,'Physics','Riccardo Giacconi'),(2002,'Chemistry','John B. Fenn'),(2002,'Chemistry','Koichi Tanaka'),
(2002,'Chemistry','Kurt Wuthrich'),(2002,'Literature','Imre Kertesz'),(2002,'Economics','Daniel Kahneman'),
(2002,'Economics','Vernon L. Smith'),(2002,'Medicine','Sydney Brenner'),(2002,'Medicine','H. Robert Horvitz'),
(2002,'Medicine','John E. Sulston'),(2003,'Physics','Alexei Abrikosov'),(2003,'Physics','Vitaly Ginzburg'),
(2003,'Physics','Anthony Leggett'),(2003,'Chemistry','Peter Agre'),(2003,'Chemistry','Roderick MacKinnon'),
(2003,'Literature','J. M. Coetzee'),(2003,'Economics','Robert F. Engle'),(2003,'Economics','Clive W. J. Granger'),
(2003,'Medicine','Paul Lauterbur'),(2003,'Medicine','Sir Peter Mansfield'),
(2004,'Physics','David Gross'),(2004,'Physics','H. David Politzer'),(2004,'Physics','Frank Wilczek'),
(2004,'Chemistry','Aaron Ciechanover'),(2004,'Chemistry','Avram Hershko'),(2004,'Chemistry','Irwin Rose'),
(2004,'Literature','Elfriede Jelinek'),(2004,'Economics','Finn E. Kydland'),(2004,'Economics','Edward C. Prescott'),
(2004,'Medicine','Linda B. Buck'),(2004,'Medicine','Richard Axel'),
(2005,'Physics','Roy Glauber'),(2005,'Physics','John Hall'),(2005,'Physics','Theodor Hansch'),
(2005,'Chemistry','Yves Chauvin'),(2005,'Chemistry','Robert H. Grubbs'),(2005,'Chemistry','Richard R. Schrock'),
(2005,'Literature','Harold Pinter'),(2005,'Economics','Robert J. Aumann'),(2005,'Economics','Thomas C. Schelling'),
(2005,'Medicine','Barry J. Marshall'),(2005,'Medicine','J. Robin Warren'),
(2006,'Physics','John Mather'),(2006,'Physics','George Smoot'),
(2006,'Chemistry','Edmond Fischer'),(2006,'Chemistry','Edwin Krebs'),(2006,'Chemistry','Tony Hunter'),
(2006,'Literature','Orhan Pamuk'),(2006,'Economics','Edmund Phelps'),
(2006,'Medicine','Andrew Fire'),(2006,'Medicine','Craig Mello'),
(2010,'Physics','Andre Geim'),(2010,'Physics','Konstantin Novoselov'),
(2010,'Chemistry','Richard Heck'),(2010,'Chemistry','Ei-ichi Negishi'),(2010,'Chemistry','Akira Suzuki'),
(2010,'Literature','Mario Vargas Llosa'),(2010,'Economics','Peter A. Diamond'),
(2010,'Economics','Dale T. Mortensen'),(2010,'Economics','Christopher A. Pissarides'),
(2010,'Medicine','Robert G. Edwards'),
(2015,'Physics','Takaaki Kajita'),(2015,'Physics','Arthur B. McDonald'),
(2015,'Chemistry','Tomas Lindahl'),(2015,'Chemistry','Paul Modrich'),(2015,'Chemistry','Aziz Sancar'),
(2015,'Literature','Svetlana Alexievich'),(2015,'Economics','Angus Deaton'),
(2015,'Medicine','William C. Campbell'),(2015,'Medicine','Satoshi Omura'),(2015,'Medicine','Tu Youyou');

CREATE TABLE dept(id INTEGER, name TEXT);
INSERT INTO dept VALUES(1,'IT'),(2,'Sales'),(3,'HR'),(4,'Finance');
CREATE TABLE emp(id INTEGER, name TEXT, salary INTEGER, dept_id INTEGER);
INSERT INTO emp VALUES
(1,'Joe',70000,1),(2,'Jim',90000,1),(3,'Henry',80000,2),(4,'Sam',60000,2),
(5,'Max',90000,1),(6,'Janet',69000,1),(7,'Randy',85000,1),(8,'Will',70000,3);
"""

WMS_SCHEMA = """
CREATE TABLE winv_inbound_order_lines(
  id INTEGER, creation_date TEXT, sku TEXT, owner_id INTEGER, plan_qty REAL,
  source_system_code TEXT, bill_status TEXT, tenant_id INTEGER
);
CREATE TABLE wmdm_batch(
  id INTEGER, creation_date TEXT, sku TEXT, owner_id INTEGER, batch_code TEXT,
  attribute7 TEXT, tenant_id INTEGER
);
"""

def make_wms_inserts():
    """生成最近 40 天的 WMS 样例数据（锚定今天，答案用 date('now') 判定，判分是结果集自比对，跨天也一致）。"""
    today = datetime.date.today()
    rnd = random.Random(20261126)
    lines, batches = [], []
    lid, bid = 1, 1
    skus = ['SKU-BEER-001','SKU-BEER-002','SKU-GLASS-500','SKU-LABEL-A','SKU-CAP-01']
    systems = ['ERP','SRM','WMS']
    for d in range(40, -1, -1):
        day = today - datetime.timedelta(days=d)
        ds = day.isoformat()
        n = rnd.randint(1, 5)
        for _ in range(n):
            ts = "%s %02d:%02d:00" % (ds, rnd.randint(8,19), rnd.randint(0,59))
            lines.append((lid, ts, rnd.choice(skus), rnd.choice([1,2]),
                          round(rnd.uniform(10, 500), 3), rnd.choice(systems),
                          rnd.choice(['COMPLETED','RECEIVING']), 1)); lid += 1
        m = rnd.randint(1, 3)
        for _ in range(m):
            ts = "%s %02d:%02d:00" % (ds, rnd.randint(8,19), rnd.randint(0,59))
            batches.append((bid, ts, rnd.choice(skus[:3]), rnd.choice([1,2]),
                            'B%s%03d' % (day.strftime('%Y%m%d'), bid),
                            rnd.choice(['1','0']), 1)); bid += 1
    def vals(rows):
        return ";".join("INSERT INTO %s VALUES(%s);" % (
            table, ",".join("'%s'" % v if isinstance(v, str) else str(v) for v in row))
            for table, rows2 in [(table, rows)] for row in rows2)
    # 上面写法冗长，直接分表拼
    def ins(table, rows):
        out = []
        for row in rows:
            cells = ",".join("'%s'" % v if isinstance(v, str) else str(v) for v in row)
            out.append("INSERT INTO %s VALUES(%s);" % (table, cells))
        return "\n".join(out)
    return ins("winv_inbound_order_lines", lines) + "\n" + ins("wmdm_batch", batches)

# ---------------- 题库（定义在 qbank.py，两个前端共用同一份） ----------------
from qbank import Q, TABLE_DICT, CATS, LEVELS

# ---------------- 验证 ----------------
def build_db():
    con = sqlite3.connect(":memory:")
    con.executescript(STATIC_SCHEMA)
    con.executescript(WMS_SCHEMA)
    con.executescript(make_wms_inserts())
    return con

def cell(v):
    if v is None: return ""
    return str(v)

def result_set(rows):
    return sorted(tuple(cell(v) for v in r) for r in rows)

def validate():
    con = build_db()
    errors = []
    for item in Q:
        qid = item["id"]
        try:
            cur = con.execute(item["sql"])
            rows = cur.fetchall()
            if not rows:
                errors.append("%s: 结果为空 -> %s" % (qid, item["sql"]))
            else:
                print("%-3s %-6s %-4s rows=%-4d %s" % (
                    qid, item["cat"], item["level"], len(rows), item["title"]))
        except Exception as e:
            errors.append("%s: %s | SQL=%s" % (qid, e, item["sql"]))

    # 结构完整性：表名必须在字段字典里，每题必须有解析步骤
    for item in Q:
        for t in item["tables"]:
            if t not in TABLE_DICT:
                errors.append("%s: tables 引用了未知表 %s" % (item["id"], t))
        if not item["tables"]:
            errors.append("%s: 未标注涉及的表" % item["id"])
        if not item["explain"]:
            errors.append("%s: 缺少解题步骤 explain" % item["id"])

    print("\n题数:", len(Q), " 表数:", len(TABLE_DICT), " 错误:", len(errors))
    for e in errors: print("  !!", e)
    if errors: raise SystemExit("题库验证失败")
    return con

# ---------------- 生成 ----------------
def js_str(s):
    return json.dumps(s, ensure_ascii=False)

def make_data_js():
    questions = [dict(id=it["id"], cat=it["cat"], level=it["level"], title=it["title"],
                      desc=it["desc"], hint=it["hint"], sql=it["sql"], strict=it["strict"],
                      note=it["note"], tables=it["tables"],
                      explain=it["explain"], keywords=it["keywords"])
                 for it in Q]
    table_dict = {name: dict(label=t["label"], desc=t["desc"],
                             cols=[dict(name=c[0], type=c[1], desc=c[2], sample=c[3])
                                   for c in t["cols"]])
                  for name, t in TABLE_DICT.items()}
    data = dict(questions=questions, cats=CATS, levels=LEVELS,
                schema=STATIC_SCHEMA.strip() + "\n" + WMS_SCHEMA.strip(),
                wmsInserts=make_wms_inserts(),
                tableDict=table_dict,
                # 兼容壳：旧版页面按“字段串 + 描述”展示，新模板优先用 tableDict
                tableInfo=[
                    dict(name=name, cols=", ".join(c[0] for c in t["cols"]),
                         rows=0, desc=t["desc"]) for name, t in TABLE_DICT.items()
                ])
    return "const QUIZ = " + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";"

# (源模板, 输出文件) —— 题库与引擎共用一份，产出两个互相独立的 HTML
BUILD_TARGETS = [
    ("SQL练习场.template.html", "SQL练习场.html"),   # 双模式：答题 + 速查
    ("SQL闯关.template.html",   "SQL闯关.html"),     # SQLZoo 式分步引导
]

def build_one(template_name, output_name):
    # 模板统一放在 src/ 下，根目录只留可直接双击的成品，避免误开模板看到空白页
    tpl = os.path.join(BASE, "src", template_name)
    out = os.path.join(BASE, output_name)
    with open(tpl, "r", encoding="utf-8") as f:
        html = f.read()
    missing = [p for p in ("/*__SQLJS_LIB__*/", "/*__QUIZ_DATA__*/", "/*__WASM_B64__*/") if p not in html]
    if missing:
        raise SystemExit("%s 缺少占位符: %s" % (template_name, missing))
    with open(os.path.join(ASSETS, "sql-wasm.js"), "r", encoding="utf-8") as f:
        lib = f.read()
    with open(os.path.join(ASSETS, "sql-wasm.wasm"), "rb") as f:
        wasm_b64 = base64.b64encode(f.read()).decode("ascii")
    html = html.replace("/*__SQLJS_LIB__*/", lib)
    html = html.replace("/*__QUIZ_DATA__*/", make_data_js())
    html = html.replace("/*__WASM_B64__*/", wasm_b64)
    html = html.replace("__QCOUNT__", str(len(Q)))
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print("生成完成: %-22s %.1f MB" % (output_name, os.path.getsize(out)/1024/1024))

def build_html():
    validate()
    for tpl, out in BUILD_TARGETS:
        build_one(tpl, out)
    sync_to_webapp()


# ---------------- 同步给 .NET 版查询页 ----------------
# 查询页（wwwroot/index.html）的侧栏有「SQL 题库」入口，链接到 /quiz/practice.html 与 /quiz/challenge.html；
# 这两个文件由本脚本在构建后复制过去，发布 exe 时会随 wwwroot 一起打进产物。
#
# 目录合并后本脚本位于 <工程根>/quiz-src/，所以工程根就是上一级。
# wwwroot/quiz/*.html 是**构建产物**，不入库（见 .gitignore），改题后必须重跑本脚本。
PROJECT_DOTNET = os.path.dirname(BASE)
WEBAPP_QUIZ = os.path.join(PROJECT_DOTNET, "SqlPlayground", "wwwroot", "quiz")
SYNC_MAP = [("SQL练习场.html", "practice.html"), ("SQL闯关.html", "challenge.html")]


def sync_to_webapp():
    """把成品复制到 .NET 版的静态目录。

    目标文件不入库，所以这里是它们唯一的来源：找不到工程目录直接报错退出，
    而不是静默跳过——静默跳过会让发布出来的 exe 缺题库页面，且很难察觉。
    """
    if not os.path.isdir(os.path.join(PROJECT_DOTNET, "SqlPlayground")):
        raise SystemExit(
            "错误：未找到 SqlPlayground 工程目录（%s）。\n"
            "本脚本应位于 <工程根>/quiz-src/ 下，请不要单独移动它。" % PROJECT_DOTNET)
    os.makedirs(WEBAPP_QUIZ, exist_ok=True)
    for src_name, dst_name in SYNC_MAP:
        src = os.path.join(BASE, src_name)
        dst = os.path.join(WEBAPP_QUIZ, dst_name)
        shutil.copyfile(src, dst)
        print("已同步 wwwroot/quiz/%-14s %.1f MB" % (dst_name, os.path.getsize(dst) / 1024 / 1024))

if __name__ == "__main__":
    if os.environ.get("VALIDATE_ONLY") == "1":
        validate()
    else:
        build_html()
