# -*- coding: utf-8 -*-
"""测试模型配置兼容性"""
import sys
sys.path.insert(0, r'e:\Qwen\xmjl')

from web_system.model_config import get_model_config

print("\n" + "="*60)
print("测试模型配置兼容性")
print("="*60)

# 测试用例
test_cases = [
    'qwen3-14b-instruct',         # 直接匹配
    'ollama-qwen3-14b-instruct',  # ollama 前缀
    'qwen2.5-14b-instruct',       # 直接匹配
    'ollama-qwen2.5-14b-instruct',# ollama 前缀
    'ollama-deepseek-r1-14b',     # ollama 前缀
    'deepseek-r1-14b',            # 无前缀
    'qwen-max',                   # 直接匹配
    'non-existent-model',         # 不存在
]

for model_id in test_cases:
    config = get_model_config(model_id)
    if config:
        print(f"✓ {model_id} => {config.name} ({config.provider})")
    else:
        print(f"✗ {model_id} => 未找到配置")

print("\n" + "="*60)
print("测试完成")
print("="*60)  
