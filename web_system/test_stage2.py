#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试第二阶段功能"""

from ai_engine import extract_info_field, generate_section_content_with_ai

# 测试信息提取
test_text = '''
项目名称：智慧社区管理平台建设项目
建设单位：XX 科技有限公司
负责人：张三
联系电话：010-12345678
建设工期：12 个月
总投资：500 万元
'''

print('测试信息提取:')
for field in ['项目名称', '建设单位', '负责人', '总投资']:
    result = extract_info_field(field, test_text)
    print(f'  {field}: {result}')

print()
print('测试 AI 生成:')
api_key = 'sk-cc3bee3fa06c4987b52756db0abb7991'

# 信息型字段
result = generate_section_content_with_ai('项目名称', test_text, '', '', api_key)
print(f'项目名称（信息型）: {result}')

# 描述型字段
result = generate_section_content_with_ai('项目概况', test_text, '', '', api_key)
print(f'项目概况（描述型）: {result[:100]}...')

print()
print('测试完成')
