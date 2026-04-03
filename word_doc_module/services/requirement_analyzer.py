# -*- coding: utf-8 -*-
"""
需求分析器

功能：
1. 从需求文档中提取痛点、需求、目标
2. 建立章节标题到需求类型的映射
3. 检查生成内容对需求的覆盖度

使用方式：
    analyzer = RequirementAnalyzer()

    # 分析需求文档
    result = analyzer.extract(requirement_text)
    print(result['pain_points'])
    print(result['requirements'])
    print(result['goals'])

    # 获取章节应回应的需求
    req_text = analyzer.get_requirements_text('项目背景')
    print(req_text)

    # 检查覆盖度
    coverage = analyzer.check_coverage(generated_content, requirements_list)
    print(coverage.coverage_rate)
"""

import re
import json
from dataclasses import dataclass
from typing import Dict, List, Optional, Any


# =============================================================================
# 数据结构
# =============================================================================

@dataclass
class CoverageResult:
    """覆盖度检查结果"""
    coverage_rate: float           # 覆盖率 0-1
    covered: List[str]             # 已覆盖的需求
    uncovered: List[str]           # 未覆盖的需求
    analysis: str                  # 分析说明


# =============================================================================
# 章节-需求类型映射
# =============================================================================

# 章节标题关键词 -> 应回应的需求类型
CHAPTER_REQUIREMENT_MAP: Dict[str, List[str]] = {
    # 必要性相关章节 -> 应回应痛点
    '必要性': ['pain_points'],
    '背景': ['pain_points'],
    '现状': ['pain_points'],
    '问题': ['pain_points'],

    # 需求相关章节 -> 应回应需求
    '需求': ['requirements'],
    '分析': ['requirements'],
    '建设内容': ['requirements'],
    '建设方案': ['requirements'],
    '技术方案': ['requirements'],
    '系统设计': ['requirements'],
    '功能': ['requirements'],

    # 目标相关章节 -> 应回应目标
    '目标': ['goals'],
    '效益': ['goals'],
    '预期': ['goals'],
    '成果': ['goals'],

    # 综合章节 -> 回应多种需求
    '总体': ['pain_points', 'requirements', 'goals'],
    '概述': ['pain_points', 'requirements', 'goals'],
    '概况': ['pain_points', 'requirements', 'goals'],
}


# =============================================================================
# 需求分析器
# =============================================================================

class RequirementAnalyzer:
    """需求分析器

    分析需求文档，提取关键需求点，并检查生成内容的覆盖度。

    使用方式：
        analyzer = RequirementAnalyzer()
        result = analyzer.extract(requirement_text)
        req_text = analyzer.get_requirements_text('项目背景')
    """

    def __init__(self):
        """初始化需求分析器"""
        self._pain_points: List[str] = []
        self._requirements: List[str] = []
        self._goals: List[str] = []
        self._coverage_history: List[Dict] = []

    def extract(self, requirement_text: str) -> Dict[str, List[str]]:
        """从需求文档中提取需求点

        使用启发式规则提取，支持后续扩展 AI 辅助提取。

        Args:
            requirement_text: 需求文档内容

        Returns:
            {
                'pain_points': [...],   # 痛点列表
                'requirements': [...],  # 需求列表
                'goals': [...]          # 目标列表
            }
        """
        if not requirement_text:
            return {'pain_points': [], 'requirements': [], 'goals': []}

        # 使用启发式提取
        self._extract_heuristic(requirement_text)

        return {
            'pain_points': self._pain_points.copy(),
            'requirements': self._requirements.copy(),
            'goals': self._goals.copy()
        }

    def _extract_heuristic(self, text: str) -> None:
        """启发式提取需求点

        基于关键词和句式提取痛点、需求、目标。
        """
        lines = text.split('\n')

        for line in lines:
            line = line.strip()
            if not line or len(line) < 5:
                continue

            # 痛点识别
            pain_indicators = [
                r'问题', r'困难', r'痛点', r'挑战', r'瓶颈', r'障碍',
                r'不足', r'缺陷', r'隐患', r'风险', r'老化', r'落后',
                r'缺乏', r'不够', r'不足', r'难以', r'无法'
            ]
            for indicator in pain_indicators:
                if re.search(indicator, line):
                    cleaned = self._clean_requirement_text(line)
                    if cleaned and cleaned not in self._pain_points:
                        self._pain_points.append(cleaned)
                    break

            # 需求识别
            req_indicators = [
                r'需要', r'需求', r'要求', r'必须', r'应', r'需',
                r'建设', r'实现', r'完成', r'达到', r'满足',
                r'具备', r'拥有', r'配置', r'部署', r'安装'
            ]
            for indicator in req_indicators:
                if re.search(indicator, line):
                    cleaned = self._clean_requirement_text(line)
                    if cleaned and cleaned not in self._requirements:
                        self._requirements.append(cleaned)
                    break

            # 目标识别
            goal_indicators = [
                r'目标', r'目的', r'旨在', r'为了', r'实现',
                r'提升', r'提高', r'改善', r'优化', r'增强',
                r'降低', r'减少', r'节约', r'效率', r'效益'
            ]
            for indicator in goal_indicators:
                if re.search(indicator, line):
                    cleaned = self._clean_requirement_text(line)
                    if cleaned and cleaned not in self._goals:
                        self._goals.append(cleaned)
                    break

    def _clean_requirement_text(self, text: str) -> str:
        """清理需求文本"""
        # 去除序号前缀
        text = re.sub(r'^[\d一二三四五六七八九十]+[.、)）\s]+', '', text)
        # 去除多余空格
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def extract_with_ai(self, text: str, ai_call_func) -> None:
        """使用 AI 辅助提取需求点

        Args:
            text: 需求文档内容
            ai_call_func: AI 调用函数，接收 prompt 返回字符串
        """
        prompt = f"""请分析以下需求文档，提取所有的痛点、需求和目标。

【需求文档】
{text[:3000]}

【提取要求】
1. 痛点：当前存在的问题、困难、挑战
2. 需求：需要实现的功能、建设的内容
3. 目标：预期达到的效果、效益

【输出格式】
请以 JSON 格式输出：
{{
  "pain_points": ["痛点1", "痛点2", ...],
  "requirements": ["需求1", "需求2", ...],
  "goals": ["目标1", "目标2", ...]
}}

注意：
- 每个条目要简洁明确，不超过 50 字
- 只提取文档中明确提到的内容"""

        try:
            result = ai_call_func(prompt)
            data = json.loads(result)

            if 'pain_points' in data:
                for item in data['pain_points']:
                    if item and item not in self._pain_points:
                        self._pain_points.append(item)

            if 'requirements' in data:
                for item in data['requirements']:
                    if item and item not in self._requirements:
                        self._requirements.append(item)

            if 'goals' in data:
                for item in data['goals']:
                    if item and item not in self._goals:
                        self._goals.append(item)

        except Exception:
            pass

    def map_to_chapter(self, chapter_title: str) -> List[str]:
        """根据章节标题映射应回应的需求点

        Args:
            chapter_title: 章节标题

        Returns:
            该章节应回应的需求点列表
        """
        requirements_to_cover = []

        for keyword, req_types in CHAPTER_REQUIREMENT_MAP.items():
            if keyword in chapter_title:
                for req_type in req_types:
                    if req_type == 'pain_points':
                        requirements_to_cover.extend(self._pain_points)
                    elif req_type == 'requirements':
                        requirements_to_cover.extend(self._requirements)
                    elif req_type == 'goals':
                        requirements_to_cover.extend(self._goals)

        # 去重
        return list(dict.fromkeys(requirements_to_cover))

    def get_requirements_text(self, chapter_title: str = "") -> str:
        """获取格式化的需求点文本

        用于 Prompt 注入。

        Args:
            chapter_title: 章节标题，为空则输出所有需求点

        Returns:
            格式化的需求点文本
        """
        lines = []

        if chapter_title:
            relevant = self.map_to_chapter(chapter_title)
            if relevant:
                lines.append("【本章应回应的需求点】")
                for i, req in enumerate(relevant, 1):
                    lines.append(f"{i}. {req}")
            else:
                lines.append("（本章暂无特定需求点要求）")
        else:
            if self._pain_points:
                lines.append("【痛点】")
                for item in self._pain_points:
                    lines.append(f"- {item}")

            if self._requirements:
                lines.append("\n【需求】")
                for item in self._requirements:
                    lines.append(f"- {item}")

            if self._goals:
                lines.append("\n【目标】")
                for item in self._goals:
                    lines.append(f"- {item}")

        return "\n".join(lines) if lines else "（暂无需求点）"

    def check_coverage(self, content: str, requirements: List[str],
                       ai_call_func=None) -> CoverageResult:
        """检查内容对需求的覆盖度

        Args:
            content: 生成的内容
            requirements: 需要检查的需求点列表
            ai_call_func: 可选的 AI 调用函数

        Returns:
            CoverageResult 对象
        """
        if not requirements:
            return CoverageResult(coverage_rate=1.0, analysis="无需求点需要检查")

        if not content:
            return CoverageResult(
                covered=[],
                uncovered=requirements.copy(),
                coverage_rate=0.0,
                analysis="内容为空"
            )

        # 启发式检查（关键词匹配）
        covered = []
        uncovered = []

        for req in requirements:
            keywords = self._extract_keywords(req)
            match_count = sum(1 for kw in keywords if kw in content)
            match_rate = match_count / len(keywords) if keywords else 0

            if match_rate >= 0.5:
                covered.append(req)
            else:
                uncovered.append(req)

        coverage_rate = len(covered) / len(requirements) if requirements else 1.0

        return CoverageResult(
            covered=covered,
            uncovered=uncovered,
            coverage_rate=coverage_rate,
            analysis=f"覆盖率: {len(covered)}/{len(requirements)} ({coverage_rate:.1%})"
        )

    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        # 去除停用词
        stopwords = ['的', '了', '在', '是', '和', '与', '或', '等', '进行', '实现']
        words = re.findall(r'[\w]+', text)
        return [w for w in words if len(w) >= 2 and w not in stopwords]

    def get_all_requirements(self) -> Dict[str, List[str]]:
        """获取所有需求点"""
        return {
            'pain_points': self._pain_points.copy(),
            'requirements': self._requirements.copy(),
            'goals': self._goals.copy()
        }

    def reset(self) -> None:
        """重置所有数据"""
        self._pain_points.clear()
        self._requirements.clear()
        self._goals.clear()
        self._coverage_history.clear()
