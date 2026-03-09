# -*- coding: utf-8 -*-
"""
Services 模块 - AI 内容优化服务
包含：
- data_point_manager: 数据点管理（数据一致性）
- requirement_analyzer: 需求分析（需求覆盖度）
- quality_reviewer: 质量审校（全文审校）
- content_optimizer: 内容优化（Few-shot 示例、章节类型识别、内容去重）
"""

from .data_point_manager import DataPointManager
from .requirement_analyzer import RequirementAnalyzer
from .quality_reviewer import QualityReviewer
from .content_optimizer import ContentOptimizer

__all__ = ['DataPointManager', 'RequirementAnalyzer', 'QualityReviewer', 'ContentOptimizer']
