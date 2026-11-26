"""验证题库扩充后的两个页面：字段说明块、答案解析步骤、题数、判分与样例表。"""
import pathlib
from playwright.sync_api import sync_playwright

BASE = pathlib.Path(__file__).resolve().parent
errors = []


def wait_ready(pg):
    pg.wait_for_function("document.getElementById('engineStatus').textContent.includes('就绪')", timeout=30000)


def main():
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)

        # ---------------- 练习场 ----------------
        pg = b.new_page()
        js_err = []
        pg.on("pageerror", lambda e: js_err.append(str(e)))
        pg.goto((BASE / "SQL练习场.html").as_uri())
        wait_ready(pg)

        total = pg.locator("#qCount").inner_text().strip()
        print("[1] 题数显示:", total)
        assert total == "57", total

        # 字段说明块：第一题 A1 应显示 world 表 5 个字段
        n_fields = pg.locator("#fieldBox .fc").count()
        field_text = pg.locator("#fieldBox").inner_text()
        print("[2] 字段块字段数:", n_fields)
        assert n_fields >= 5, n_fields
        for kw in ["name", "continent", "area", "population", "gdp"]:
            assert kw in field_text, kw

        # 查看答案 -> 解析步骤 + 关键点
        pg.click("#ansBtn")
        steps = pg.locator("#hintBox .steps li").count()
        kws = pg.locator("#hintBox .kws code").count()
        print("[3] 解析步骤数:", steps, "关键点标签:", kws)
        assert steps >= 2, steps
        assert kws >= 1, kws

        # 判分：填入 A1 标准答案
        ans = pg.evaluate("(id)=>QUIZ.questions.filter(q=>q.id===id)[0].sql", "A1")
        pg.click("#ansBtn")          # 收起
        pg.fill("#editor", ans)
        pg.click("#runBtn")
        verdict = pg.locator("#verdict").inner_text()
        print("[4] A1 判分:", verdict.replace("\n", " / ")[:60])
        assert "✓ 通过" in verdict

        # 换到 WMS 题，检查双表字段块
        pg.select_option("#fCat", "WMS实战")
        wms_fields = pg.locator("#fieldBox .fc").count()
        wms_text = pg.locator("#fieldBox").inner_text()
        print("[5] WMS 字段数:", wms_fields, "| 含 plan_qty:", "plan_qty" in wms_text)
        assert "plan_qty" in wms_text and "creation_date" in wms_text

        # 样例数据表：6 张卡片 + 字段明细表
        cards = pg.locator("#tableList .tcard").count()
        subtbl = pg.locator("#tableList table.subtbl").count()
        print("[6] 样例表卡片:", cards, "字段明细表:", subtbl)
        assert cards == 6 and subtbl == 6, (cards, subtbl)

        # 速查模式：题目条目数 = 57，且含解析步骤
        pg.click("#modeRef")
        details = pg.locator("#refRoot details").count()
        ref_steps = pg.locator("#refRoot .steps li").count()
        print("[7] 速查条目:", details, "解析条目:", ref_steps)
        assert details == 57, details
        assert ref_steps > 0, ref_steps

        print("[8] JS 错误数:", len(js_err), js_err[:3])
        assert not js_err, js_err
        pg.close()

        # ---------------- 闯关 ----------------
        pg2 = b.new_page()
        err2 = []
        pg2.on("pageerror", lambda e: err2.append(str(e)))
        pg2.goto((BASE / "SQL闯关.html").as_uri())
        pg2.wait_for_function("document.getElementById('hintBox')!==null && QUIZ!==undefined", timeout=30000)
        pg2.wait_for_function("document.getElementById('engineStatus').textContent.includes('就绪')", timeout=30000)

        print("[9] 闯关总关数:", pg2.locator("#allStep").inner_text())
        assert pg2.locator("#allStep").inner_text().strip() == "57"

        n2 = pg2.locator("#fieldBox .fc").count()
        print("[10] 闯关字段数:", n2)
        assert n2 >= 5, n2

        pg2.click("#ansBtn")
        s2 = pg2.locator("#hintBox .steps li").count()
        k2 = pg2.locator("#hintBox .kws code").count()
        print("[11] 闯关解析步骤:", s2, "关键点:", k2)
        assert s2 >= 2 and k2 >= 1

        # 判分 + 自动进下一关
        pg2.click("#ansBtn")
        a1 = pg2.evaluate("(id)=>QUIZ.questions.filter(q=>q.id===id)[0].sql", "A1")
        pg2.fill("#editor", a1)
        pg2.click("#runBtn")
        v2 = pg2.locator("#verdict").inner_text()
        print("[12] 闯关判分:", v2.replace("\n", " / ")[:50])
        assert "通关" in v2
        pg2.wait_for_function("document.getElementById('curStep').textContent==='2'", timeout=6000)
        print("[13] 自动进入第 2 关: 通过")

        print("[14] 闯关 JS 错误数:", len(err2), err2[:3])
        assert not err2, err2
        pg2.close()
        b.close()

    print("\n全部验证通过")


if __name__ == "__main__":
    main()
