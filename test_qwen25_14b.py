# -*- coding: utf-8 -*-
"""
测试 Qwen2.5-14B-Instruct 和 Qwen3-14B-Instruct 模型
"""

import sys
sys.path.insert(0, 'web_system')

from model_config import get_model_config
from ai_engine import call_ai_api

def test_model(model_id, model_name):
    """测试指定模型"""
    
    print("=" * 70)
    print(f"测试 {model_name} 模型")
    print("=" * 70)
    
    config = get_model_config(model_id)
    
    if config is None:
        print("[ERROR] 未找到模型配置")
        return False
    
    print(f"\n模型配置:")
    print(f"  ID: {config.id}")
    print(f"  名称：{config.name}")
    print(f"  模型：{config.model}")
    
    # 测试 1：简单对话
    print("\n" + "=" * 70)
    print("测试 1：简单对话")
    print("=" * 70)
    
    test_prompt = "你好，请用一句话介绍你自己。"
    print(f"问题：{test_prompt}")
    result = call_ai_api(test_prompt, config)
    print(f"AI 回复：{result[:200] if result else 'empty'}")
    
    if result.startswith("[API"):
        print("\n[WARN] API 调用可能失败")
        return False
    else:
        print("\n[SUCCESS] 测试 1 成功!")
        return True

if __name__ == '__main__':
    # 测试 Qwen2.5-14B
    test_model('qwen2.5-14b-instruct', 'Qwen2.5-14B-Instruct')
    
    print("\n\n")
    
    # 测试 Qwen3-14B
    test_model('qwen3-14b-instruct', 'Ophiuchi-Qwen3-14B-Instruct')
