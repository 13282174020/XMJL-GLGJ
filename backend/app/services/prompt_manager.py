# -*- coding: utf-8 -*-
"""
Prompt 管理服务 - SKILL-009
管理所有 LLM 使用的 Prompt 模板
"""

import os
from typing import Dict, Any, Optional
from jinja2 import Environment, FileSystemLoader, BaseLoader


class PromptManager:
    """Prompt 管理器类"""
    
    def __init__(self, template_dir: Optional[str] = None):
        """初始化 Prompt 管理器
        
        Args:
            template_dir: Prompt 模板目录路径
        """
        if template_dir is None:
            template_dir = os.path.join(os.path.dirname(__file__), 'prompts')
        
        self.template_dir = template_dir
        self.env = Environment(loader=FileSystemLoader(template_dir))
        self._cache = {}
    
    def get_template(self, name: str) -> Optional[str]:
        """获取 Prompt 模板内容
        
        Args:
            name: 模板名称（不含.j2 后缀）
            
        Returns:
            模板内容字符串
        """
        if name in self._cache:
            return self._cache[name]
        
        template_path = os.path.join(self.template_dir, f"{name}.j2")
        if not os.path.exists(template_path):
            return None
        
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self._cache[name] = content
            return content
    
    def render(self, name: str, **kwargs) -> str:
        """渲染 Prompt 模板
        
        Args:
            name: 模板名称
            **kwargs: 模板变量
            
        Returns:
            渲染后的 Prompt
        """
        try:
            template = self.env.get_template(f"{name}.j2")
            return template.render(**kwargs)
        except Exception as e:
            raise Exception(f"渲染 Prompt 模板失败 [{name}]: {str(e)}")
    
    def render_from_string(self, template_str: str, **kwargs) -> str:
        """从字符串渲染 Prompt
        
        Args:
            template_str: 模板字符串
            **kwargs: 模板变量
            
        Returns:
            渲染后的 Prompt
        """
        template = Environment(loader=BaseLoader).from_string(template_str)
        return template.render(**kwargs)
    
    def list_templates(self) -> list:
        """列出所有可用的模板
        
        Returns:
            模板名称列表
        """
        templates = []
        if os.path.exists(self.template_dir):
            for f in os.listdir(self.template_dir):
                if f.endswith('.j2'):
                    templates.append(f[:-3])  # 去掉.j2 后缀
        return templates
    
    def reload(self) -> None:
        """重新加载所有模板（清除缓存）"""
        self._cache.clear()
        self.env = Environment(loader=FileSystemLoader(self.template_dir))


# 全局 Prompt 管理器实例
prompt_manager = PromptManager()


def get_prompt(name: str) -> Optional[str]:
    """获取 Prompt 模板的便捷函数"""
    return prompt_manager.get_template(name)


def render_prompt(name: str, **kwargs) -> str:
    """渲染 Prompt 模板的便捷函数"""
    return prompt_manager.render(name, **kwargs)


if __name__ == '__main__':
    # 测试代码
    print("可用的 Prompt 模板:")
    for t in prompt_manager.list_templates():
        print(f"  - {t}")
