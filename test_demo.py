"""金融 Agent 平台 Demo 全链路验证脚本"""
from playwright.sync_api import sync_playwright
import time

BASE = "http://localhost:3001"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 900})

    # ========================================
    # 1. 登录页
    # ========================================
    print("1. 打开登录页...")
    page.goto(f"{BASE}/login", wait_until="networkidle")
    page.screenshot(path="/tmp/demo_01_login.png", full_page=True)
    print("   截图: /tmp/demo_01_login.png")

    # 填写表单
    page.fill('input[type="email"]', "test@test.com")
    page.fill('input[type="password"]', "123456")
    page.screenshot(path="/tmp/demo_02_login_filled.png", full_page=True)
    print("2. 填写登录表单 → 截图: /tmp/demo_02_login_filled.png")

    # 点击登录
    page.click('button[type="submit"]')
    page.wait_for_url("**/dashboard**", timeout=10000)
    page.wait_for_load_state("networkidle")
    print("3. 登录成功，已跳转 Dashboard")

    page.screenshot(path="/tmp/demo_03_dashboard.png", full_page=True)
    print("   截图: /tmp/demo_03_dashboard.png")

    # ========================================
    # 2. 验证 Commander 卡片存在
    # ========================================
    commander_heading = page.locator("text=Commander 智能分析")
    if commander_heading.is_visible():
        print("4. ✅ Commander 智能分析卡片可见")
    else:
        print("4. ❌ Commander 卡片未找到！")
        browser.close()
        exit(1)

    # 检查建议问题按钮
    has_hints = page.locator("text=试试").is_visible()
    print(f"   建议问题快捷按钮: {'有' if has_hints else '无'}")

    # ========================================
    # 3. 输入分析问题
    # ========================================
    print("\n5. 输入测试问题...")
    textarea = page.locator("textarea").first
    textarea.fill("分析贵州茅台(600519)的基本面、行业地位和主要风险")

    page.screenshot(path="/tmp/demo_04_input.png", full_page=True)
    print("   截图: /tmp/demo_04_input.png")

    # ========================================
    # 4. 触发分析
    # ========================================
    print("6. 点击「智能分析」按钮...")
    analyze_btn = page.locator("button").filter(has_text="智能分析")
    analyze_btn.click()

    # 等待 loading 出现
    page.wait_for_timeout(2000)
    page.screenshot(path="/tmp/demo_05_loading.png", full_page=True)
    print("   截图: /tmp/demo_05_loading.png")

    # ========================================
    # 5. 等待分析完成（最多 4 分钟）
    # ========================================
    print("7. 等待 Commander 分析完成（最长 4 分钟）...")
    try:
        # 等待 "分析完成" 或 "综合报告" 出现
        page.wait_for_selector("text=综合报告", timeout=240_000)
        print("   ✅ 分析完成！")
    except Exception as e:
        # 检查是否有错误
        error_card = page.locator("text=分析未能完成")
        if error_card.is_visible():
            print(f"   ❌ 分析失败，错误信息: {page.locator('text=分析未能完成').text_content()}")
        else:
            print(f"   ❌ 超时，检查最终状态")

    page.wait_for_timeout(1500)
    page.screenshot(path="/tmp/demo_06_result.png", full_page=True)
    print("   截图: /tmp/demo_06_result.png")

    # ========================================
    # 6. 验证结果区
    # ========================================
    print("\n8. 验证结果区...")

    # 检查编排计划
    plan_section = page.locator("text=编排计划")
    print(f"   编排计划: {'✅' if plan_section.is_visible() else '❌'}")

    # 检查专家分析详情
    detail_section = page.locator("text=专家分析详情")
    print(f"   专家详情: {'✅' if detail_section.is_visible() else '❌'}")

    # 检查综合报告
    report_section = page.locator("text=综合报告")
    print(f"   综合报告: {'✅' if report_section.is_visible() else '❌'}")

    # 检查折叠面板
    details_elements = page.locator("details")
    count = details_elements.count()
    print(f"   可展开专家面板: {count} 个")
    if count > 0:
        # 展开第一个
        details_elements.first.evaluate("el => el.setAttribute('open', '')")
        page.wait_for_timeout(500)
        page.screenshot(path="/tmp/demo_07_expanded.png", full_page=True)
        print("   展开第一个专家 → 截图: /tmp/demo_07_expanded.png")

    # 检查操作链接
    task_link = page.locator("text=查看任务详情")
    print(f"   任务详情链接: {'✅' if task_link.is_visible() else '❌'}")

    page.screenshot(path="/tmp/demo_08_fullpage.png", full_page=True)
    print("\n=========== 验证完成 ===========")
    browser.close()
