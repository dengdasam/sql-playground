# -*- coding: utf-8 -*-
"""验证 SQL 闯关：引擎、判分、自动进下一题、进度、关卡地图、提示/答案、草稿。"""
from playwright.sync_api import sync_playwright
import pathlib

url = (pathlib.Path(__file__).parent / "SQL闯关.html").resolve().as_uri()
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(url)
    pg.wait_for_function("document.getElementById('engineStatus').textContent.includes('就绪')", timeout=30000)
    print("[1] 引擎:", pg.locator("#engineStatus").inner_text())
    print("[1b] 初始关卡:", pg.locator("#curStep").inner_text(), "题号:", pg.locator("#qIdx").inner_text())

    # 第 1 关标准答案 -> 通过 -> 1.6s 后自动进第 2 关
    pg.fill("#editor", "SELECT name FROM world WHERE population > 100000000")
    pg.click("#runBtn")
    v = pg.locator("#verdict").inner_text()
    assert "通关" in v, v
    print("[2] 判分:", v.replace("\n", " / ")[:80])
    assert pg.locator("#curStep").inner_text() == "1", "自动跳转前仍在第一关"
    pg.wait_for_function("document.getElementById('curStep').textContent === '2'", timeout=5000)
    print("[3] 自动进入下一关: 当前 =", pg.locator("#curStep").inner_text(), "题号 =", pg.locator("#qIdx").inner_text())

    # 进度
    assert pg.locator("#sideBig").inner_text() == "1"
    print("[4] 进度: 已通关", pg.locator("#sideBig").inner_text(), "百分比", pg.locator("#topPct").inner_text())

    # 关卡地图：点 J/分类里的某题跳转（G1 是第 28 题，index 27）
    pg.locator('.qnum[data-i="27"]').click()
    assert pg.locator("#qIdx").inner_text() == "Q-G1", pg.locator("#qIdx").inner_text()
    print("[5] 关卡地图跳转:", pg.locator("#qIdx").inner_text(), pg.locator("#qTitle").inner_text())

    # 草稿保存：输入内容后跳到别的题再回来
    pg.fill("#editor", "SELECT 1 AS test_draft")
    pg.click("#prevBtn")
    pg.click("#nextBtn")
    assert pg.locator("#qIdx").inner_text() == "Q-G1"
    assert pg.locator("#editor").input_value() == "SELECT 1 AS test_draft"
    print("[6] 草稿保留: OK")

    # 提示与答案
    pg.click("#hintBtn")
    assert "提示" in pg.locator("#hintBox").inner_text()
    pg.click("#ansBtn")
    assert "标准答案" in pg.locator("#hintBox").inner_text()
    print("[7] 提示/答案展开: OK")

    # 错误答案
    pg.fill("#editor", "SELECT 999 AS wrong")
    pg.click("#runBtn")
    v2 = pg.locator("#verdict").inner_text()
    assert "未通过" in v2, v2
    print("[8] 错误判分:", v2.replace("\n", " / ")[:70])

    # G1 日期题标准答案（在 SQLite 上真实跑）
    ans = pg.evaluate("()=>QUIZ.questions.filter(q=>q.id==='G1')[0].sql")
    pg.fill("#editor", ans)
    pg.click("#runBtn")
    v3 = pg.locator("#verdict").inner_text()
    assert "通关" in v3, v3
    print("[9] WMS 日期题判分:", v3.replace("\n", " / ")[:70])

    # 数据表预览
    pg.click('button[data-tbl="world"]')
    assert pg.locator("#tablePreview table tr").count() > 1
    print("[10] 数据表预览: OK")

    # 刷新后进度与草稿保留
    pg.reload()
    pg.wait_for_function("document.getElementById('engineStatus').textContent.includes('就绪')", timeout=30000)
    assert pg.locator("#sideBig").inner_text() == "2", pg.locator("#sideBig").inner_text()
    print("[11] 刷新后进度:", pg.locator("#sideBig").inner_text())

    print("[12] JS 错误数:", len(errs))
    for e in errs[:3]: print("   !", e)
    assert not errs
    b.close()
print("SQL 闯关全部验证通过")
