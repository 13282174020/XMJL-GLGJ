# -*- coding: utf-8 -*-
"""
AI 引擎服务 - 基础 AI 调用功能
调用百炼 API 生成章节内容
"""

import requests
import json
from typing import Dict, Optional


def call_bailian_api(
    prompt: str,
    api_key: str,
    model: str = 'qwen-max',
    max_tokens: int = 2000,
    temperature: float = 0.7
) -> str:
    """调用百炼 API 生成内容
    
    Args:
        prompt: 提示词
        api_key: 百炼 API Key
        model: 模型名称（qwen-max/qwen-plus/qwen-turbo）
        max_tokens: 最大生成 token 数
        temperature: 温度参数（0-1）
    
    Returns:
        AI 生成的文本内容
    """
    url = 'https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation'
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        'model': model,
        'input': {
            'messages': [
                {'role': 'user', 'content': prompt}
            ]
        },
        'parameters': {
            'max_tokens': max_tokens,
            'temperature': temperature
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=120)
        
        if response.status_code == 200:
            result = response.json()
            # 提取 AI 回复内容
            if 'output' in result and 'choices' in result['output']:
                content = result['output']['choices'][0]['message']['content']
                return content.strip()
            elif 'output' in result and 'text' in result['output']:
                return result['output']['text'].strip()
            else:
                return f"[API 返回格式异常] {json.dumps(result, ensure_ascii=False)}"
        else:
            return f"[API 调用失败] 状态码：{response.status_code}, 错误：{response.text}"
    
    except requests.exceptions.Timeout:
        return "[API 调用超时] 请重试"
    except requests.exceptions.RequestException as e:
        return f"[API 调用异常] {str(e)}"


def generate_section_content_with_ai(
    section_title: str,
    requirement_text: str = '',
    template_text: str = '',
    user_instruction: str = '',
    api_key: str = '',
    model: str = 'qwen-max'
) -> str:
    """使用 AI 生成章节内容
    
    Args:
        section_title: 章节标题（如"项目概况"）
        requirement_text: 需求文档内容
        template_text: 模板文档内容
        user_instruction: 用户补充要求
        api_key: 百炼 API Key
        model: 模型名称
    
    Returns:
        AI 生成的章节内容
    """
    # 构建 Prompt
    prompt = f"""你是一位专业的可行性研究报告编写专家。

【任务】请为以下章节撰写内容。

【章节标题】{section_title}

【需求文档内容】
{requirement_text[:2000] if requirement_text else '无相关需求文档'}

【参考模板】
{template_text[:1000] if template_text else '无参考模板'}

【用户补充要求】
{user_instruction if user_instruction else '无特殊要求'}

【输出要求】
1. 内容要专业、准确、逻辑清晰
2. 使用正式的公文语言
3. 不要输出章节标题
4. 字数控制在 200-400 字

【请开始撰写】
"""
    
    # 调用 AI API
    content = call_bailian_api(prompt, api_key, model)
    
    # 清理 AI 生成内容（移除可能的标题行）
    content = clean_ai_content(content, section_title)
    
    return content


def clean_ai_content(content: str, section_title: str) -> str:
    """清理 AI 生成的内容
    
    Args:
        content: AI 生成的原始内容
        section_title: 章节标题
    
    Returns:
        清理后的内容
    """
    if not content:
        return ''
    
    lines = content.split('\n')
    cleaned_lines = []
    
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        
        # 跳过可能是标题的行
        if stripped.startswith(section_title):
            continue
        if stripped.startswith('#'):
            continue
        
        cleaned_lines.append(stripped)
    
    return '\n'.join(cleaned_lines)


# 测试函数
if __name__ == '__main__':
    # 简单测试
    test_api_key = 'sk-cc3bee3fa06c4987b52756db0abb7991'
    result = call_bailian_api('你好，请用一句话介绍你自己。', test_api_key)
    print(f'AI 回复：{result}')
