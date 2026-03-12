# -*- coding: utf-8 -*-
"""
文档生成测试脚本
测试 4-6 级标题生成
"""

import os
import time
import sys

sys.path.insert(0, r'e:\Qwen\xmjl')
from backend.app.browser import BrowserTool

WEB_SERVER_URL = "http://localhost:5000"
UPLOADS_DIR = r"e:\Qwen\xmjl\uploads"
OUTPUTS_DIR = r"e:\Qwen\xmjl\outputs"


def test_heading_levels():
    """测试 4-6 级标题生成"""
    from web_system.app import (
        scan_template_styles,
        build_chapter_tree,
        generate_chapter_numbering,
        get_heading_level,
        print_chapter_tree
    )
    
    print("\n" + "="*60)
    print("测试：4-6 级标题生成")
    print("="*60)
    
    # 测试 1: 标题级别检测
    print("\n[测试 1] 标题级别检测")
    print("-"*60)
    
    test_cases = [
        ('Heading 1', '第一章 项目概况', 1),
        ('Heading 2', '1.1 项目名称', 2),
        ('Heading 3', '1.1.1 项目背景', 3),
        ('Heading 4', '1.1.1.1 详细内容', 4),
        ('Heading 5', '1.1.1.1.1 细节说明', 5),
        ('Heading 6', '1.1.1.1.1.1 补充信息', 6),
        ('标题 1', '第一章 测试', 1),
        ('标题 4', '1.1.1.1 测试', 4),
        ('标题 5', '1.1.1.1.1 测试', 5),
        ('标题 6', '1.1.1.1.1.1 测试', 6),
        ('Normal', '正文内容', 0),
    ]
    
    passed = 0
    failed = 0
    for style_name, text, expected in test_cases:
        level = get_heading_level(style_name, text)
        status = "✓" if level == expected else "✗"
        if level == expected:
            passed += 1
        else:
            failed += 1
        print(f"{status} 样式='{style_name}', 文本='{text[:20]}' => 级别={level} (期望={expected})")
    
    print(f"\n级别检测：通过={passed}, 失败={failed}")
    
    # 测试 2: 章节树构建
    print("\n[测试 2] 章节树构建（模拟 4-6 级标题）")
    print("-"*60)
    
    headings = [
        {'level': 1, 'text': '4 现况分析及差距', 'style': 'Heading 1', 'numbering': ''},
        {'level': 2, 'text': '4.2 现况分析及差距', 'style': 'Heading 2', 'numbering': ''},
        {'level': 3, 'text': '4.2.1 信息化建设现状分析', 'style': 'Heading 3', 'numbering': ''},
        {'level': 4, 'text': '建设单位信息化建设应用情况', 'style': 'Heading 4', 'numbering': ''},
        {'level': 5, 'text': '系统建设情况', 'style': 'Heading 5', 'numbering': ''},
        {'level': 6, 'text': '硬件系统现状', 'style': 'Heading 6', 'numbering': ''},
    ]
    
    print("\n原始标题列表:")
    for h in headings:
        print(f"  L{h['level']}: {h['text']}")
    
    # 生成编号
    headings = generate_chapter_numbering(headings)
    
    print("\n生成编号后:")
    for h in headings:
        print(f"  L{h['level']}: {h['numbering']} - {h['text']}")
    
    # 构建树
    chapters = build_chapter_tree(headings)
    
    print("\n构建的章节树:")
    print_chapter_tree(chapters, 0)
    
    # 验证级别
    def verify_levels(nodes, expected_level=1):
        for node in nodes:
            if node['level'] != expected_level:
                print(f"✗ 级别错误：节点 '{node['title']}' 的级别={node['level']}, 期望={expected_level}")
                return False
            children = node.get('children')
            if children:
                if not verify_levels(children, expected_level + 1):
                    return False
        return True
    
    print("\n验证级别:")
    if verify_levels(chapters, 1):
        print("✓ 所有节点级别正确")
    else:
        print("✗ 存在级别错误的节点")
    
    # 测试 3: 扫描实际文档
    print("\n[测试 3] 扫描实际文档")
    print("-"*60)
    
    outputs_dir = OUTPUTS_DIR
    if os.path.exists(outputs_dir):
        # 查找包含 4-6 级标题的文档
        test_files = [
            '建设方案_20260312_003354.docx',
            'partial_34fb646c.docx',
        ]
        
        for filename in test_files:
            filepath = os.path.join(outputs_dir, filename)
            if os.path.exists(filepath):
                print(f"\n扫描文件：{filepath}")
                result = scan_template_styles(filepath)
                if result['success']:
                    print(f"✓ 扫描成功：{result['message']}")
                    print(f"  总节点数：{result['total_nodes']}")
                else:
                    print(f"✗ 扫描失败：{result['message']}")
            else:
                print(f"文件不存在：{filepath}")
        
        # 列出所有 docx 文件
        print("\noutputs 目录下的所有 docx 文件:")
        for f in os.listdir(outputs_dir):
            if f.endswith('.docx'):
                print(f"  - {f}")
    else:
        print(f"outputs 目录不存在：{outputs_dir}")
    
    print("\n" + "="*60)
    print("测试完成")
    print("="*60)


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


def test_clean_ai():
    """测试 clean_ai_content 函数"""
    import sys
    sys.path.insert(0, r'e:\Qwen\xmjl\web_system')
    from ai_engine import clean_ai_content
    
    print("\n" + "="*60)
    print("测试 clean_ai_content 函数")
    print("="*60)
    
    test_cases = [
        {'name': '测试 1: 以"建议"开头的正文', 'section_title': '建议', 'input': '建议结合《浙江省公共安全技术防范条例》，加快部署高空抛物探头。', 'expect_keep': True},
        {'name': '测试 2: 纯标题行', 'section_title': '建议', 'input': '建议', 'expect_keep': False},
        {'name': '测试 3: Markdown 标题', 'section_title': '建议', 'input': '## 建议\n建议结合《条例》...', 'expect_keep': True},
        {'name': '测试 4: 括号标题', 'section_title': '建议', 'input': '【建议】\n建议结合《条例》...', 'expect_keep': True},
        {'name': '测试 5: 多行内容', 'section_title': '建议', 'input': '建议结合《浙江省公共安全技术防范条例》。\n加快部署高空抛物探头。\n升级监控设备。', 'expect_keep': True},
        {'name': '测试 6: 建设目标章节', 'section_title': '建设目标', 'input': '建设目标如下：\n1. 提升社区安全水平\n2. 完善基础设施', 'expect_keep': True},
        {'name': '测试 7: 纯标题', 'section_title': '建设目标', 'input': '建设目标', 'expect_keep': False},
    ]
    
    passed = 0
    failed = 0
    
    for case in test_cases:
        print(f"\n{case['name']}")
        print("-" * 60)
        print(f"输入：{case['input'][:50]}...")
        
        result = clean_ai_content(case['input'], case['section_title'])
        
        print(f"输出：{result[:50] if result else '(空)'}...")
        print(f"输出长度：{len(result)}")
        
        has_content = len(result) > 0
        should_have_content = case['expect_keep'] and len(case['input']) > len(case['section_title'])
        
        if should_have_content and has_content:
            print("PASS - 正确保留了正文内容")
            passed += 1
        elif not should_have_content and not has_content:
            print("PASS - 正确过滤了纯标题")
            passed += 1
        elif should_have_content and not has_content:
            print("FAIL - 错误地过滤了正文内容")
            failed += 1
        else:
            print("? 结果异常")
            failed += 1
    
    print("\n" + "="*60)
    print(f"测试结果：通过={passed}, 失败={failed}")
    print("="*60)
    
    # 模拟真实 AI 输出测试
    print("\n" + "="*60)
    print("模拟真实 AI 输出测试")
    print("="*60)
    
    ai_output = """建议结合《浙江省公共安全技术防范条例》（2021 年修订）及 GB 50348-2018《安全防范工程技术标准》，加快部署高空抛物探头、单元门禁系统及烟感设备，升级监控设备以解决车牌识别率低、电瓶车盗窃等问题，同步开发"平安码"功能提升安防管控效率。依据《浙江省流动人口居住登记条例》（2020 年施行）及 GB/T 28181-2016 标准，构建流动人口、陌生人及暂居人员管控机制，开展社区人员结构分析，优化社区活动策划。参照 DB33/T 1234-2020《智慧社区建设规范》，推进与区平台的系统对接，结合回迁小区的属性进行个性化开发，确保管理适配性。依托邻里中心及商铺资源，建设共享书房与邻里街，完善 15 分钟生活圈配套。依据《浙江省物业管理条例》（20..."""
    
    result = clean_ai_content(ai_output, '建议')
    print(f"AI 输出长度：{len(ai_output)}")
    print(f"清理后长度：{len(result)}")
    if len(result) > 0:
        print(f"清理后前 50 字：{result[:50]}...")
        print("PASS - 成功保留正文内容")
    else:
        print("FAIL - 正文内容被错误过滤")
    
    print("\n测试完成\n")


if __name__ == '__main__':
    test_clean_ai()

