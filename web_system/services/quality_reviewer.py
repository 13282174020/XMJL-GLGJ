# -*- coding: utf-8 -*-
"""
质量审校模块 - 实现全文审校

功能：
1. 审校数据一致性（检查全文数据是否前后一致）
2. 审校需求覆盖度（检查是否覆盖所有需求点）
3. 生成审校报告

设计原则：
- 独立于生成流程，可作为后置检查
- 支持 AI 辅助的深度审校
- 输出结构化的审校报告
"""

import re
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ConsistencyIssue:
    """一致性问题的记录"""
    data_name: str                    # 数据项名称
    values: List[str]                 # 出现的所有值
    locations: List[str]              # 出现位置（章节）
    severity: str = "warning"         # 严重程度：error/warning/info
    suggestion: str = ""              # 修改建议
    
    def __str__(self):
        values_str = " vs ".join([f"'{v}'" for v in self.values])
        return f"[{self.severity.upper()}] {self.data_name}: {values_str}"


@dataclass
class CoverageIssue:
    """覆盖度问题的记录"""
    requirement: str                  # 未覆盖的需求
    req_type: str                     # 需求类型：pain_point/requirement/goal
    suggested_chapter: str = ""       # 建议补充的章节
    severity: str = "warning"         # 严重程度
    
    def __str__(self):
        return f"[{self.severity.upper()}] 未覆盖: {self.requirement}"


@dataclass
class ReviewReport:
    """审校报告"""
    # 基本信息
    review_time: str = field(default_factory=lambda: datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    total_chapters: int = 0
    total_words: int = 0
    
    # 一致性审校结果
    consistency_issues: List[ConsistencyIssue] = field(default_factory=list)
    data_consistency_rate: float = 1.0
    
    # 覆盖度审校结果
    coverage_issues: List[CoverageIssue] = field(default_factory=list)
    requirement_coverage_rate: float = 1.0
    
    # 总体评估
    overall_score: float = 100.0      # 综合评分（0-100）
    overall_assessment: str = ""       # 总体评估意见
    
    # 改进建议
    improvement_suggestions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'review_time': self.review_time,
            'total_chapters': self.total_chapters,
            'total_words': self.total_words,
            'consistency': {
                'issues': [
                    {
                        'data_name': i.data_name,
                        'values': i.values,
                        'locations': i.locations,
                        'severity': i.severity,
                        'suggestion': i.suggestion
                    }
                    for i in self.consistency_issues
                ],
                'consistency_rate': self.data_consistency_rate,
                'issue_count': len(self.consistency_issues)
            },
            'coverage': {
                'issues': [
                    {
                        'requirement': i.requirement,
                        'req_type': i.req_type,
                        'suggested_chapter': i.suggested_chapter,
                        'severity': i.severity
                    }
                    for i in self.coverage_issues
                ],
                'coverage_rate': self.requirement_coverage_rate,
                'issue_count': len(self.coverage_issues)
            },
            'overall': {
                'score': self.overall_score,
                'assessment': self.overall_assessment,
                'suggestions': self.improvement_suggestions
            }
        }
    
    def to_markdown(self) -> str:
        """生成 Markdown 格式报告"""
        lines = [
            "# 文档质量审校报告",
            "",
            f"**审校时间**: {self.review_time}",
            f"**章节数量**: {self.total_chapters}",
            f"**总字数**: {self.total_words}",
            "",
            "## 总体评估",
            "",
            f"**综合评分**: {self.overall_score:.1f}/100",
            "",
            f"{self.overall_assessment}",
            "",
            "## 数据一致性审校",
            "",
            f"**一致性率**: {self.data_consistency_rate:.1%}",
            f"**问题数量**: {len(self.consistency_issues)}",
            ""
        ]
        
        if self.consistency_issues:
            lines.append("### 问题详情")
            lines.append("")
            for issue in self.consistency_issues:
                lines.append(f"- **{issue.data_name}**")
                values_str = ', '.join(["'" + v + "'" for v in issue.values])
                lines.append(f"  - 不一致的值: {values_str}")
                lines.append(f"  - 出现位置: {', '.join(issue.locations)}")
                lines.append(f"  - 严重程度: {issue.severity}")
                if issue.suggestion:
                    lines.append(f"  - 建议: {issue.suggestion}")
                lines.append("")
        else:
            lines.append("✅ 未发现数据一致性问题")
            lines.append("")
        
        lines.extend([
            "## 需求覆盖度审校",
            "",
            f"**覆盖率**: {self.requirement_coverage_rate:.1%}",
            f"**问题数量**: {len(self.coverage_issues)}",
            ""
        ])
        
        if self.coverage_issues:
            lines.append("### 未覆盖需求")
            lines.append("")
            for issue in self.coverage_issues:
                lines.append(f"- **[{issue.req_type}]** {issue.requirement}")
                if issue.suggested_chapter:
                    lines.append(f"  - 建议补充章节: {issue.suggested_chapter}")
                lines.append("")
        else:
            lines.append("✅ 所有需求点均已覆盖")
            lines.append("")
        
        if self.improvement_suggestions:
            lines.extend([
                "## 改进建议",
                ""
            ])
            for i, suggestion in enumerate(self.improvement_suggestions, 1):
                lines.append(f"{i}. {suggestion}")
            lines.append("")
        
        return "\n".join(lines)


class QualityReviewer:
    """质量审校器
    
    对生成的文档进行全文审校，检查数据一致性和需求覆盖度。
    """
    
    def __init__(self):
        """初始化质量审校器"""
        self._report: Optional[ReviewReport] = None
        self._review_history: List[ReviewReport] = []
    
    def review_consistency(self, chapter_contents: Dict[str, str], 
                           data_points: Dict[str, str],
                           ai_call_func=None) -> List[ConsistencyIssue]:
        """审校数据一致性
        
        Args:
            chapter_contents: 章节内容字典 {章节标题: 内容}
            data_points: 期望保持一致的数据点
            ai_call_func: 可选的 AI 调用函数
            
        Returns:
            一致性问题列表
        """
        issues = []
        
        if not chapter_contents:
            return issues
        
        # 1. 检查数据点在全文中的一致性
        for data_name, expected_value in data_points.items():
            found_values = []
            locations = []
            
            for chapter_title, content in chapter_contents.items():
                if not content:
                    continue
                
                # 在内容中查找该数据
                # 使用多种匹配方式
                patterns = [
                    re.escape(expected_value),  # 精确匹配
                    re.escape(expected_value).replace(r'\ ', r'\s*'),  # 忽略空格
                ]
                
                found = False
                for pattern in patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        found = True
                        break
                
                # 同时检查是否有不同的值
                # 提取可能的变体
                value_pattern = r'(?:' + re.escape(data_name) + r'[\s:：]+)([^\n，。；]{1,30})'
                matches = re.findall(value_pattern, content, re.IGNORECASE)
                
                for match in matches:
                    match_clean = match.strip()
                    if match_clean and match_clean != expected_value:
                        if match_clean not in found_values:
                            found_values.append(match_clean)
                        if chapter_title not in locations:
                            locations.append(chapter_title)
            
            # 如果发现了不同的值，记录问题
            if found_values:
                all_values = [expected_value] + found_values
                issue = ConsistencyIssue(
                    data_name=data_name,
                    values=all_values,
                    locations=locations,
                    severity="error" if len(found_values) > 1 else "warning",
                    suggestion=f"建议统一为: {expected_value}"
                )
                issues.append(issue)
        
        # 2. AI 辅助深度检查（如果提供了 AI 函数）
        if ai_call_func and len(chapter_contents) > 1:
            ai_issues = self._review_consistency_with_ai(chapter_contents, data_points, ai_call_func)
            # 合并结果（去重）
            existing_names = {i.data_name for i in issues}
            for issue in ai_issues:
                if issue.data_name not in existing_names:
                    issues.append(issue)
        
        return issues
    
    def _review_consistency_with_ai(self, chapter_contents: Dict[str, str],
                                     data_points: Dict[str, str],
                                     ai_call_func) -> List[ConsistencyIssue]:
        """使用 AI 审校一致性
        
        Args:
            chapter_contents: 章节内容字典
            data_points: 数据点
            ai_call_func: AI 调用函数
            
        Returns:
            一致性问题列表
        """
        # 合并所有内容
        full_text = "\n\n".join([
            f"【{title}】\n{content[:500]}" 
            for title, content in chapter_contents.items()
        ])
        
        data_text = "\n".join([f"- {k}: {v}" for k, v in data_points.items()])
        
        prompt = f"""请检查以下文档内容中的数据一致性。

【期望保持一致的数据】
{data_text}

【文档内容摘要】
{full_text[:3000]}

【检查要求】
1. 检查上述数据在文档中是否保持一致
2. 如果发现同一数据有不同表述，记录下来
3. 关注金额、时间、数量、名称等关键数据

【输出格式】
请以 JSON 格式输出：
{{
  "issues": [
    {{
      "data_name": "数据项名称",
      "values": ["值1", "值2"],
      "severity": "error/warning",
      "suggestion": "修改建议"
    }}
  ]
}}

如果没有发现问题，输出空数组。"""
        
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
                    return []
            
            issues = []
            for item in data.get('issues', []):
                issue = ConsistencyIssue(
                    data_name=item.get('data_name', ''),
                    values=item.get('values', []),
                    locations=[],  # AI 可能无法提供准确位置
                    severity=item.get('severity', 'warning'),
                    suggestion=item.get('suggestion', '')
                )
                issues.append(issue)
            
            return issues
            
        except Exception as e:
            print(f"[QualityReviewer] AI 一致性审校失败: {e}")
            return []
    
    def review_coverage(self, chapter_contents: Dict[str, str],
                        requirements: Dict[str, List[str]],
                        ai_call_func=None) -> List[CoverageIssue]:
        """审校需求覆盖度
        
        Args:
            chapter_contents: 章节内容字典
            requirements: 需求点字典 {'pain_points': [...], 'requirements': [...], 'goals': [...]}
            ai_call_func: 可选的 AI 调用函数
            
        Returns:
            覆盖度问题列表
        """
        issues = []
        
        if not chapter_contents or not requirements:
            return issues
        
        # 合并所有内容
        full_text = "\n\n".join(chapter_contents.values())
        
        # 检查每类需求
        req_type_map = {
            'pain_points': '痛点',
            'requirements': '需求',
            'goals': '目标'
        }
        
        for req_type, req_list in requirements.items():
            if not req_list:
                continue
            
            for req in req_list:
                # 启发式检查
                keywords = self._extract_keywords(req)
                match_count = sum(1 for kw in keywords if kw in full_text)
                match_rate = match_count / len(keywords) if keywords else 0
                
                if match_rate < 0.3:  # 匹配度低于 30% 认为未覆盖
                    # 建议补充的章节
                    suggested = self._suggest_chapter_for_requirement(req)
                    
                    issue = CoverageIssue(
                        requirement=req,
                        req_type=req_type_map.get(req_type, req_type),
                        suggested_chapter=suggested,
                        severity="warning"
                    )
                    issues.append(issue)
        
        # AI 辅助检查
        if ai_call_func:
            ai_issues = self._review_coverage_with_ai(chapter_contents, requirements, ai_call_func)
            # 合并（去重）
            existing_reqs = {i.requirement for i in issues}
            for issue in ai_issues:
                if issue.requirement not in existing_reqs:
                    issues.append(issue)
        
        return issues
    
    def _review_coverage_with_ai(self, chapter_contents: Dict[str, str],
                                  requirements: Dict[str, List[str]],
                                  ai_call_func) -> List[CoverageIssue]:
        """使用 AI 审校覆盖度
        
        Args:
            chapter_contents: 章节内容字典
            requirements: 需求点
            ai_call_func: AI 调用函数
            
        Returns:
            覆盖度问题列表
        """
        # 构建需求文本
        req_lines = []
        req_type_map = {
            'pain_points': '痛点',
            'requirements': '需求',
            'goals': '目标'
        }
        
        all_reqs = []
        for req_type, req_list in requirements.items():
            for req in req_list:
                req_lines.append(f"[{req_type_map.get(req_type, req_type)}] {req}")
                all_reqs.append((req_type, req))
        
        req_text = "\n".join(req_lines)
        
        # 构建内容摘要
        content_summary = "\n\n".join([
            f"【{title}】\n{content[:300]}"
            for title, content in list(chapter_contents.items())[:5]  # 限制章节数
        ])
        
        prompt = f"""请检查以下需求点是否在文档内容中有回应。

【需求点列表】
{req_text}

【文档内容摘要】
{content_summary}

【检查要求】
1. 判断每个需求点是否在文档中有明确回应
2. "回应"指内容直接相关或间接涉及该需求
3. 关注语义相关性，不要求字面匹配

【输出格式】
请以 JSON 格式输出：
{{
  "uncovered": [
    {{
      "requirement": "需求描述",
      "type": "痛点/需求/目标",
      "suggested_chapter": "建议补充的章节"
    }}
  ]
}}

如果没有未覆盖的需求，输出空数组。"""
        
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
                    return []
            
            issues = []
            for item in data.get('uncovered', []):
                issue = CoverageIssue(
                    requirement=item.get('requirement', ''),
                    req_type=item.get('type', ''),
                    suggested_chapter=item.get('suggested_chapter', ''),
                    severity="warning"
                )
                issues.append(issue)
            
            return issues
            
        except Exception as e:
            print(f"[QualityReviewer] AI 覆盖度审校失败: {e}")
            return []
    
    def generate_report(self, chapter_contents: Dict[str, str],
                        data_points: Dict[str, str],
                        requirements: Dict[str, List[str]],
                        ai_call_func=None) -> ReviewReport:
        """生成完整的审校报告
        
        Args:
            chapter_contents: 章节内容字典
            data_points: 数据点
            requirements: 需求点
            ai_call_func: 可选的 AI 调用函数
            
        Returns:
            审校报告
        """
        report = ReviewReport()
        
        # 基本信息
        report.total_chapters = len(chapter_contents)
        report.total_words = sum(len(c) for c in chapter_contents.values())
        
        # 一致性审校
        consistency_issues = self.review_consistency(
            chapter_contents, data_points, ai_call_func
        )
        report.consistency_issues = consistency_issues
        
        # 计算一致性率
        if data_points:
            consistent_count = len(data_points) - len(consistency_issues)
            report.data_consistency_rate = consistent_count / len(data_points)
        else:
            report.data_consistency_rate = 1.0
        
        # 覆盖度审校
        coverage_issues = self.review_coverage(
            chapter_contents, requirements, ai_call_func
        )
        report.coverage_issues = coverage_issues
        
        # 计算覆盖率
        total_reqs = sum(len(v) for v in requirements.values())
        if total_reqs > 0:
            covered_count = total_reqs - len(coverage_issues)
            report.requirement_coverage_rate = covered_count / total_reqs
        else:
            report.requirement_coverage_rate = 1.0
        
        # 综合评分
        report.overall_score = self._calculate_overall_score(report)
        
        # 总体评估
        report.overall_assessment = self._generate_assessment(report)
        
        # 改进建议
        report.improvement_suggestions = self._generate_suggestions(report)
        
        # 保存报告
        self._report = report
        self._review_history.append(report)
        
        return report
    
    def _calculate_overall_score(self, report: ReviewReport) -> float:
        """计算综合评分
        
        基于一致性率和覆盖率计算
        """
        # 权重：一致性 40%，覆盖率 60%
        score = (report.data_consistency_rate * 40 + 
                 report.requirement_coverage_rate * 60)
        
        # 根据问题数量扣分
        consistency_penalty = len(report.consistency_issues) * 5
        coverage_penalty = len(report.coverage_issues) * 3
        
        score = score - consistency_penalty - coverage_penalty
        
        return max(0, min(100, score))
    
    def _generate_assessment(self, report: ReviewReport) -> str:
        """生成总体评估意见"""
        if report.overall_score >= 90:
            return "文档质量优秀，数据一致性良好，需求覆盖完整。"
        elif report.overall_score >= 75:
            return "文档质量良好，存在少量问题需要修正。"
        elif report.overall_score >= 60:
            return "文档质量一般，存在较多问题需要改进。"
        else:
            return "文档质量较差，建议全面检查并修正问题。"
    
    def _generate_suggestions(self, report: ReviewReport) -> List[str]:
        """生成改进建议"""
        suggestions = []
        
        # 基于一致性问题
        if report.consistency_issues:
            suggestions.append("统一全文中的关键数据表述，确保数据一致性。")
        
        # 基于覆盖度问题
        if report.coverage_issues:
            suggestions.append("补充未覆盖的需求点，确保文档完整性。")
        
        # 基于评分
        if report.overall_score < 60:
            suggestions.append("建议重新审阅全文，重点关注数据准确性和需求覆盖度。")
        
        return suggestions
    
    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        stop_words = {'的', '了', '在', '是', '和', '与', '或', '有', '被', '把',
                      '为', '之', '而', '及', '等', '对', '从', '到', '由', '向'}
        
        words = re.findall(r'[\u4e00-\u9fa5]{2,}', text)
        return [w for w in words if w not in stop_words]
    
    def _suggest_chapter_for_requirement(self, requirement: str) -> str:
        """为未覆盖的需求建议补充章节"""
        # 基于关键词匹配
        if any(kw in requirement for kw in ['问题', '困难', '痛点', '现状']):
            return "项目建设的必要性 / 现状分析"
        elif any(kw in requirement for kw in ['建设', '系统', '平台', '功能']):
            return "建设内容 / 技术方案"
        elif any(kw in requirement for kw in ['目标', '效益', '效果']):
            return "项目目标 / 效益分析"
        elif any(kw in requirement for kw in ['风险', '安全']):
            return "风险分析 / 安全保障"
        else:
            return "根据需求类型选择合适的章节"
    
    def get_last_report(self) -> Optional[ReviewReport]:
        """获取最后一次审校报告"""
        return self._report
    
    def get_review_history(self) -> List[ReviewReport]:
        """获取审校历史"""
        return self._review_history.copy()
    
    def clear_history(self) -> None:
        """清空审校历史"""
        self._review_history.clear()
        self._report = None


# 便捷函数
def create_quality_reviewer() -> QualityReviewer:
    """创建质量审校器实例"""
    return QualityReviewer()


# 测试代码
if __name__ == '__main__':
    # 简单测试
    reviewer = QualityReviewer()
    
    # 测试数据
    chapter_contents = {
        "1 项目概况": "项目名称：智慧社区管理平台建设项目，总投资500万元。",
        "2 建设单位": "建设单位：XX科技有限公司。",
        "3 投资估算": "项目总投资约800万元。"  # 数据不一致
    }
    
    data_points = {
        "项目名称": "智慧社区管理平台建设项目",
        "总投资": "500万元",
        "建设单位": "XX科技有限公司"
    }
    
    requirements = {
        'pain_points': ['监控设备老化'],
        'requirements': ['建设高清监控系统'],
        'goals': ['提升社区安全水平']
    }
    
    # 生成报告
    report = reviewer.generate_report(chapter_contents, data_points, requirements)
    
    print("审校报告：")
    print(f"综合评分: {report.overall_score}")
    print(f"一致性率: {report.data_consistency_rate:.1%}")
    print(f"覆盖率: {report.requirement_coverage_rate:.1%}")
    print("\n一致性问题:")
    for issue in report.consistency_issues:
        print(f"  - {issue}")
    print("\n覆盖度问题:")
    for issue in report.coverage_issues:
        print(f"  - {issue}")
