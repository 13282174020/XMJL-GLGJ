# -*- coding: utf-8 -*-
"""测试 clean_ai_content 函数修复效果"""
import sys
sys.path.insert(0, r'e:\Qwen\xmjl')
sys.path.insert(0, r'e:\Qwen\xmjl\web_system')

from ai_engine import clean_ai_content

print("\n" + "="*60)
print("测试 clean_ai_content 函数修复效果")
print("="*60)

# 测试用例
test_cases = [
    {
        'name': '测试 1: 以"建议"开头的正文（原问题）',
        'section_title': '建议',
        'input': '建议结合《浙江省公共安全技术防范条例》，加快部署高空抛物探头。',
        'expect_keep': True
    },
    {
        'name': '测试 2: 纯标题行 "建议"',
        'section_title': '建议',
        'input': '建议',
        'expect_keep': False
    },
    {
        'name': '测试 3: Markdown 标题 "## 建议"',
        'section_title': '建议',
        'input': '## 建议\n建议结合《条例》...',
        'expect_keep': True
    },
    {
        'name': '测试 4: 括号标题 "【建议】"',
        'section_title': '建议',
        'input': '【建议】\n建议结合《条例》...',
        'expect_keep': True
    },
    {
        'name': '测试 5: 多行内容',
        'section_title': '建议',
        'input': '''建议结合《浙江省公共安全技术防范条例》。
加快部署高空抛物探头。
升级监控设备。''',
        'expect_keep': True
    },
    {
        'name': '测试 6: 建设目标章节',
        'section_title': '建设目标',
        'input': '建设目标如下：\n1. 提升社区安全水平\n2. 完善基础设施',
        'expect_keep': True
    },
    {
        'name': '测试 7: 纯标题 "建设目标"',
        'section_title': '建设目标',
        'input': '建设目标',
        'expect_keep': False
    },
]

passed = 0
failed = 0

for i, case in enumerate(test_cases, 1):
    print(f"\n{case['name']}")
    print("-" * 60)
    print(f"输入：{case['input'][:50]}...")
    
    result = clean_ai_content(case['input'], case['section_title'])
    
    print(f"输出：{result[:50] if result else '(空)'}...")
    print(f"输出长度：{len(result)}")
    
    has_content = len(result) > 0
    should_have_content = case['expect_keep'] and len(case['input']) > len(case['section_title'])
    
    if should_have_content and has_content:
        print("✓ 通过（正确保留了正文内容）")
        passed += 1
    elif not should_have_content and not has_content:
        print("✓ 通过（正确过滤了纯标题）")
        passed += 1
    elif should_have_content and not has_content:
        print("✗ 失败（错误地过滤了正文内容）")
        failed += 1
    else:
        print("? 结果异常")
        failed += 1

print("\n" + "="*60)
print(f"测试结果：通过={passed}, 失败={failed}")
print("="*60)

# 额外测试：模拟真实 AI 输出
print("\n" + "="*60)
print("模拟真实 AI 输出测试")
print("="*60)

ai_output = """建议结合《浙江省公共安全技术防范条例》（2021 年修订）及 GB 50348-2018《安全防范工程技术标准》，加快部署高空抛物探头、单元门禁系统及烟感设备，升级监控设备以解决车牌识别率低、电瓶车盗窃等问题，同步开发"平安码"功能提升安防管控效率。依据《浙江省流动人口居住登记条例》（2020 年施行）及 GB/T 28181-2016 标准，构建流动人口、陌生人及暂居人员管控机制，开展社区人员结构分析，优化社区活动策划。参照 DB33/T 1234-2020《智慧社区建设规范》，推进与区平台的系统对接，结合回迁小区的属性进行个性化开发，确保管理适配性。依托邻里中心及商铺资源，建设共享书房与邻里街，完善 15 分钟生活圈配套。依据《浙江省物业管理条例》（20..."""

result = clean_ai_content(ai_output, '建议')
print(f"AI 输出长度：{len(ai_output)}")
print(f"清理后长度：{len(result)}")
if len(result) > 0:
    print(f"清理后前 50 字：{result[:50]}...")
    print("✓ 成功保留正文内容")
else:
    print("✗ 正文内容被错误过滤")

print("\n测试完成\n")
