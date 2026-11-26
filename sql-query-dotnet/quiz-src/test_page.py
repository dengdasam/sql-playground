# -*- coding: utf-8 -*-
"""浏览器端验证：引擎加载、判分、速查模式、进度保存。"""
from playwright.sync_api import sync_playwright
import pathlib, time

HTML = pathlib.Path(__file__).parent / "SQL练习场.html"
url = HTML.as_uri()

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(url)
    # 等引擎就绪
    page.wait_for_function("document.getElementById('engineStatus').textContent.includes('就绪')", timeout=30000)
    print("[1] 引擎就绪:", page.locator("#engineStatus").inner_text())

    # 标准答案提交（Q-A1）：期望通过
    page.fill("#editor", "SELECT name FROM world WHERE population > 100000000")
    page.click("#runBtn")
    verdict = page.locator("#verdict").inner_text()
    assert "通过" in verdict and "未通过" not in verdict, verdict
    print("[2] 标准答案判分:", verdict.replace("\n", " / "))

    # 用户结果表有数据
    user_rows = page.locator("#userResult table tr").count()
    print("[3] 用户结果表行数(含表头):", user_rows)
    assert user_rows > 1

    # 错误答案：期望未通过
    page.click("#nextBtn")
    page.fill("#editor", "SELECT name FROM world WHERE population < 100000000")
    page.click("#runBtn")
    verdict2 = page.locator("#verdict").inner_text()
    assert "未通过" in verdict2, verdict2
    print("[4] 错误答案判分:", verdict2.replace("\n", " / "))

    # SQL 语法错误
    page.fill("#editor", "SELEC bad syntax")
    page.click("#runBtn")
    v3 = page.locator("#verdict").inner_text()
    assert "出错" in v3, v3
    print("[5] 语法错误处理:", v3.replace("\n", " / "))

    # 进度保存
    passed = page.locator("#stPassed").inner_text()
    print("[6] 已通过计数:", passed)
    assert passed == "1"

    # 速查模式
    page.click("#modeRef")
    details_count = page.locator("#refRoot details").count()
    print("[7] 速查模式题目数:", details_count)
    assert details_count == 34
    page.locator("#refRoot details").first.click()
    assert page.locator("#refRoot details").first.get_attribute("open") is not None
    print("[8] 速查折叠展开: OK")

    # 数据表预览
    page.click('button[data-tbl="world"]')
    prev = page.locator("#tablePreview table tr").count()
    print("[9] 数据表预览行数(含表头):", prev)
    assert prev > 1

    # 刷新后进度保留
    page.reload()
    page.wait_for_function("document.getElementById('engineStatus').textContent.includes('就绪')", timeout=30000)
    print("[10] 刷新后已通过:", page.locator("#stPassed").inner_text())
    assert page.locator("#stPassed").inner_text() == "1"

    print("[11] 页面 JS 错误数:", len(errors))
    for e in errors[:5]: print("   !", e)
    browser.close()
print("全部浏览器验证通过")
