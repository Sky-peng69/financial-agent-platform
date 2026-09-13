"""弈金平台演示入口验证脚本。"""
from playwright.sync_api import sync_playwright

BASE = "http://localhost:3001"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 900})

    print("1. 打开首页，验证自动进入体验用户...")
    page.goto(BASE, wait_until="networkidle")
    page.wait_for_url("**/dashboard", timeout=15000)
    page.screenshot(path="/tmp/demo_01_dashboard.png", full_page=True)
    print("   截图: /tmp/demo_01_dashboard.png")

    print("2. 验证工作台聊天入口...")
    if not page.locator("text=Commander 智能分析").is_visible():
        raise AssertionError("未找到 Commander 智能分析入口")
    if not page.locator("textarea").first.is_visible():
        raise AssertionError("未找到聊天输入框")
    if not page.locator("button").filter(has_text="附件").is_visible():
        raise AssertionError("未找到附件按钮")
    print("   工作台聊天框和附件入口可见")

    print("3. 验证公司研究入口...")
    page.goto(f"{BASE}/dashboard/research", wait_until="networkidle")
    if not page.locator("text=公司研究").first.is_visible():
        raise AssertionError("未找到公司研究页面")
    if not page.locator("text=创建研究对象").is_visible():
        raise AssertionError("未找到创建研究对象按钮")
    page.screenshot(path="/tmp/demo_02_research.png", full_page=True)
    print("   截图: /tmp/demo_02_research.png")

    print("=========== 验证完成 ===========")
    browser.close()
