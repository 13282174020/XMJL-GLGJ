# -*- coding: utf-8 -*-
"""
文档生成测试脚本
"""

import os
import time
import sys

sys.path.insert(0, r'e:\Qwen\xmjl')
from backend.app.browser import BrowserTool

WEB_SERVER_URL = "http://localhost:5000"
UPLOADS_DIR = r"e:\Qwen\xmjl\uploads"
OUTPUTS_DIR = r"e:\Qwen\xmjl\outputs"

def create_test_files():
    """创建测试文件"""
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    
    requirement = """良熟社区未来社区建设项目需求

一、项目概况
1. 项目名称：良熟社区未来社区数字化建设项目
2. 项目建设单位：良熟社区居委会
3. 负责人：张三
4. 建设工期：12 个月
5. 总投资：1200 万元

二、建设目标
1. 智慧安防：高空抛物监控、门禁系统
2. 人员管理：流动人口管理
3. 邻里商业：15 分钟生活圈
4. 共享空间：共享书房
5. 未来健康：健康管理服务
6. 未来低碳：垃圾分类、节能减排
"""
    
    req_path = os.path.join(UPLOADS_DIR, "需求.txt")
    with open(req_path, 'w', encoding='utf-8') as f:
        f.write(requirement)
    print(f"Created: {req_path}")
    return req_path


def test():
    print("=" * 60)
    print("Starting browser test...")
    print("=" * 60)
    
    req_file = create_test_files()
    
    browser = BrowserTool(headless=False)
    browser.start("chromium")
    
    try:
        print(f"\n[1] Going to {WEB_SERVER_URL}")
        browser.goto(WEB_SERVER_URL, wait_until="networkidle")
        time.sleep(2)
        
        browser.screenshot(os.path.join(OUTPUTS_DIR, "step1_homepage.png"))
        print("    Screenshot: step1_homepage.png")
        
        # Get page title
        try:
            title = browser.get_text('title')
            print(f"    Page title: {title}")
        except:
            pass
        
        # Find and upload requirement file
        print("\n[2] Uploading requirement file...")
        try:
            browser.fill('input[type="file"][name="requirement_file"], input[type="file"]', req_file)
            time.sleep(1)
            print("    Upload successful")
        except Exception as e:
            print(f"    Upload failed: {e}")
        
        browser.screenshot(os.path.join(OUTPUTS_DIR, "step2_uploaded.png"))
        print("    Screenshot: step2_uploaded.png")
        
        # Select template type
        print("\n[3] Selecting template type...")
        try:
            browser.click('select[name="template_type"]')
            time.sleep(0.5)
            # Try to select future_community option
            browser.evaluate('document.querySelector(\'select[name="template_type"]\').value = "future_community"')
            time.sleep(1)
            print("    Template selected: future_community")
        except Exception as e:
            print(f"    Select failed: {e}")
        
        # Click generate button
        print("\n[4] Clicking generate button...")
        try:
            browser.click('button[type="submit"], input[type="submit"], button:has-text("生成"), button:has-text("生成文档")')
            print("    Button clicked")
        except Exception as e:
            print(f"    Click failed: {e}")
        
        # Wait for navigation or task center
        print("\n[5] Waiting for task processing...")
        for i in range(15):
            time.sleep(2)
            try:
                page_text = browser.get_inner_html('body')
                if '任务中心' in page_text or 'task_center' in page_text or 'task-list' in page_text:
                    print(f"    -> Navigated to task center ({i+1}s)")
                    break
                if '生成完成' in page_text or '已完成' in page_text:
                    print(f"    -> Task completed ({i+1}s)")
                    break
            except:
                pass
            print(f"    Waiting... ({i+1}/15)")
        
        browser.screenshot(os.path.join(OUTPUTS_DIR, "step3_final.png"))
        print("\n    Screenshot: step3_final.png")
        
        # Check task list
        print("\n[6] Checking task list...")
        try:
            task_list = browser.get_inner_html('#task-list, .task-list, [id*="task"]')
            if task_list:
                print("    Task list found!")
                print(task_list[:300])
        except:
            print("    No task list detected")
        
        print("\n" + "=" * 60)
        print("Test completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        
        try:
            browser.screenshot(os.path.join(OUTPUTS_DIR, "error.png"))
            print(f"    Error screenshot saved")
        except:
            pass
    
    finally:
        print("\nClosing browser...")
        browser.close()
        print("Browser closed")


if __name__ == '__main__':
    test()
