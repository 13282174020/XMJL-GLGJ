# -*- coding: utf-8 -*-
"""
AI 章节内容生成引擎

功能：
1. 构建描述型字段 Prompt（带数据注入、Few-shot、需求映射）
2. 构建信息型字段 Prompt（简短提取）
3. 调用 AI API 生成内容
4. 清理输出（去除思考过程、Markdown 格式）
5. 项目类型和业务场景识别

依赖：
- requests（用于调用 API）
- services.content_optimizer
- services.requirement_analyzer
- services.data_point_manager
"""

import re
import json
from typing import Dict, List, Optional, Any, Callable
from .services.content_optimizer import ContentOptimizer
from .services.requirement_analyzer import RequirementAnalyzer
from .services.data_point_manager import DataPointManager
from .template_scanner import extract_section_from_template


# =============================================================================
# 项目类型识别
# =============================================================================

def extract_project_type(requirement_text: str) -> str:
    """从需求文档中提取项目类型

    Args:
        requirement_text: 需求文档内容

    Returns:
        项目类型字符串，如"未来社区"、"智慧园区"等
    """
    if not requirement_text:
        return ""

    project_types = {
        '未来社区': ['未来社区', '未来小区'],
        '智慧社区': ['智慧社区', '智慧小区', '智慧住区'],
        '智慧园区': ['智慧园区', '产业园区', '科技园区', '工业园'],
        '智慧校园': ['智慧校园', '数字校园', '智慧学校', '数字化校园'],
        '智慧医院': ['智慧医院', '数字医院', '智慧医疗', '医院信息化'],
        '智慧政务': ['智慧政务', '数字政府', '政务信息化', '电子政务'],
        '智慧乡村': ['智慧乡村', '数字乡村', '乡村治理'],
        '智慧景区': ['智慧景区', '智慧旅游', '景区管理'],
    }

    type_scores = {}
    for project_type, keywords in project_types.items():
        score = sum(1 for keyword in keywords if keyword in requirement_text)
        if score > 0:
            type_scores[project_type] = score

    if type_scores:
        return max(type_scores, key=type_scores.get)

    return ""


def extract_business_scenes(requirement_text: str) -> List[str]:
    """从需求文档中提取业务场景

    Args:
        requirement_text: 需求文档内容

    Returns:
        业务场景列表
    """
    if not requirement_text:
        return []

    scenes = []

    scene_keywords = {
        '智慧安防': ['智慧安防', '安防监控', '高空抛物', '门禁系统', '车辆识别', '平安码'],
        '人员管理': ['人员管理', '流动人口', '人口分析', '访客管理', '实名制'],
        '邻里商业': ['邻里街', '商业配套', '15 分钟生活圈', '商铺管理'],
        '共享空间': ['共享空间', '共享书房', '活动室', '公共空间', '文化空间'],
        '未来健康': ['未来健康', '健康管理', '健康咨询', '医疗服务'],
        '未来低碳': ['未来低碳', '低碳社区', '节能减排', '绿色社区', '垃圾分类'],
        '物业管理': ['物业管理', '物业服务', '物业费', '水电上报'],
        '停车管理': ['停车管理', '停车位', '智能停车', '车辆管理'],
        '环境监测': ['环境监测', '空气质量', '噪音监测'],
        '能源管理': ['能源管理', '能耗监测', '智能电表', '节能管理'],
        '社区治理': ['社区治理', '网格化管理', '基层治理', '民主协商'],
        '志愿服务': ['志愿服务', '志愿者', '公益活动', '社区活动'],
        '智慧养老': ['智慧养老', '养老服务', '居家养老', '老年服务'],
        '智慧教育': ['智慧教育', '社区教育', '培训服务'],
        '智慧物流': ['智慧物流', '快递柜', '物流配送', '最后 100 米'],
    }

    for scene_name, keywords in scene_keywords.items():
        for keyword in keywords:
            if keyword in requirement_text:
                if scene_name not in scenes:
                    scenes.append(scene_name)
                break

    return scenes


# =============================================================================
# Prompt 构建函数
# =============================================================================

# 信息型字段列表（简短提取，不需要详细论述）
INFO_FIELDS = [
    '项目名称', '项目建设单位', '负责人', '联系方式',
    '建设工期', '总投资', '资金来源', '编制单位',
    '项目建设单位与职能', '项目实施机构', '项目实施机构与职责'
]


def build_info_field_prompt(section_title: str, requirement_text: str,
                            template_text: str = '') -> str:
    """构建信息型字段的 Prompt（智能提取或生成）

    用于简短的信息字段，如项目名称、建设单位等。

    Args:
        section_title: 章节标题
        requirement_text: 需求文档内容
        template_text: 模板文档内容

    Returns:
        Prompt 字符串
    """
    return f"""你是一位专业的文档信息提取和生成专家。

【任务】为【{section_title}】提供内容

【需求文档】
{requirement_text[:1500] if requirement_text else '无'}

【要求】
1. 优先从需求文档中提取准确的{section_title}
2. 如果文档中没有明确的{section_title}，请根据上下文智能生成一个合理的、专业的{section_title}
3. **只输出{section_title}的内容，不要解释，不要输出分析过程、思考过程**
4. **直接输出结果，不要使用任何 Markdown 格式（如 **粗体**、## 标题等）**
5. 不超过 50 字
6. 内容要专业、符合可行性研究报告规范

【{section_title}】
"""


def build_desc_field_prompt(section_title: str, requirement_text: str,
                            template_text: str = '', user_instruction: str = '',
                            dp_manager: DataPointManager = None,
                            req_analyzer: RequirementAnalyzer = None,
                            optimizer: ContentOptimizer = None) -> str:
    """构建描述型字段的 Prompt（详细论述）

    这是生成可行性研究报告正文内容的核心 Prompt。

    包含以下关键优化：
    1. 项目类型和业务场景识别 - 明确告知 AI 应该写什么业务
    2. 数据点注入 - 确保数据一致性
    3. 需求点映射 - 确保回应需求文档的要求
    4. 章节类型识别 + Few-shot - 提供格式参考
    5. 模板内容提取 - 提取参考格式

    Args:
        section_title: 章节标题
        requirement_text: 需求文档内容
        template_text: 模板文档内容
        user_instruction: 用户补充要求
        dp_manager: 数据点管理器（可选）
        req_analyzer: 需求分析器（可选）
        optimizer: 内容优化器（可选）

    Returns:
        Prompt 字符串
    """
    # 识别项目类型和业务场景
    project_type = extract_project_type(requirement_text)
    business_scenes = extract_business_scenes(requirement_text)

    # 获取数据点文本
    data_points_text = ''
    if dp_manager:
        data_points_text = dp_manager.get_formatted_prompt_text()

    # 获取需求点文本
    requirements_text = ''
    if req_analyzer:
        requirements_text = req_analyzer.get_requirements_text(section_title)

    # 提取模板章节内容
    template_section = extract_section_from_template(template_text, section_title)

    # 识别章节类型
    format_guidance = ''
    few_shot_prompt = ''
    type_guidance = ''

    if optimizer:
        type_info = optimizer.identify_section_type(section_title)
        if type_info['format_strategy']:
            type_guidance = f"\n【格式策略】{type_info['format_strategy']}"

        few_shot_prompt = optimizer.get_few_shot_prompt(section_title)

        # 获取格式指导
        if template_section:
            if any(kw in section_title for kw in ['政策', '法规', '标准']):
                format_guidance = "\n   - **本章节特殊要求**：请列出相关的法律法规、政策文件或技术标准"
                format_guidance += "\n   - 使用列表形式，每条包含标准编号（如GB/T、DB33/T等）和标准名称"

    # 构建项目类型提示
    project_type_hint = ''
    if project_type:
        project_type_hint = f"- **项目类型**：{project_type}\n"
    if business_scenes:
        scenes_text = '\n'.join(f"   - {scene}" for scene in business_scenes)
        project_type_hint += f"- **业务场景**：\n{scenes_text}\n"

    return f"""你是一位专业的可行性研究报告编写专家。

【任务】请为【{section_title}】这一章节撰写内容。

【重要提示】
- **内容来源**：必须严格基于【需求文档内容】中的业务信息，这是你撰写内容的唯一来源
- **模板用途**：【参考模板】仅用于学习格式、结构、论述方式，不要直接复用其中的具体业务信息
- **撰写原则**：围绕上述项目类型和业务场景进行撰写，确保内容贴合实际需求
- 只生成【{section_title}】这一章节的内容，不要涉及其他章节
- **严禁**在内容中重复或罗列其他章节的标题
- **重要**：直接输出章节正文内容，不要输出任何分析过程、思考过程、元信息
- **重要**：不要使用 Markdown 格式（如 **粗体**、## 标题等），直接输出纯文本

【项目信息】
{project_type_hint if project_type_hint else '- 项目类型：根据需求文档确定'}

【章节标题】{section_title}

{data_points_text}

【需求文档内容】（这是你撰写内容的唯一来源）
{requirement_text[:2000] if requirement_text else '无相关需求文档'}

{requirements_text}

【参考模板（仅学习格式，不要复制业务内容）】
{template_section if template_section else '无参考模板'}

【用户补充要求】
{user_instruction if user_instruction else '无特殊要求'}
{type_guidance}
{few_shot_prompt}
【输出要求】
1. **内容来源**：必须来自需求文档，根据项目类型和业务场景进行撰写
2. **格式参考**：参考模板的段落结构、列表形式、标准编号等格式特征
3. 内容要专业、准确、逻辑清晰，使用正式的公文语言
4. **重要**：引用数据时必须与【已确立的关键数据】保持完全一致
5. **重要**：必须回应【本章应回应的需求点】中的每一个要点
{format_guidance}
6. 结合需求文档中的具体场景和问题，不要泛泛而谈
7. **不要输出章节标题**（如"{section_title}"）
8. **不要生成总结性段落**（如"通过实施本项目..."）
9. **不要输出任何分析过程、思考过程、元信息**
10. 字数控制在 200-400 字（除非模板格式要求更多内容）

【请开始撰写，直接输出正文内容】
"""


def get_format_guidance(section_title: str, template_section: str) -> str:
    """根据章节类型获取特定的格式指导"""
    guidance = []

    title_lower = section_title.lower()

    # 政策法规/技术规范类章节
    if any(keyword in title_lower for keyword in ['政策', '法规', '规范', '标准', '依据']):
        guidance.append("   - **本章节特殊要求**：请列出相关的法律法规、政策文件或技术标准")
        guidance.append("   - 使用列表形式，每条包含标准编号（如GB/T、DB33/T等）和标准名称")
        guidance.append("   - 参考模板的列举方式，保持格式一致")

    # 检测模板中的格式特征
    if template_section:
        if re.search(r'[A-Z]+/T?\s*\d+[-–]\d{4}', template_section):
            guidance.append("   - **检测到标准编号格式**：请确保生成的内容包含相应的标准编号")
        if re.search(r'^\s*\d+\.', template_section, re.MULTILINE):
            guidance.append("   - **检测到列表格式**：请使用类似的数字列表格式（1. 2. 3.）")

    return '\n'.join(guidance) if guidance else ''


# =============================================================================
# AI 调用与输出清理
# =============================================================================

def clean_ai_content(content: str, section_title: str = '') -> str:
    """清理 AI 生成的内容

    过滤掉：
    1. AI 思考过程（各种模型的思考标记）
    2. Markdown 格式符号

    Args:
        content: AI 生成的原始内容
        section_title: 章节标题（用于调试）

    Returns:
        清理后的内容
    """
    if not content:
        return ''

    # 过滤 AI 思考过程标记
    thinking_markers = [
        # 通用思考标记
        r'^\*\*分析请求：\*\*',
        r'^\*\*目标：\*\*',
        r'^\*\*约束条件：\*\*',
        r'^\*\*输入数据：\*\*',
        r'^\*\*输出要求：\*\*',
        r'^\*\*请开始撰写\*\*',
        r'^\d+\.\s*分析请求',
        r'^\d+\.\s*分析需求',
        r'^\d+\.\s*确定.*内容',
        r'^\d+\.\s*起草内容',
        r'^\d+\.\s*起草策略',
        r'^\d+\.\s*优化内容',
        r'^\d+\.\s*格式检查',
        r'^角色：',
        r'^任务：',
        r'^约束条件：',
        r'^输入数据：',
        r'^输出要求：',
        r'^起草策略：',
        r'^优化内容：',
        r'^格式检查：',
        r'^尝试\s*\d+',
        r'^\*\*尝试\s*\d+\*\*',
        # GLM-4 思考过程
        r'^\*\*\s*1\.\s*分析请求\s*\*\*',
        r'^\*\*\s*2\.\s*分析需求\s*\*\*',
        r'^\*\*\s*3\.\s*确定.*\*\*',
        r'^\*\*\s*4\.\s*起草.*\*\*',
        r'^\*\*\s*5\.\s*优化.*\*\*',
        r'^\*\*\s*6\.\s*格式检查.*\*\*',
        # 更多思考标记
        r'^【分析请求】',
        r'^【目标】',
        r'^【输入】',
        r'^【输出】',
        r'^\*\*1\.\*\*',
        r'^\*\*2\.\*\*',
        r'^\*\*3\.\*\*',
        r'^\*\*4\.\*\*',
        r'^\*\*5\.\*\*',
        r'^\*\*6\.\*\*',
    ]

    lines = content.split('\n')
    cleaned_lines = []

    for line in lines:
        skip = False
        for marker in thinking_markers:
            if re.search(marker, line):
                skip = True
                break

        if not skip:
            cleaned_lines.append(line)

    content = '\n'.join(cleaned_lines)

    # 过滤 Markdown 格式
    content = re.sub(r'\*\*(.+?)\*\*', r'\1', content)  # 粗体
    content = re.sub(r'##+\s+', '', content)             # 标题
    content = re.sub(r'^\s*[-*+]\s+', '', content)      # 无序列表
    content = re.sub(r'^\s*\d+\.\s+', '', content)      # 有序列表（谨慎，可能需要保留）

    return content.strip()


# =============================================================================
# AI 章节内容生成器
# =============================================================================

class ModelConfig:
    """模型配置

    用于配置 AI API 调用参数。
    支持 Ollama、OpenAI、百炼等多种兼容 OpenAI 格式的 API。
    """

    def __init__(self,
                 model: str = 'qwen-max',
                 api_key: str = '',
                 base_url: str = '',
                 max_tokens: int = 2000,
                 temperature: float = 0.7,
                 **kwargs):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.extra = kwargs


class AIChapterGenerator:
    """AI 章节内容生成器

    整合所有服务，提供简单的章节内容生成接口。

    使用方式：
        # 配置模型
        config = ModelConfig(
            model='qwen-max',
            api_key='your-api-key',
            base_url='https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation',
        )

        # 创建生成器
        generator = AIChapterGenerator(config)

        # 生成章节内容
        content = generator.generate(
            section_title='项目概况',
            requirement_text='项目名称：智慧社区\n总投资：500万元...',
            template_text='项目概况\\n本项目...'
        )

        print(content)
    """

    def __init__(self, model_config: ModelConfig,
                 requirement_text: str = '',
                 template_text: str = ''):
        """初始化生成器

        Args:
            model_config: 模型配置
            requirement_text: 需求文档内容（可选）
            template_text: 模板文档内容（可选）
        """
        self.model_config = model_config
        self.requirement_text = requirement_text
        self.template_text = template_text

        # 初始化服务
        self.dp_manager = DataPointManager()
        self.req_analyzer = RequirementAnalyzer()
        self.optimizer = ContentOptimizer()

        # 分析需求文档
        if requirement_text:
            self.req_analyzer.extract(requirement_text)
            data = self.dp_manager.extract_from_text(requirement_text, '需求文档')
            self.dp_manager.update(data, '需求文档')

    def generate(self,
                 section_title: str,
                 requirement_text: str = None,
                 template_text: str = None,
                 user_instruction: str = '',
                 api_call_func: Callable = None) -> str:
        """生成章节内容

        Args:
            section_title: 章节标题
            requirement_text: 需求文档内容（如果初始化时未提供）
            template_text: 模板文档内容（如果初始化时未提供）
            user_instruction: 用户补充要求
            api_call_func: 自定义 API 调用函数（可选）

        Returns:
            生成的章节内容
        """
        req_text = requirement_text or self.requirement_text
        tpl_text = template_text or self.template_text

        # 判断是信息型还是描述型
        if section_title in INFO_FIELDS:
            prompt = build_info_field_prompt(section_title, req_text, tpl_text)
            max_tokens = 100
        else:
            prompt = build_desc_field_prompt(
                section_title, req_text, tpl_text, user_instruction,
                self.dp_manager, self.req_analyzer, self.optimizer
            )
            max_tokens = self.model_config.max_tokens

        # 调用 AI
        if api_call_func:
            content = api_call_func(prompt)
        else:
            content = self._call_api(prompt, max_tokens)

        # 清理输出
        content = clean_ai_content(content, section_title)

        # 更新数据点
        new_data = self.dp_manager.extract_from_text(content, section_title)
        self.dp_manager.update(new_data, section_title)

        # 添加到优化器历史
        self.optimizer.add_generated_content(section_title, content)

        return content

    def _call_api(self, prompt: str, max_tokens: int = 2000) -> str:
        """调用 AI API

        默认实现使用 requests 调用兼容 OpenAI 格式的 API。
        子类可以覆盖此方法实现自定义调用逻辑。

        Args:
            prompt: Prompt 文本
            max_tokens: 最大 token 数

        Returns:
            API 返回的文本内容
        """
        import requests

        config = self.model_config

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {config.api_key}'
        }

        payload = {
            'model': config.model,
            'messages': [{'role': 'user', 'content': prompt}],
            'max_tokens': max_tokens,
            'temperature': config.temperature
        }

        try:
            response = requests.post(
                config.base_url,
                headers=headers,
                json=payload,
                timeout=120
            )
            response.raise_for_status()
            result = response.json()

            # 提取内容（兼容不同格式）
            if 'choices' in result:
                return result['choices'][0]['message']['content']
            elif 'output' in result:
                return result['output']['text']
            else:
                return str(result)

        except Exception as e:
            return f"[AI 调用失败: {str(e)}]"

    def reset(self) -> None:
        """重置生成器状态"""
        self.dp_manager.clear()
        self.req_analyzer.reset()
        self.optimizer.reset()
