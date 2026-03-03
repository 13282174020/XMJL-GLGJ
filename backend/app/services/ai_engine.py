# -*- coding: utf-8 -*-
"""
AI 引擎服务 - 核心 AI 生成逻辑
整合 LLM 适配器、Prompt 管理、数据点管理
"""

import json
from typing import Dict, Any, List, Optional
from .llm_adapter import get_llm_adapter, BaseLLMAdapter
from .prompt_manager import render_prompt
from .data_point_manager import DataPointManager


class AIEngine:
    """AI 引擎类"""
    
    def __init__(self, api_key: str, model: str = 'qwen-max'):
        """初始化 AI 引擎
        
        Args:
            api_key: LLM API Key
            model: 模型名称
        """
        self.api_key = api_key
        self.model = model
        self.adapter: BaseLLMAdapter = get_llm_adapter(model, api_key)
        self.data_point_manager = DataPointManager()
        self.token_usage = 0
    
    def extract_requirements(self, document_text: str) -> Dict[str, Any]:
        """阶段一：从需求文档中提取结构化信息
        
        Args:
            document_text: 需求文档文本
            
        Returns:
            提取的结构化信息
        """
        prompt = render_prompt(
            'extract_requirements',
            document_text=document_text
        )
        
        result = self.adapter.call_with_json(prompt)
        return result
    
    def analyze_template(self, document_text: str) -> Dict[str, Any]:
        """阶段二：分析模板文档的章节结构
        
        Args:
            document_text: 模板文档文本
            
        Returns:
            章节结构树
        """
        prompt = render_prompt(
            'analyze_template',
            document_text=document_text
        )
        
        result = self.adapter.call_with_json(prompt)
        return result
    
    def generate_chapter(
        self,
        project_context: Dict[str, Any],
        chapter: Dict[str, Any],
        user_instruction: str = '',
        prev_summary: str = '',
        example: str = ''
    ) -> Dict[str, Any]:
        """阶段三：生成单个章节内容
        
        Args:
            project_context: 项目上下文信息
            chapter: 当前章节要求
            user_instruction: 用户补充要求
            prev_summary: 前文摘要
            example: Few-shot 示例
            
        Returns:
            生成的章节内容 JSON
        """
        prompt = render_prompt(
            'generate_chapter',
            project_context=project_context,
            chapter=chapter,
            data_points=self.data_point_manager.get_all(),
            user_instruction=user_instruction,
            prev_summary=prev_summary,
            example=example
        )
        
        result = self.adapter.call_with_json(prompt)
        
        # 提取并更新数据点
        if 'subsections' in result:
            chapter_text = json.dumps(result, ensure_ascii=False)
            new_points = self.data_point_manager.extract_from_text(chapter_text)
            self.data_point_manager.update(new_points)
        
        return result
    
    def review_consistency(self, chapter_content: str) -> Dict[str, Any]:
        """阶段四：数据一致性审校
        
        Args:
            chapter_content: 章节内容
            
        Returns:
            审校结果
        """
        prompt = render_prompt(
            'review_consistency',
            data_points=self.data_point_manager.get_all(),
            chapter_content=chapter_content
        )
        
        result = self.adapter.call_with_json(prompt)
        return result
    
    def review_coverage(
        self,
        requirements: List[str],
        generated_content_summary: str
    ) -> Dict[str, Any]:
        """阶段四：需求覆盖度审校
        
        Args:
            requirements: 需求列表
            generated_content_summary: 生成内容摘要
            
        Returns:
            审校结果
        """
        prompt = render_prompt(
            'review_coverage',
            requirements=requirements,
            generated_content_summary=generated_content_summary
        )
        
        result = self.adapter.call_with_json(prompt)
        return result
    
    def review_quality(self, chapter_content: str) -> Dict[str, Any]:
        """阶段四：整体质量审校
        
        Args:
            chapter_content: 章节内容
            
        Returns:
            审校结果
        """
        prompt = render_prompt(
            'review_quality',
            chapter_content=chapter_content
        )
        
        result = self.adapter.call_with_json(prompt)
        return result
    
    def extract_data_points(self, text: str) -> Dict[str, str]:
        """从文本中提取数据点
        
        Args:
            text: 文本内容
            
        Returns:
            数据点字典
        """
        return self.data_point_manager.extract_from_text(text)
    
    def get_data_points(self) -> Dict[str, Any]:
        """获取当前数据点字典
        
        Returns:
            数据点字典
        """
        return self.data_point_manager.get_all()
    
    def clear_data_points(self) -> None:
        """清空数据点"""
        self.data_point_manager.clear()
    
    def summarize_text(self, text: str, max_length: int = 500) -> str:
        """生成文本摘要
        
        Args:
            text: 原文本
            max_length: 最大长度
            
        Returns:
            摘要文本
        """
        prompt = f"请用{max_length}字以内概括以下内容的核心要点：\n\n{text[:3000]}"
        summary = self.adapter.call(prompt, max_tokens=min(max_length, 500))
        return summary
    
    def set_model(self, model: str) -> None:
        """切换模型
        
        Args:
            model: 新模型名称
        """
        self.model = model
        self.adapter = get_llm_adapter(model, self.api_key)
    
    def get_token_usage(self) -> int:
        """获取 Token 使用量
        
        Returns:
            Token 数量
        """
        return self.token_usage


def create_ai_engine(api_key: str, model: str = 'qwen-max') -> AIEngine:
    """创建 AI 引擎实例的便捷函数"""
    return AIEngine(api_key, model)


if __name__ == '__main__':
    # 测试代码
    import os
    
    api_key = os.environ.get('LLM_API_KEY', '')
    if not api_key:
        print("请设置环境变量 LLM_API_KEY")
    else:
        engine = create_ai_engine(api_key)
        print("AI 引擎初始化成功")
        print(f"当前模型：{engine.model}")
