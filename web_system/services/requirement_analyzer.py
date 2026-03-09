# -*- coding: utf-8 -*-
"""
需求分析模块 - 实现需求覆盖度检查

功能：
1. 从需求文档动态提取需求点（痛点、需求、目标）
2. 建立章节-需求映射关系
3. 检查生成内容对需求的覆盖度

设计原则：
- 不预设任何需求类型，完全动态识别
- 基于章节标题关键词自动映射
- 支持 AI 辅助的覆盖度检查
"""

import re
import json
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field


@dataclass
class CoverageResult:
    """覆盖度检查结果"""
    covered: List[str] = field(default_factory=list)      # 已覆盖的需求
    uncovered: List[str] = field(default_factory=list)    # 未覆盖的需求
    analysis: str = ""                                     # 分析说明
    coverage_rate: float = 0.0                            # 覆盖率
    
    def __str__(self):
        return f"覆盖率: {self.coverage_rate:.1%} ({len(self.covered)}/{len(self.covered) + len(self.uncovered)})"


class RequirementAnalyzer:
    """需求分析器
    
    分析需求文档，提取关键需求点，并检查生成内容的覆盖度。
    """
    
    # 章节-需求类型映射规则
    # 基于章节标题关键词自动映射
    CHAPTER_REQUIREMENT_MAP = {
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
    
    def __init__(self):
        """初始化需求分析器"""
        self._pain_points: List[str] = []      # 痛点列表
        self._requirements: List[str] = []     # 需求列表
        self._goals: List[str] = []            # 目标列表
        self._coverage_history: List[Dict] = []  # 覆盖度检查历史
    
    def extract(self, requirement_text: str, ai_call_func=None) -> Dict[str, List[str]]:
        """从需求文档中提取需求点
        
        Args:
            requirement_text: 需求文档内容
            ai_call_func: 可选的 AI 调用函数，用于辅助提取
            
        Returns:
            提取结果 {'pain_points': [...], 'requirements': [...], 'goals': [...]}
        """
        if not requirement_text:
            return {'pain_points': [], 'requirements': [], 'goals': []}
        
        # 1. 启发式提取（基于关键词）
        self._extract_heuristic(requirement_text)
        
        # 2. AI 辅助提取（如果提供了 AI 函数）
        if ai_call_func:
            self._extract_with_ai(requirement_text, ai_call_func)
        
        return {
            'pain_points': self._pain_points.copy(),
            'requirements': self._requirements.copy(),
            'goals': self._goals.copy()
        }
    
    def _extract_heuristic(self, text: str) -> None:
        """启发式提取需求点
        
        基于常见关键词和句式提取
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
                    # 提取句子（去除序号和标记）
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
    
    def _extract_with_ai(self, text: str, ai_call_func) -> None:
        """使用 AI 提取需求点
        
        Args:
            text: 需求文档内容
            ai_call_func: AI 调用函数
        """
        prompt = f"""请分析以下需求文档，提取所有的痛点、需求和目标。

【需求文档】
{text[:3000]}

【提取要求】
1. 痛点：当前存在的问题、困难、挑战
2. 需求：需要实现的功能、建设的内容
3. 目标：预期达到的效果、效益

【输出格式】
请以 JSON 格式输出，不要包含其他内容：
{{
  "pain_points": ["痛点1", "痛点2", ...],
  "requirements": ["需求1", "需求2", ...],
  "goals": ["目标1", "目标2", ...]
}}

注意：
- 每个条目要简洁明确，不超过 50 字
- 只提取文档中明确提到的内容
- 如果没有某类内容，对应数组为空"""
        
        try:
            result = ai_call_func(prompt)
            
            # 解析 JSON
            try:
                data = json.loads(result)
            except json.JSONDecodeError:
                json_match = re.search(r'\{[\s\S]*\}', result)
                if json_match:
                    data = json.loads(json_match.group(0))
                else:
                    return
            
            # 合并结果（去重）
            if 'pain_points' in data and isinstance(data['pain_points'], list):
                for item in data['pain_points']:
                    if item and item not in self._pain_points:
                        self._pain_points.append(item)
            
            if 'requirements' in data and isinstance(data['requirements'], list):
                for item in data['requirements']:
                    if item and item not in self._requirements:
                        self._requirements.append(item)
            
            if 'goals' in data and isinstance(data['goals'], list):
                for item in data['goals']:
                    if item and item not in self._goals:
                        self._goals.append(item)
                        
        except Exception as e:
            print(f"[RequirementAnalyzer] AI 提取失败: {e}")
    
    def map_to_chapter(self, chapter_title: str) -> List[str]:
        """根据章节标题映射应回应的需求点
        
        Args:
            chapter_title: 章节标题
            
        Returns:
            该章节应回应的需求点列表
        """
        requirements_to_cover = []
        
        for keyword, req_types in self.CHAPTER_REQUIREMENT_MAP.items():
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
    
    def get_all_requirements(self) -> Dict[str, List[str]]:
        """获取所有需求点
        
        Returns:
            所有需求点的副本
        """
        return {
            'pain_points': self._pain_points.copy(),
            'requirements': self._requirements.copy(),
            'goals': self._goals.copy()
        }
    
    def get_requirements_text(self, chapter_title: str = "") -> str:
        """获取格式化的需求点文本（用于 Prompt 注入）
        
        Args:
            chapter_title: 章节标题（用于筛选相关需求）
            
        Returns:
            格式化的需求点文本
        """
        lines = []
        
        if chapter_title:
            relevant = self.map_to_chapter(chapter_title)
            if relevant:
                lines.append(f"【本章应回应的需求点】")
                for i, req in enumerate(relevant, 1):
                    lines.append(f"{i}. {req}")
            else:
                lines.append("（本章暂无特定需求点要求）")
        else:
            # 输出所有需求点
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
            覆盖度检查结果
        """
        if not requirements:
            return CoverageResult(coverage_rate=1.0, analysis="无需求点需要检查")
        
        if not content:
            return CoverageResult(
                uncovered=requirements.copy(),
                analysis="内容为空"
            )
        
        # 1. 启发式检查（关键词匹配）
        covered = []
        uncovered = []
        
        for req in requirements:
            # 提取关键词（去除停用词）
            keywords = self._extract_keywords(req)
            
            # 检查是否有足够的关键词出现在内容中
            match_count = sum(1 for kw in keywords if kw in content)
            match_rate = match_count / len(keywords) if keywords else 0
            
            if match_rate >= 0.5:  # 50% 关键词匹配即认为覆盖
                covered.append(req)
            else:
                uncovered.append(req)
        
        result = CoverageResult(
            covered=covered,
            uncovered=uncovered,
            coverage_rate=len(covered) / len(requirements) if requirements else 1.0
        )
        
        # 2. AI 辅助检查（如果提供了 AI 函数且启发式检查有遗漏）
        if ai_call_func and uncovered:
            result = self._check_coverage_with_ai(content, requirements, ai_call_func)
        
        # 记录历史
        self._coverage_history.append({
            'requirements': requirements.copy(),
            'covered': result.covered.copy(),
            'uncovered': result.uncovered.copy(),
            'coverage_rate': result.coverage_rate
        })
        
        return result
    
    def _check_coverage_with_ai(self, content: str, requirements: List[str],
                                 ai_call_func) -> CoverageResult:
        """使用 AI 检查覆盖度
        
        Args:
            content: 生成的内容
            requirements: 需求点列表
            ai_call_func: AI 调用函数
            
        Returns:
            覆盖度检查结果
        """
        req_text = "\n".join([f"{i+1}. {req}" for i, req in enumerate(requirements)])
        
        prompt = f"""请检查以下内容是否回应了以下需求点。

【需求点列表】
{req_text}

【待检查内容】
{content[:2000]}

【检查要求】
1. 判断每个需求点是否在内容中有明确回应
2. "回应"指内容直接相关或间接涉及该需求
3. 不要严格要求字面匹配，关注语义相关

【输出格式】
请以 JSON 格式输出：
{{
  "covered": ["已回应的需求1", ...],
  "uncovered": ["未回应的需求1", ...],
  "analysis": "简要分析说明"
}}"""
        
        try:
            result = ai_call_func(prompt)
            
            # 解析 JSON
            try:
                data = json.loads(result)
            except json.JSONDecodeError:
                json_match = re.search(r'\{[\s\S]*\}', result)
                if json_match:
                    data = json.loads(json_match.group(0))
                else:
                    raise ValueError("无法解析 AI 返回")
            
            covered = data.get('covered', [])
            uncovered = data.get('uncovered', requirements.copy())
            analysis = data.get('analysis', '')
            
            # 计算覆盖率
            total = len(covered) + len(uncovered)
            coverage_rate = len(covered) / total if total > 0 else 1.0
            
            return CoverageResult(
                covered=covered,
                uncovered=uncovered,
                analysis=analysis,
                coverage_rate=coverage_rate
            )
            
        except Exception as e:
            print(f"[RequirementAnalyzer] AI 覆盖度检查失败: {e}")
            # 返回启发式检查结果
            return CoverageResult(
                covered=[],
                uncovered=requirements.copy(),
                analysis=f"AI 检查失败: {e}"
            )
    
    def get_uncovered_requirements(self, chapter_contents: Dict[str, str],
                                    ai_call_func=None) -> List[str]:
        """获取全文中未覆盖的需求点
        
        Args:
            chapter_contents: 章节内容字典 {章节标题: 内容}
            ai_call_func: 可选的 AI 调用函数
            
        Returns:
            未覆盖的需求点列表
        """
        all_uncovered = set()
        
        # 获取所有需求点
        all_requirements = (
            self._pain_points + 
            self._requirements + 
            self._goals
        )
        
        # 合并所有章节内容
        full_text = "\n\n".join(chapter_contents.values())
        
        # 检查覆盖度
        result = self.check_coverage(full_text, all_requirements, ai_call_func)
        
        return result.uncovered
    
    def _clean_requirement_text(self, text: str) -> str:
        """清理需求文本
        
        去除序号、标记等
        """
        # 去除常见序号格式
        cleaned = re.sub(r'^\s*[\d一二三四五六七八九十]+[、.．\s]+', '', text)
        cleaned = re.sub(r'^\s*[(（][\d一二三四五六七八九十]+[)）]\s*', '', cleaned)
        cleaned = re.sub(r'^\s*[-•●*]\s*', '', cleaned)
        
        # 去除首尾空白
        cleaned = cleaned.strip()
        
        # 限制长度
        if len(cleaned) > 100:
            cleaned = cleaned[:100] + "..."
        
        return cleaned
    
    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词
        
        从文本中提取有意义的关键词
        """
        # 停用词
        stop_words = {'的', '了', '在', '是', '和', '与', '或', '有', '被', '把',
                      '为', '之', '而', '及', '等', '对', '从', '到', '由', '向',
                      '要', '需', '应', '须', '请', '将', '会', '能', '可'}
        
        # 提取中文字符和数字
        words = re.findall(r'[\u4e00-\u9fa5]{2,}|[\d]+', text)
        
        # 过滤停用词
        keywords = [w for w in words if w not in stop_words and len(w) >= 2]
        
        return keywords
    
    def clear(self) -> None:
        """清空所有需求点和历史记录"""
        self._pain_points.clear()
        self._requirements.clear()
        self._goals.clear()
        self._coverage_history.clear()
    
    def get_summary(self) -> Dict:
        """获取需求分析摘要
        
        Returns:
            摘要信息
        """
        return {
            'pain_points_count': len(self._pain_points),
            'requirements_count': len(self._requirements),
            'goals_count': len(self._goals),
            'total': len(self._pain_points) + len(self._requirements) + len(self._goals),
            'pain_points': self._pain_points.copy(),
            'requirements': self._requirements.copy(),
            'goals': self._goals.copy(),
            'coverage_check_count': len(self._coverage_history)
        }


# 便捷函数
def create_requirement_analyzer() -> RequirementAnalyzer:
    """创建需求分析器实例"""
    return RequirementAnalyzer()


# 测试代码
if __name__ == '__main__':
    # 简单测试
    analyzer = RequirementAnalyzer()
    
    # 测试文本
    test_text = """
    当前社区存在以下问题：
    1. 监控设备老化，存在安全隐患
    2. 电瓶车盗窃问题频发
    3. 流动人口管理困难
    
    需要建设：
    - 高清监控系统
    - 电瓶车防盗系统
    - 流动人口管理平台
    
    预期目标：
    - 提升社区安全水平
    - 改善居民生活品质
    """
    
    # 提取需求点
    result = analyzer.extract(test_text)
    print("提取结果：")
    print(f"  痛点: {result['pain_points']}")
    print(f"  需求: {result['requirements']}")
    print(f"  目标: {result['goals']}")
    
    # 测试章节映射
    chapter_reqs = analyzer.map_to_chapter("3 项目建设的必要性")
    print(f"\n章节 '3 项目建设的必要性' 应回应: {chapter_reqs}")
