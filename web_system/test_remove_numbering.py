# -*- coding: utf-8 -*-
"""测试删除编号前缀功能"""
import sys
sys.path.insert(0, '.')

from template_preprocessor import remove_numbering_prefix

# 测试用例
test_cases = [
    # (输入，期望编号，期望纯文本)
    ('2.3 项目建设的依据', '2.3', '项目建设的依据'),
    ('2.3.1 相关政策文件', '2.3.1', '相关政策文件'),
    ('1.1.1.1 详细政策', '1.1.1.1', '详细政策'),
    ('4. 管理后台', '4.', '管理后台'),
    ('第一章 项目概况', '第一章', '项目概况'),
    ('一、建设背景', '一、', '建设背景'),
    ('（一）软件系统', '（一）', '软件系统'),
    ('(1) 测试内容', '(1)', '测试内容'),
    ('① 第一项', '①', '第一项'),
    ('4.0 版本说明', '', '4.0 版本说明'),  # 版本号不应删除
    ('2024 年 01 月', '', '2024 年 01 月'),  # 日期不应删除
    ('正常文本', '', '正常文本'),
]

print('=' * 80)
print('测试 remove_numbering_prefix 函数')
print('=' * 80)

passed = 0
failed = 0

for text, expected_num, expected_text in test_cases:
    numbering, pure_text = remove_numbering_prefix(text)
    
    if numbering == expected_num and pure_text == expected_text:
        status = '✓'
        passed += 1
    else:
        status = '✗'
        failed += 1
    
    print(f'{status} 输入："{text}"')
    print(f'   期望：编号="{expected_num}", 文本="{expected_text}"')
    print(f'   实际：编号="{numbering}", 文本="{pure_text}"')
    print()

print('=' * 80)
print(f'测试结果：{passed} 通过，{failed} 失败')
print('=' * 80)
