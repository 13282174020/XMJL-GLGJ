# -*- coding: utf-8 -*-
"""
Word 文档 AI 生成模块 - 服务层

包含三个核心服务：
1. ContentOptimizer - 章节类型识别、Few-shot 示例
2. RequirementAnalyzer - 需求点提取与映射
3. DataPointManager - 数据点一致性管理
"""

from .content_optimizer import ContentOptimizer, FEW_SHOT_EXAMPLES, CHAPTER_TYPE_MAP
from .requirement_analyzer import RequirementAnalyzer, CHAPTER_REQUIREMENT_MAP
from .data_point_manager import DataPointManager

__all__ = [
    'ContentOptimizer',
    'RequirementAnalyzer',
    'DataPointManager',
    'FEW_SHOT_EXAMPLES',
    'CHAPTER_TYPE_MAP',
    'CHAPTER_REQUIREMENT_MAP',
]
