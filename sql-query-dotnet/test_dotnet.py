# -*- coding: utf-8 -*-
"""验证 .NET 全栈版：控制器反代 + API 信封 + 页面表格/图表 + 只读拦截。"""
from playwright.sync_api import sync_playwright
import urllib.request, json

BASE = "http://127.0.0.1:5288"

def get(path):
    return json.loads(urllib.request.urlopen(BASE + path).read().decode("utf-8"))

def post(path, obj):
    req = urllib.request.Request(BASE + path, data=json.dumps(obj).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req).read().decode("utf-8"))

# 控制端点
st = get("/control/status")
assert st["running"] and st["backendUrl"] == "http://127.0.0.1:5280"
print("[1] 控制器状态: running =", st["running"], "pid =", st["pid"])

# health（经控制器反代，ApiEnvelope 信封）
h = get("/api/health")
assert h["success"] and h["data"]["ok"] and h["data"]["service"] == "SqlPlayground"
print("[2] health:", h["data"]["db"], h["data"]["engine"], h["data"]["provider"])

# tables
t = get("/api/tables")
assert t["success"] and len(t["data"]["tables"]) == 6
print("[3] 表数量:", len(t["data"]["tables"]))

# query
r = post("/api/query", {"sql": "SELECT name,population FROM world ORDER BY population DESC LIMIT 3"})
assert r["success"] and r["data"]["rowCount"] == 3 and r["data"]["rows"][0][0] == "China"
print("[4] 查询:", r["data"]["rows"][:2], "耗时", r["data"]["elapsedMs"], "ms")

# 只读拦截
e = post("/api/query", {"sql": "DELETE FROM world"})
assert not e["success"] and e["error"]["code"] == "READONLY_VIOLATION"
print("[5] 只读拦截:", e["error"]["code"], e["error"]["message"])

e2 = post("/api/query", {"sql": "SELECT 1; SELECT 2"})
assert not e2["success"] and e2["error"]["code"] == "MULTI_STATEMENT"
print("[6] 多语句拦截:", e2["error"]["code"])

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_page()
    errs = []
    pg.on("pageerror", lambda err: errs.append(str(err)))
    pg.goto(BASE)
    pg.wait_for_function("document.getElementById('status').textContent.includes('已连接')", timeout=10000)
    print("[7] 页面状态:", pg.locator("#status").inner_text().replace("\n", " / "))
    assert pg.locator("#schemaBody tr").count() == 6

    pg.click("#runBtn")
    pg.wait_for_function("document.getElementById('resTitle').textContent.includes('5 行')", timeout=10000)
    print("[8] 查询结果:", pg.locator("#resTitle").inner_text())
    assert pg.locator("#tableWrap table tr").count() == 6

    pg.click("#tabChart")
    assert pg.locator("#chartWrap svg").count() == 1
    print("[9] 柱状图:", pg.locator("#chartWrap svg").get_attribute("viewBox"))

    pg.locator(".example[data-i='0']").click()
    pg.click("#runBtn")
    pg.wait_for_function("document.getElementById('resTitle').textContent.includes('30 行')", timeout=10000)
    pg.click("#tabChart")
    assert pg.locator("#chartWrap svg polyline.line").count() >= 1
    print("[10] 折线图: polyline =", pg.locator("#chartWrap svg polyline.line").count())

    pg.locator(".example[data-i='5']").click()
    pg.click("#runBtn")
    pg.wait_for_function("document.getElementById('resTitle').textContent.includes('3 行')", timeout=10000)
    pg.click("#tabChart")
    assert pg.locator("#chartWrap svg path.slice").count() == 3
    print("[11] 饼图扇区:", pg.locator("#chartWrap svg path.slice").count())

    pg.fill("#editor", "DELETE FROM world")
    pg.click("#runBtn")
    pg.wait_for_selector("#err.show", timeout=10000)
    print("[12] 错误提示:", pg.locator("#err").inner_text()[:60])
    assert "检测到写入" in pg.locator("#err").inner_text()

    print("[13] JS 错误数:", len(errs))
    for x in errs[:3]: print("   !", x)
    assert not errs
    b.close()
print("全部验证通过")
