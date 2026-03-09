# -*- coding: utf-8 -*-
"""
AI 引擎服务 - 基础 AI 调用功能
调用百炼 API 生成章节内容

优化：支持字段分类
- 信息型字段：从需求文档提取（简短）
- 描述型字段：AI 详细生成（200-400 字）

V2.0 更新：集成数据点管理和需求分析
- 数据一致性：注入已确立的数据点
- 需求覆盖度：注入章节应回应的需求点
"""

import requests
import json
import re
from typing import Dict, Optional, Callable

# 导入优化服务
from services.data_point_manager import DataPointManager
from services.requirement_analyzer import RequirementAnalyzer


# 全局实例（用于保持跨章节的数据一致性）
_data_point_manager: Optional[DataPointManager] = None
_requirement_analyzer: Optional[RequirementAnalyzer] = None


def get_data_point_manager() -> DataPointManager:
    """获取数据点管理器实例（单例）"""
    global _data_point_manager
    if _data_point_manager is None:
        _data_point_manager = DataPointManager()
    return _data_point_manager


def get_requirement_analyzer() -> RequirementAnalyzer:
    """获取需求分析器实例（单例）"""
    global _requirement_analyzer
    if _requirement_analyzer is None:
        _requirement_analyzer = RequirementAnalyzer()
    return _requirement_analyzer


def reset_optimization_services():
    """重置优化服务（用于新文档生成任务）"""
    global _data_point_manager, _requirement_analyzer
    _data_point_manager = DataPointManager()
    _requirement_analyzer = RequirementAnalyzer()
    print('[INFO] 优化服务已重置')


# 字段分类配置
INFO_FIELDS = [
    '项目名称', '项目建设单位', '负责人', '联系方式',
    '建设工期', '总投资', '资金来源', '编制单位',
    '项目建设单位与职能', '项目实施机构', '项目实施机构与职责'
]

# 信息提取正则表达式
INFO_PATTERNS = {
    '项目名称': [r'项目名称 [：:]\s*([^\n]+)', r'项目名称为 [：:]\s*([^\n]+)'],
    '项目建设单位': [r'建设单位 [：:]\s*([^\n]+)', r'业主单位 [：:]\s*([^\n]+)'],
    '负责人': [r'负责人 [：:]\s*([^\n]+)', r'联系人 [：:]\s*([^\n]+)'],
    '联系方式': [r'联系方式 [：:]\s*([^\n]+)', r'联系电话 [：:]\s*([^\n]+)', r'电话 [：:]\s*([^\n]+)'],
    '建设工期': [r'建设工期 [：:]\s*([^\n]+)', r'工期 [：:]\s*([^\n]+)', r'([\d]+)[个]?[年月天]'],
    '总投资': [r'总投资 [：:]\s*([^\n]+)', r'投资估算 [：:]\s*([^\n]+)', r'([\d\.]+)\s*万?元'],
    '资金来源': [r'资金来源 [：:]\s*([^\n]+)', r'资金筹措 [：:]\s*([^\n]+)'],
    '编制单位': [r'编制单位 [：:]\s*([^\n]+)', r'可研编制 [：:]\s*([^\n]+)'],
}


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


def extract_info_field(section_title: str, requirement_text: str) -> Optional[str]:
    """从需求文档中提取信息型字段
    
    Args:
        section_title: 章节标题
        requirement_text: 需求文档内容
    
    Returns:
        提取的信息，如果未找到则返回 None
    """
    if section_title not in INFO_FIELDS:
        return None
    
    patterns = INFO_PATTERNS.get(section_title, [])
    
    for pattern in patterns:
        match = re.search(pattern, requirement_text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    
    return None


def generate_section_content_with_ai(
    section_title: str,
    requirement_text: str = '',
    template_text: str = '',
    user_instruction: str = '',
    api_key: str = '',
    model: str = 'qwen-max',
    extract_data_points: bool = True
) -> str:
    """使用 AI 生成章节内容

    Args:
        section_title: 章节标题（如"项目概况"）
        requirement_text: 需求文档内容
        template_text: 模板文档内容
        user_instruction: 用户补充要求
        api_key: 百炼 API Key
        model: 模型名称
        extract_data_points: 是否提取数据点（默认 True）

    Returns:
        AI 生成的章节内容
    """
    # 首次生成时，从需求文档提取初始数据点
    if extract_data_points and requirement_text:
        dp_manager = get_data_point_manager()
        initial_data = dp_manager.extract_from_text(requirement_text, "需求文档")
        if initial_data:
            conflicts = dp_manager.update(initial_data, "需求文档")
            if conflicts:
                print(f'[WARN] 需求文档中发现数据冲突: {conflicts}')
            print(f'[INFO] 从需求文档提取数据点: {list(initial_data.keys())}')

    # 判断是否为信息型字段
    if section_title in INFO_FIELDS:
        # 尝试从需求文档提取
        extracted = extract_info_field(section_title, requirement_text)
        if extracted:
            print(f'[INFO] 提取信息型字段：{section_title} = {extracted}')
            # 更新数据点
            if extract_data_points:
                dp_manager = get_data_point_manager()
                dp_manager.update({section_title: extracted}, section_title)
            return extracted

        # 提取失败，使用 AI 生成简短内容
        prompt = build_info_field_prompt(section_title, requirement_text, template_text)
        max_tokens = 100  # 信息型字段限制字数
    else:
        # 描述型字段，详细生成（带数据注入）
        prompt = build_desc_field_prompt(section_title, requirement_text, template_text, user_instruction)
        max_tokens = 800  # 描述型字段允许更多字数

    # 调用 AI API
    content = call_bailian_api(prompt, api_key, model, max_tokens=max_tokens)

    # 清理 AI 生成内容
    content = clean_ai_content(content, section_title)

    # 从生成内容中提取数据点（增量更新）
    if extract_data_points and content:
        dp_manager = get_data_point_manager()
        new_data = dp_manager.extract_from_text(content, section_title)
        if new_data:
            conflicts = dp_manager.update(new_data, section_title)
            if conflicts:
                print(f'[WARN] 章节 [{section_title}] 数据冲突:')
                for c in conflicts:
                    print(f'  - {c}')
            print(f'[INFO] 从 [{section_title}] 提取新数据点: {list(new_data.keys())}')

    return content


def extract_requirements_from_text(requirement_text: str, 
                                    ai_call_func: Optional[Callable] = None) -> Dict:
    """从需求文档提取需求点
    
    Args:
        requirement_text: 需求文档内容
        ai_call_func: AI 调用函数（可选）
        
    Returns:
        需求点字典 {'pain_points': [...], 'requirements': [...], 'goals': [...]}
    """
    req_analyzer = get_requirement_analyzer()
    result = req_analyzer.extract(requirement_text, ai_call_func)
    print(f'[INFO] 提取需求点: {len(result["pain_points"])} 痛点, '
          f'{len(result["requirements"])} 需求, {len(result["goals"])} 目标')
    return result


def get_optimization_summary() -> Dict:
    """获取优化摘要（数据点和需求点）
    
    Returns:
        优化摘要字典
    """
    dp_manager = get_data_point_manager()
    req_analyzer = get_requirement_analyzer()
    
    return {
        'data_points': dp_manager.get_extraction_summary(),
        'requirements': req_analyzer.get_summary()
    }


def build_info_field_prompt(section_title: str, requirement_text: str, template_text: str) -> str:
    """构建信息型字段的 Prompt（简短提取）"""
    return f"""你是一位专业的文档信息提取专家。

【任务】从以下文本中提取【{section_title}】

【需求文档】
{requirement_text[:1500] if requirement_text else '无'}

【要求】
1. 只输出{section_title}，不要解释
2. 不超过 50 字
3. 如果没有相关信息，输出"根据项目实际情况确定"

【{section_title}】
"""


def build_desc_field_prompt(section_title: str, requirement_text: str, template_text: str, user_instruction: str) -> str:
    """构建描述型字段的 Prompt（详细论述，带数据注入）"""
    # 调试输出
    print(f'[DEBUG] 生成描述型字段：{section_title}')
    print(f'[DEBUG] 需求文档长度：{len(requirement_text) if requirement_text else 0}')
    print(f'[DEBUG] 模板参考长度：{len(template_text) if template_text else 0}')

    # 获取数据点管理器和需求分析器
    dp_manager = get_data_point_manager()
    req_analyzer = get_requirement_analyzer()

    # 注入已确立的数据点
    data_points_text = dp_manager.get_formatted_prompt_text()

    # 注入本章应回应的需求点
    requirements_text = req_analyzer.get_requirements_text(section_title)

    return f"""你是一位专业的可行性研究报告编写专家。

【任务】请为以下章节撰写内容。

【章节标题】{section_title}

{data_points_text}

【需求文档内容】
{requirement_text[:2000] if requirement_text else '无相关需求文档'}

{requirements_text}

【参考模板】
{template_text[:1000] if template_text else '无参考模板'}

【用户补充要求】
{user_instruction if user_instruction else '无特殊要求'}

【输出要求】
1. 内容要专业、准确、逻辑清晰
2. 使用正式的公文语言
3. 引用数据时必须与【已确立的关键数据】保持一致
4. 回应本章应覆盖的需求点
5. 不要输出章节标题
6. 字数控制在 200-400 字

【请开始撰写】
"""


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
