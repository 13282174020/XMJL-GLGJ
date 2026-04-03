# -*- coding: utf-8 -*-
"""
数据点管理器

功能：
1. 从文本中提取关键数据（项目名称、投资、工期等）
2. 管理数据一致性，确保文档中同一数据只出现一次且值一致
3. 将数据点注入 Prompt，确保 AI 生成的内容数据一致

使用方式：
    dp_manager = DataPointManager()

    # 从需求文档提取数据
    data = dp_manager.extract_from_text(requirement_text, '需求文档')

    # 从生成内容中提取并更新
    new_data = dp_manager.extract_from_text(generated_content, '项目概况')
    dp_manager.update(new_data, '项目概况')

    # 获取注入 Prompt 的文本
    prompt_text = dp_manager.get_formatted_prompt_text()
"""

import re
import json
from dataclasses import dataclass
from typing import Dict, List, Optional, Any


# =============================================================================
# 数据结构
# =============================================================================

@dataclass
class DataConflict:
    """数据冲突"""
    data_key: str          # 数据项名称
    old_value: str         # 旧值
    new_value: str         # 新值
    source: str            # 来源章节
    resolution: str        # 解决方式


# =============================================================================
# 数据点管理器
# =============================================================================

class DataPointManager:
    """数据点管理器

    管理文档中需要保持一致的关键数据，如：
    - 项目名称、建设单位
    - 总投资、建设工期
    - 人口数量、户数等

    使用方式：
        dp_manager = DataPointManager()

        # 提取
        data = dp_manager.extract_from_text('项目总投资 500 万元', '需求文档')

        # 更新
        dp_manager.update(data, '项目概况')

        # 获取 Prompt 文本
        print(dp_manager.get_formatted_prompt_text())
    """

    # 正则表达式模式 - 用于识别常见数据类型
    PATTERNS: Dict[str, List[str]] = {
        'amount': [
            r'([\d\.]+)\s*万?元',                        # 500万元、1000元
            r'投资[\s:：]*([\d\.]+)\s*万?元',            # 总投资：500万元
        ],
        'duration': [
            r'([\d]+)\s*个?[年月天]',                    # 12个月
            r'工期[\s:：]*([\d]+)\s*个?[年月天]',        # 建设工期：12个月
        ],
        'population': [
            r'约?\s*([\d\.]+)\s*万?人',                  # 约1.1万人
            r'([\d]+)\s*户',                              # 3000户
        ],
        'project_name': [
            r'项目名称[\s:：]*([^\n]+)',                  # 项目名称：XXX
        ],
        'organization': [
            r'建设单位[\s:：]*([^\n]+)',                  # 建设单位：XXX
            r'业主单位[\s:：]*([^\n]+)',                  # 业主单位：XXX
            r'实施单位[\s:：]*([^\n]+)',                  # 实施单位：XXX
        ],
    }

    def __init__(self):
        """初始化数据点管理器"""
        self._data_points: Dict[str, str] = {}
        self._conflicts: List[DataConflict] = []
        self._extraction_history: List[Dict] = []

    def extract_from_text(self, text: str, chapter: str = "") -> Dict[str, str]:
        """从文本中提取数据点

        Args:
            text: 待分析的文本
            chapter: 文本来源章节（用于冲突记录）

        Returns:
            提取到的数据点字典 {数据项名称: 数据值}
        """
        extracted = {}

        if not text:
            return extracted

        # 1. 使用正则表达式提取常见数据
        for data_type, patterns in self.PATTERNS.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    value = match.group(1).strip() if match.groups() else match.group(0).strip()

                    # 根据匹配类型生成数据项名称
                    key = self._infer_key_from_context(text, match.start(), data_type)
                    if key and value:
                        extracted[key] = value

        # 2. 启发式规则：识别"XXX：YYY"格式的键值对
        kv_pattern = r'^\s*([^：:\n]{2,20})[\s:：]+([^\n]{1,50})$'
        for line in text.split('\n'):
            match = re.match(kv_pattern, line.strip())
            if match:
                key = match.group(1).strip()
                value = match.group(2).strip()
                if self._is_likely_data_point(key, value):
                    extracted[key] = value

        # 记录提取历史
        self._extraction_history.append({
            'chapter': chapter,
            'extracted': extracted.copy()
        })

        return extracted

    def extract_with_ai(self, text: str, ai_call_func, chapter: str = "") -> Dict[str, str]:
        """使用 AI 提取数据点

        Args:
            text: 待分析的文本
            ai_call_func: AI 调用函数
            chapter: 文本来源章节

        Returns:
            提取到的数据点字典
        """
        if not text or not ai_call_func:
            return {}

        prompt = f"""请从以下文本中提取关键数据点。

【文本内容】
{text[:2000]}

【提取要求】
1. 提取关键的数据项（如项目名称、金额、人数、日期等）
2. 只提取明确的数据，不要推测

【输出格式】
JSON 格式：
{{
  "项目名称": "值",
  "总投资": "值",
  "建设工期": "值"
}}

如果某项数据不存在，不要包含在输出中。"""

        try:
            result = ai_call_func(prompt)
            data = json.loads(result)
            return {k: v for k, v in data.items() if v}
        except Exception:
            return {}

    def update(self, new_data: Dict[str, str], source: str) -> List[DataConflict]:
        """更新数据点，检测冲突

        Args:
            new_data: 新提取的数据点
            source: 来源章节

        Returns:
            冲突列表
        """
        conflicts = []

        for key, value in new_data.items():
            if key in self._data_points:
                if self._data_points[key] != value:
                    conflict = DataConflict(
                        data_key=key,
                        old_value=self._data_points[key],
                        new_value=value,
                        source=source,
                        resolution='keep_old'  # 默认保留旧值
                    )
                    conflicts.append(conflict)
                    self._conflicts.append(conflict)
            else:
                self._data_points[key] = value

        return conflicts

    def get(self, key: str, default: str = None) -> Optional[str]:
        """获取数据点"""
        return self._data_points.get(key, default)

    def get_formatted_prompt_text(self) -> str:
        """获取格式化的数据点文本

        用于注入到 AI Prompt 中。

        Returns:
            格式化的文本
        """
        if not self._data_points:
            return "（暂无已确立的关键数据）"

        lines = ["【已确立的关键数据】",
                 "（以下数据已在文中确立，引用时必须保持一致）", ""]

        for key, value in sorted(self._data_points.items()):
            lines.append(f"- {key}：{value}")

        return "\n".join(lines)

    def get_formatted_json(self) -> str:
        """获取格式化的 JSON 字符串"""
        return json.dumps(self._data_points, ensure_ascii=False, indent=2)

    def get_conflicts(self) -> List[DataConflict]:
        """获取所有冲突"""
        return self._conflicts.copy()

    def clear(self) -> None:
        """清空所有数据点和冲突记录"""
        self._data_points.clear()
        self._conflicts.clear()
        self._extraction_history.clear()

    # ========== 辅助方法 ==========

    def _infer_key_from_context(self, text: str, position: int, data_type: str) -> Optional[str]:
        """根据上下文推断数据项名称"""
        start = max(0, position - 50)
        context = text[start:position]

        if data_type == 'amount':
            if '投资' in context or '总投' in context:
                return '总投资'
            elif '预算' in context or '估算' in context:
                return '投资估算'
            elif '资金' in context:
                return '资金金额'

        elif data_type == 'duration':
            if '工期' in context or '周期' in context:
                return '建设工期'
            elif '时间' in context:
                return '建设周期'

        elif data_type == 'population':
            if '人口' in context or '人' in context:
                return '人口数量'
            elif '户' in context:
                return '户数'

        elif data_type == 'project_name':
            return '项目名称'

        elif data_type == 'organization':
            if '建设' in context:
                return '建设单位'
            elif '业主' in context:
                return '业主单位'
            elif '实施' in context:
                return '实施单位'

        return None

    def _is_likely_data_point(self, key: str, value: str) -> bool:
        """判断是否为可能的数据点"""
        # 排除明显的非数据项
        exclude_keys = ['标题', '说明', '备注', '附件', '目录']
        if any(ex in key for ex in exclude_keys):
            return False

        # 值长度合理
        if len(value) > 100 or len(value) < 1:
            return False

        # 排除纯句子
        if value.endswith('。') or value.endswith('，'):
            return False

        return True
