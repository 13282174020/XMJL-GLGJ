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
from typing import Dict, Optional, Callable, Any

# 导入优化服务
from services.data_point_manager import DataPointManager
from services.requirement_analyzer import RequirementAnalyzer
from services.content_optimizer import ContentOptimizer
from model_config import get_model_config, ModelConfig


# 全局实例（用于保持跨章节的数据一致性）
_data_point_manager: Optional[DataPointManager] = None
_requirement_analyzer: Optional[RequirementAnalyzer] = None
_content_optimizer: Optional[ContentOptimizer] = None


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


def get_content_optimizer() -> ContentOptimizer:
    """获取内容优化器实例（单例）"""
    global _content_optimizer
    if _content_optimizer is None:
        _content_optimizer = ContentOptimizer()
    return _content_optimizer


def reset_optimization_services():
    """重置优化服务（用于新文档生成任务）"""
    global _data_point_manager, _requirement_analyzer, _content_optimizer
    _data_point_manager = DataPointManager()
    _requirement_analyzer = RequirementAnalyzer()
    _content_optimizer = ContentOptimizer()
    print('[INFO] 优化服务已重置')


# 字段分类配置
INFO_FIELDS = [
    '项目名称', '项目建设单位', '负责人', '联系方式',
    '建设工期', '总投资', '资金来源', '编制单位',
    '项目建设单位与职能', '项目实施机构', '项目实施机构与职责'
]

# 信息提取正则表达式
INFO_PATTERNS = {
    '项目名称': [r'项目名称\s*[:：]\s*(.+)', r'项目名称为\s*[:：]\s*(.+)'],
    '项目建设单位': [r'建设单位\s*[:：]\s*(.+)', r'业主单位\s*[:：]\s*(.+)', r'项目建设单位\s*[:：]\s*(.+)'],
    '负责人': [r'负责人\s*[:：]\s*(.+)', r'联系人\s*[:：]\s*(.+)'],
    '联系方式': [r'联系方式\s*[:：]\s*(.+)', r'联系电话\s*[:：]\s*(.+)', r'电话\s*[:：]\s*(.+)'],
    '建设工期': [r'建设工期\s*[:：]\s*(.+)', r'工期\s*[:：]\s*(.+)', r'([\d]+)[个]?[年月天]'],
    '总投资': [r'总投资\s*[:：]\s*(.+)', r'投资估算\s*[:：]\s*(.+)', r'([\d\.]+)\s*万?元'],
    '资金来源': [r'资金来源\s*[:：]\s*(.+)', r'资金筹措\s*[:：]\s*(.+)'],
    '编制单位': [r'编制单位\s*[:：]\s*(.+)', r'可研编制\s*[:：]\s*(.+)'],
}


def _extract_value_from_path(data: Dict, path: str) -> Any:
    """根据路径从嵌套字典中提取值
    
    Args:
        data: 字典数据
        path: 路径，如 "choices.0.message.content"
        
    Returns:
        提取的值
    """
    keys = path.split('.')
    current = data
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        elif isinstance(current, list) and key.isdigit():
            idx = int(key)
            if idx < len(current):
                current = current[idx]
            else:
                return None
        else:
            return None
    return current


def call_ai_api(
    prompt: str,
    model_config: ModelConfig
) -> str:
    """通用 AI API 调用函数
    
    根据模型配置调用不同的 AI API

    Args:
        prompt: 提示词
        model_config: 模型配置

    Returns:
        AI 生成的文本内容
    """
    if not model_config.api_key:
        return "[API 错误] API Key 未配置"
    
    # 构建请求头
    headers = {
        'Content-Type': 'application/json'
    }
    headers.update(model_config.headers)
    
    # 根据请求格式构建 payload
    if model_config.request_format == "dashscope":
        # 阿里云百炼格式
        headers['Authorization'] = f'Bearer {model_config.api_key}'
        payload = {
            'model': model_config.model,
            'input': {
                'messages': [
                    {'role': 'user', 'content': prompt}
                ]
            },
            'parameters': {
                'max_tokens': model_config.max_tokens,
                'temperature': model_config.temperature
            }
        }
    elif model_config.request_format == "openai":
        # OpenAI 兼容格式
        headers['Authorization'] = f'Bearer {model_config.api_key}'
        payload = {
            'model': model_config.model,
            'messages': [
                {'role': 'user', 'content': prompt}
            ],
            'max_tokens': model_config.max_tokens,
            'temperature': model_config.temperature
        }
    else:
        # 自定义格式（待扩展）
        return f"[API 错误] 不支持的请求格式: {model_config.request_format}"

    try:
        response = requests.post(
            model_config.base_url,
            headers=headers,
            json=payload,
            timeout=model_config.timeout
        )

        if response.status_code == 200:
            result = response.json()
            # 根据配置的路径提取内容
            content = _extract_value_from_path(result, model_config.response_path)
            if content:
                return content.strip()
            else:
                return f"[API 返回格式异常] 无法从路径 {model_config.response_path} 提取内容: {json.dumps(result, ensure_ascii=False)[:200]}"
        else:
            error_msg = response.text
            try:
                error_json = response.json()
                if 'error' in error_json:
                    error_msg = error_json['error'].get('message', error_msg)
                elif 'message' in error_json:
                    error_msg = error_json['message']
            except:
                pass
            return f"[API 调用失败] 状态码：{response.status_code}, 错误：{error_msg}"

    except requests.exceptions.Timeout:
        return "[API 调用超时] 请重试"
    except requests.exceptions.RequestException as e:
        return f"[API 调用异常] {str(e)}"


def call_bailian_api(
    prompt: str,
    api_key: str,
    model: str = 'qwen-max',
    max_tokens: int = 2000,
    temperature: float = 0.7
) -> str:
    """调用百炼 API 生成内容（兼容旧接口）

    Args:
        prompt: 提示词
        api_key: 百炼 API Key
        model: 模型名称（qwen-max/qwen-plus/qwen-turbo）
        max_tokens: 最大生成 token 数
        temperature: 温度参数（0-1）

    Returns:
        AI 生成的文本内容
    """
    # 尝试从配置中获取模型配置
    config = get_model_config(model)
    if config and config.api_key:
        # 使用配置中的 API Key
        return call_ai_api(prompt, config)
    
    # 使用传入的 API Key 创建临时配置
    from model_config import ModelProvider
    temp_config = ModelConfig(
        id=model,
        name=model,
        provider=ModelProvider.DASHSCOPE.value,
        model=model,
        api_key=api_key,
        base_url="https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
        max_tokens=max_tokens,
        temperature=temperature,
        request_format="dashscope",
        response_path="output.choices.0.message.content"
    )
    return call_ai_api(prompt, temp_config)


def extract_info_field(section_title: str, requirement_text: str, 
                       ai_call_func: Optional[Callable[[str], str]] = None,
                       model_config: Optional[ModelConfig] = None) -> Optional[str]:
    """从需求文档中提取信息型字段

    采用三级提取策略：
    1. 正则匹配（快速、无成本）
    2. AI 语义提取（精准、理解上下文）

    支持匹配包含编号的章节标题，如 "1.1 项目名称" 也能匹配 "项目名称"

    Args:
        section_title: 章节标题
        requirement_text: 需求文档内容
        ai_call_func: 可选的 AI 调用函数
        model_config: 模型配置（用于 AI 提取）

    Returns:
        提取的信息，如果未找到则返回 None
    """
    # 确定要匹配的字段名
    target_field = None
    if section_title in INFO_FIELDS:
        target_field = section_title
    else:
        # 尝试模糊匹配（章节标题可能包含编号，如 "1.1 项目名称"）
        for field_name in INFO_FIELDS:
            if field_name in section_title:
                target_field = field_name
                break
    
    if target_field:
        # 第 1 级：尝试正则匹配（快速、无成本）
        patterns = INFO_PATTERNS.get(target_field, [])
        for pattern in patterns:
            match = re.search(pattern, requirement_text, re.IGNORECASE)
            if match:
                result = match.group(1).strip()
                if target_field != section_title:
                    print(f'[INFO] 模糊匹配提取：{section_title} -> {target_field} = {result}')
                return result
        
        # 第 2 级：如果提供了 AI 函数，使用 AI 语义提取
        if ai_call_func and model_config:
            try:
                print(f'[INFO] 正则匹配失败，尝试 AI 提取：{section_title}')
                ai_result = _extract_info_field_with_ai(
                    target_field, requirement_text, ai_call_func, model_config
                )
                if ai_result:
                    print(f'[INFO] AI 提取成功：{section_title} = {ai_result[:50]}...')
                    return ai_result
            except Exception as e:
                print(f'[WARN] AI 提取失败：{e}，返回 None')
    
    return None


def _extract_info_field_with_ai(target_field: str, requirement_text: str,
                                 ai_call_func: Callable[[str], str],
                                 model_config: ModelConfig) -> Optional[str]:
    """使用 AI 提取信息型字段

    Args:
        target_field: 目标字段名（如"项目名称"）
        requirement_text: 需求文档内容
        ai_call_func: AI 调用函数
        model_config: 模型配置

    Returns:
        提取的值，如果未找到则返回 None
    """
    # 构建 AI 提取提示
    prompt = f"""请从以下需求文档中提取【{target_field}】的具体值。

【需求文档内容】
{requirement_text[:3000]}

【提取要求】
1. 只提取"{target_field}"的具体值，不要提取其他信息
2. 如果文档中没有明确提及"{target_field}"，请输出 null
3. 直接输出值即可，不要包含"{target_field}"字样
4. 如果同一信息有多个表述，选择最完整、最正式的一个

【输出格式】
直接输出"{target_field}"的值，如果未找到则输出 null

示例：
- 如果提取到"项目名称：杭海路未来社区建设项目"，输出：杭海路未来社区建设项目
- 如果未找到相关信息，输出：null
"""
    
    # 临时调整模型配置以获取简短回答
    original_max_tokens = model_config.max_tokens
    model_config.max_tokens = 50  # 限制输出长度
    
    try:
        result = ai_call_func(prompt, model_config)

        # 清理结果
        if result:
            result = result.strip()
            # 移除可能的引号
            if result.startswith('"') and result.endswith('"'):
                result = result[1:-1]
            # 检查是否为 null
            if result.lower() in ['null', 'none', '无', '未找到', '']:
                return None
            return result
        return None
    finally:
        # 恢复原始配置
        model_config.max_tokens = original_max_tokens


def generate_section_content_with_ai(
    section_title: str,
    requirement_text: str = '',
    template_text: str = '',
    user_instruction: str = '',
    api_key: str = '',
    model: str = 'qwen-max',
    extract_data_points: bool = True,
    fallback_to_template: bool = False,
    model_config: Optional[ModelConfig] = None
) -> str:
    """使用 AI 生成章节内容

    Args:
        section_title: 章节标题（如"项目概况"）
        requirement_text: 需求文档内容
        template_text: 模板文档内容
        user_instruction: 用户补充要求
        api_key: 百炼 API Key（已弃用，使用 model_config）
        model: 模型名称（已弃用，使用 model_config）
        extract_data_points: 是否提取数据点（默认 True）
        fallback_to_template: AI 失败时是否降级使用模板（默认 False，返回错误信息）
        model_config: 模型配置（推荐方式）

    Returns:
        AI 生成的章节内容，或错误信息（如果 fallback_to_template=False）
    """
    # 调试信息
    print(f'\n[DEBUG] ====== 生成章节: {section_title} ======')
    print(f'[DEBUG] requirement_text 长度: {len(requirement_text) if requirement_text else 0}')
    print(f'[DEBUG] template_text 长度: {len(template_text) if template_text else 0}')
    print(f'[DEBUG] user_instruction: {user_instruction[:50] if user_instruction else "无"}...')
    
    # 获取模型配置
    if model_config is None:
        # 尝试从配置管理器获取
        model_config = get_model_config(model)
        if model_config is None:
            # 创建临时配置（兼容旧接口）
            from model_config import ModelProvider
            model_config = ModelConfig(
                id=model,
                name=model,
                provider=ModelProvider.DASHSCOPE.value,
                model=model,
                api_key=api_key,
                base_url="https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
                max_tokens=2000,
                temperature=0.7,
                request_format="dashscope",
                response_path="output.choices.0.message.content"
            )
    
    print(f'[DEBUG] 使用模型: {model_config.name} ({model_config.id})')
    print(f'[DEBUG] 提供商: {model_config.provider}')
    print(f'[DEBUG] API Key 是否为空: {not model_config.api_key}')
    
    # 首次生成时，从需求文档提取初始数据点
    if extract_data_points and requirement_text:
        dp_manager = get_data_point_manager()
        initial_data = dp_manager.extract_from_text(requirement_text, "需求文档")
        if initial_data:
            conflicts = dp_manager.update(initial_data, "需求文档")
            if conflicts:
                print(f'[WARN] 需求文档中发现数据冲突: {conflicts}')
            print(f'[INFO] 从需求文档提取数据点: {list(initial_data.keys())}')
        else:
            print(f'[WARN] 未能从需求文档提取数据点')

    # 判断是否为信息型字段
    is_info_field = section_title in INFO_FIELDS
    # 检查是否包含信息型字段关键词
    contains_info_keyword = any(field in section_title for field in INFO_FIELDS)
    
    print(f'[DEBUG] 字段类型判断: section_title={section_title}')
    print(f'[DEBUG]   - 是否在INFO_FIELDS: {is_info_field}')
    print(f'[DEBUG]   - 是否包含信息型关键词: {contains_info_keyword}')
    
    if is_info_field or contains_info_keyword:
        # 尝试从需求文档提取（使用正则 + AI 两级提取）
        extracted = extract_info_field(
            section_title, 
            requirement_text,
            ai_call_func=call_ai_api,  # 传入 AI 调用函数
            model_config=model_config
        )
        if extracted:
            print(f'[INFO] 提取信息型字段：{section_title} = {extracted}')
            # 更新数据点
            if extract_data_points:
                dp_manager = get_data_point_manager()
                dp_manager.update({section_title: extracted}, section_title)
            return extracted

        # 提取失败，使用 AI 生成简短内容
        print(f'[INFO] 信息型字段提取失败，使用AI生成: {section_title}')
        prompt = build_info_field_prompt(section_title, requirement_text, template_text)
        max_tokens = 100  # 信息型字段限制字数
    else:
        # 描述型字段，详细生成（带数据注入）
        print(f'[INFO] 描述型字段，使用AI生成: {section_title}')
        prompt = build_desc_field_prompt(section_title, requirement_text, template_text, user_instruction)
        max_tokens = 800  # 描述型字段允许更多字数

    # 调用 AI API
    print(f'[DEBUG] 调用AI API: max_tokens={max_tokens}')
    # 更新模型配置的 max_tokens
    model_config.max_tokens = max_tokens
    content = call_ai_api(prompt, model_config)
    print(f'[DEBUG] AI返回内容长度: {len(content) if content else 0}')
    print(f'[DEBUG] AI返回内容前100字: {content[:100] if content else "空"}...')

    # 检查 AI 调用是否失败
    if content.startswith('[') and ('API' in content or 'Error' in content or 'error' in content):
        error_msg = f"[AI 生成失败] 章节 '{section_title}': {content}"
        print(f'[ERROR] {error_msg}')
        
        if fallback_to_template:
            # 降级使用模板
            print(f'[WARNING] 降级使用模板: {section_title}')
            from app import get_chapter_content_template
            content = get_chapter_content_template(section_title)
        else:
            # 返回错误信息，不降级
            print(f'[DEBUG] ====== 完成章节: {section_title} (失败) ======\n')
            return error_msg

    # 清理 AI 生成内容
    content = clean_ai_content(content, section_title)
    print(f'[DEBUG] 清理后内容长度: {len(content) if content else 0}')

    # 内容去重检测（新增功能）
    if content:
        optimizer = get_content_optimizer()
        duplicate_result = optimizer.check_duplicate(content, threshold=0.6)
        if duplicate_result["is_duplicate"]:
            print(f'[WARN] 检测到重复内容：与 {duplicate_result["duplicate_sections"][0]["section_title"]} 相似度 {duplicate_result["duplicate_sections"][0]["similarity"]:.1%}')
            # 记录但不阻止生成，由后续审校处理
        # 添加到历史记录
        optimizer.add_generated_content(section_title, content)
    

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

    print(f'[DEBUG] ====== 完成章节: {section_title} ======\n')
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
    """构建信息型字段的 Prompt（智能提取或生成）"""
    return f"""你是一位专业的文档信息提取和生成专家。

【任务】为【{section_title}】提供内容

【需求文档】
{requirement_text[:1500] if requirement_text else '无'}

【要求】
1. 优先从需求文档中提取准确的{section_title}
2. 如果文档中没有明确的{section_title}，请根据上下文智能生成一个合理的、专业的{section_title}
3. 只输出{section_title}的内容，不要解释
4. 不超过 50 字
5. 内容要专业、符合可行性研究报告规范

【{section_title}】
"""


def extract_template_section(section_title: str, template_text: str) -> str:
    """从模板文档中提取指定章节的内容
    
    Args:
        section_title: 章节标题
        template_text: 模板文档全文
        
    Returns:
        该章节的模板内容
    """
    if not template_text or not section_title:
        return ""
    
    # 尝试找到章节标题位置
    # 支持多种格式："1.1 项目名称"、"项目名称"、"1.1项目名称"等
    patterns = [
        rf'{re.escape(section_title)}[\s\n]*',
        rf'{re.escape(section_title.split()[-1] if " " in section_title else section_title)}[\s\n]*',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, template_text, re.IGNORECASE)
        if match:
            start_pos = match.end()
            # 查找下一个章节标题位置（或文档结束）
            # 假设下一个章节以数字或"第"开头
            next_section_match = re.search(r'\n\s*(?:\d+\.|第[一二三四五六七八九十]+章|【)', template_text[start_pos:])
            if next_section_match:
                end_pos = start_pos + next_section_match.start()
                section_content = template_text[start_pos:end_pos].strip()
            else:
                section_content = template_text[start_pos:].strip()
            
            # 限制长度
            if len(section_content) > 1500:
                section_content = section_content[:1500] + "..."
            
            return section_content
    
    # 如果没找到特定章节，返回文档开头部分作为通用参考
    return template_text[:800] if template_text else ""


def build_desc_field_prompt(section_title: str, requirement_text: str, template_text: str, user_instruction: str) -> str:
    """构建描述型字段的 Prompt（详细论述，带数据注入、Few-shot 示例和类型识别）"""
    # 调试输出
    print(f'[DEBUG] 生成描述型字段：{section_title}')
    print(f'[DEBUG] 需求文档长度：{len(requirement_text) if requirement_text else 0}')
    print(f'[DEBUG] 模板参考长度：{len(template_text) if template_text else 0}')

    # 获取数据点管理器和需求分析器
    dp_manager = get_data_point_manager()
    req_analyzer = get_requirement_analyzer()
    optimizer = get_content_optimizer()

    # 注入已确立的数据点
    data_points_text = dp_manager.get_formatted_prompt_text()

    # 注入本章应回应的需求点
    requirements_text = req_analyzer.get_requirements_text(section_title)

    # 提取该章节对应的模板内容
    template_section = extract_template_section(section_title, template_text)
    print(f'[DEBUG] 提取模板章节内容长度：{len(template_section)}')

    # 识别章节类型
    type_info = optimizer.identify_section_type(section_title)
    print(f'[DEBUG] 章节类型识别：{type_info["type"]}型 ({type_info["subtype"]})')

    # 获取 Few-shot 示例
    few_shot_prompt = optimizer.get_few_shot_prompt(section_title)
    if few_shot_prompt:
        print(f'[DEBUG] 已加载 Few-shot 示例')

    # 根据章节类型添加特定的格式指导
    format_guidance = get_format_guidance(section_title, template_section)

    # 构建类型指导
    type_guidance = ''
    if type_info['format_strategy']:
        type_guidance = f"\n【格式策略】{type_info['format_strategy']}"

    return f"""你是一位专业的可行性研究报告编写专家。

【任务】请为【{section_title}】这一章节撰写内容。

【重要提示】
- 只生成【{section_title}】这一章节的内容
- **严禁**生成其他章节的内容（如建设目标、建设规模、项目效益等）
- **严禁**在内容中重复或罗列其他章节的标题
- 如果需求文档包含多个主题，只提取与【{section_title}】相关的内容

【章节标题】{section_title}

{data_points_text}

【需求文档内容】
{requirement_text[:2000] if requirement_text else '无相关需求文档'}

{requirements_text}

【参考模板（本章节）】
{template_section if template_section else '无参考模板'}

【用户补充要求】
{user_instruction if user_instruction else '无特殊要求'}
{type_guidance}
{few_shot_prompt}
【输出要求】
1. **只生成【{section_title}】的内容**，不要涉及其他章节
2. 内容要专业、准确、逻辑清晰，使用正式的公文语言
3. **重要**：引用数据时必须与【已确立的关键数据】保持完全一致
4. **重要**：必须回应【本章应回应的需求点】中的每一个要点
5. **格式要求**：严格参考【参考模板】的格式、结构和风格
   - 如果模板是列表形式（如"1. XXX 2. XXX"），请生成类似的列表
   - 如果模板包含标准编号（如"GB/T、DB33/T"），请包含相应的标准编号
   - 保持与模板相同的段落结构和层次
{format_guidance}
6. 结合需求文档中的具体场景和问题，不要泛泛而谈
7. **不要输出章节标题**（如"{section_title}"）
8. **不要生成总结性段落**（如"通过实施本项目..."）
9. 字数控制在 200-400 字（除非模板格式要求更多内容）

【请开始撰写】
"""


def get_format_guidance(section_title: str, template_section: str) -> str:
    """根据章节类型获取特定的格式指导"""
    guidance = []
    
    # 检查章节标题关键词
    title_lower = section_title.lower()
    
    # 政策法规/技术规范类章节
    if any(keyword in title_lower for keyword in ['政策', '法规', '规范', '标准', '依据']):
        guidance.append("   - **本章节特殊要求**：请列出相关的法律法规、政策文件或技术标准")
        guidance.append("   - 使用列表形式，每条包含标准编号（如GB/T、DB33/T等）和标准名称")
        guidance.append("   - 参考模板的列举方式，保持格式一致")
    
    # 如果模板内容包含标准编号格式，明确要求保持
    if template_section:
        # 检查是否包含标准编号模式
        if re.search(r'[A-Z]+/T?\s*\d+[-–]\d{4}', template_section):
            guidance.append("   - **检测到标准编号格式**：请确保生成的内容包含相应的标准编号（如GB/T、DB、ISO等）")
        # 检查是否是列表格式
        if re.search(r'^\s*\d+\.', template_section, re.MULTILINE):
            guidance.append("   - **检测到列表格式**：请使用类似的数字列表格式（1. 2. 3.）")
    
    return '\n'.join(guidance) if guidance else ''


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

    # 常见章节标题模式（用于检测混入的其他章节）
    other_section_patterns = [
        r'^\s*\d+[\.\s]+建设目标',
        r'^\s*\d+[\.\s]+建设规模',
        r'^\s*\d+[\.\s]+建设内容',
        r'^\s*\d+[\.\s]+建设周期',
        r'^\s*\d+[\.\s]+投资估算',
        r'^\s*\d+[\.\s]+资金筹措',
        r'^\s*\d+[\.\s]+项目效益',
        r'^\s*\d+[\.\s]+效益分析',
        r'^\s*\d+[\.\s]+风险分析',
        r'^\s*\d+[\.\s]+结论',
        r'^\s*\d+[\.\s]+建议',
        r'^\s*\d+[\.\s]+项目概况',
        r'^\s*\d+[\.\s]+项目背景',
        r'^\s*\d+[\.\s]+需求分析',
        r'^\s*\d+[\.\s]+技术方案',
        r'^\s*\d+[\.\s]+总体框架',
        r'^\s*第[一二三四五六七八九十]+章',
        r'^\s*第\s*\d+\s*章',
        r'^\s*\d+\.\d+\s+',  # 如 "1.1 项目名称"
        r'^\s*【[^】]+】',     # 如 "【建设目标】"
    ]
    
    lines = content.split('\n')
    cleaned_lines = []
    found_other_section = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # 跳过当前章节标题行
        if stripped.startswith(section_title):
            continue
        if stripped.startswith('#'):
            continue
        
        # 检测是否出现其他章节标题
        for pattern in other_section_patterns:
            if re.search(pattern, stripped, re.IGNORECASE):
                # 如果检测到其他章节标题，截断后续内容
                print(f'[WARN] 检测到混入的其他章节标题，截断: {stripped[:50]}...')
                found_other_section = True
                break
        
        if found_other_section:
            break
        
        # 检测总结性段落的开头
        if re.search(r'^(通过实施本项目|综上所述|总之|本项目旨在|本次建设)', stripped):
            print(f'[WARN] 检测到总结性段落，截断: {stripped[:50]}...')
            break
        
        # 清理 Markdown 格式符号
        # 移除 ** 粗体符号
        stripped = re.sub(r'\*\*(.+?)\*\*', r'\1', stripped)
        # 移除 * 斜体符号
        stripped = re.sub(r'\*(.+?)\*', r'\1', stripped)
        # 移除 ` 代码符号
        stripped = re.sub(r'`(.+?)`', r'\1', stripped)
        # 移除 # 标题符号
        stripped = re.sub(r'^#+\s*', '', stripped)
        # 移除 - 列表符号（但保留内容）
        stripped = re.sub(r'^[-•●*]\s+', '', stripped)
        
        cleaned_lines.append(stripped)

    return '\n'.join(cleaned_lines)


# 测试函数
if __name__ == '__main__':
    # 简单测试
    test_api_key = 'sk-cc3bee3fa06c4987b52756db0abb7991'
    result = call_bailian_api('你好，请用一句话介绍你自己。', test_api_key)
    print(f'AI 回复：{result}')

