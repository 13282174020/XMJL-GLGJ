# -*- coding: utf-8 -*-
"""
LLM 适配器服务 - 支持多种大模型 API 调用
"""

import os
import json
import requests
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod


class BaseLLMAdapter(ABC):
    """LLM 适配器基类"""
    
    @abstractmethod
    def call(self, prompt: str, **kwargs) -> str:
        """调用 LLM API
        
        Args:
            prompt: 提示词
            **kwargs: 其他参数
            
        Returns:
            LLM 响应文本
        """
        pass
    
    @abstractmethod
    def call_with_json(self, prompt: str, schema: Optional[Dict] = None, **kwargs) -> Dict:
        """调用 LLM API 并解析 JSON 响应
        
        Args:
            prompt: 提示词
            schema: JSON Schema（可选）
            **kwargs: 其他参数
            
        Returns:
            解析后的 JSON 数据
        """
        pass


class QwenLLMAdapter(BaseLLMAdapter):
    """通义千问 LLM 适配器"""
    
    def __init__(self, api_key: str, model: str = 'qwen-max'):
        self.api_key = api_key
        self.model = model
        self.base_url = 'https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation'
    
    def call(self, prompt: str, **kwargs) -> str:
        """调用通义千问 API"""
        max_tokens = kwargs.get('max_tokens', 4000)
        temperature = kwargs.get('temperature', 0.7)
        timeout = kwargs.get('timeout', 120)
        
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'model': self.model,
            'input': {
                'messages': [
                    {'role': 'user', 'content': prompt}
                ]
            },
            'parameters': {
                'max_tokens': max_tokens,
                'temperature': temperature,
                'top_p': 0.8
            }
        }
        
        try:
            response = requests.post(self.base_url, headers=headers, json=payload, timeout=timeout)
            
            if response.status_code == 200:
                result = response.json()
                if 'output' in result and 'text' in result['output']:
                    return result['output']['text']
                elif 'output' in result and 'choices' in result['output']:
                    return result['output']['choices'][0]['message']['content']
                else:
                    return f"API 返回格式异常：{result}"
            else:
                return f"API 调用失败 (状态码 {response.status_code}): {response.text}"
                
        except requests.exceptions.Timeout:
            return "API 调用超时，请重试"
        except Exception as e:
            return f"API 调用异常：{str(e)}"
    
    def call_with_json(self, prompt: str, schema: Optional[Dict] = None, **kwargs) -> Dict:
        """调用并解析 JSON 响应"""
        # 在 prompt 中强调 JSON 输出
        json_prompt = prompt + "\n\n【重要】请严格按 JSON 格式输出，不要包含任何其他内容。"
        
        response_text = self.call(json_prompt, **kwargs)
        
        # 尝试提取 JSON
        json_data = self._extract_json(response_text)
        if json_data:
            return json_data
        
        raise ValueError(f"无法解析 LLM 响应为 JSON: {response_text[:500]}")
    
    def _extract_json(self, text: str) -> Optional[Dict]:
        """从文本中提取 JSON 数据"""
        import re
        
        # 尝试直接解析
        try:
            return json.loads(text)
        except:
            pass
        
        # 尝试提取 ```json 块
        match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except:
                pass
        
        # 尝试提取第一个 { 到最后一个 }
        start = text.find('{')
        end = text.rfind('}') + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except:
                pass
        
        return None


class GPTLLMAdapter(BaseLLMAdapter):
    """GPT LLM 适配器"""
    
    def __init__(self, api_key: str, model: str = 'gpt-4o'):
        self.api_key = api_key
        self.model = model
        self.base_url = 'https://api.openai.com/v1/chat/completions'
    
    def call(self, prompt: str, **kwargs) -> str:
        """调用 GPT API"""
        max_tokens = kwargs.get('max_tokens', 4000)
        temperature = kwargs.get('temperature', 0.7)
        timeout = kwargs.get('timeout', 120)
        
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'model': self.model,
            'messages': [
                {'role': 'user', 'content': prompt}
            ],
            'max_tokens': max_tokens,
            'temperature': temperature
        }
        
        try:
            response = requests.post(self.base_url, headers=headers, json=payload, timeout=timeout)
            
            if response.status_code == 200:
                result = response.json()
                if 'choices' in result and len(result['choices']) > 0:
                    return result['choices'][0]['message']['content']
                else:
                    return f"API 返回格式异常：{result}"
            else:
                return f"API 调用失败 (状态码 {response.status_code}): {response.text}"
                
        except requests.exceptions.Timeout:
            return "API 调用超时，请重试"
        except Exception as e:
            return f"API 调用异常：{str(e)}"
    
    def call_with_json(self, prompt: str, schema: Optional[Dict] = None, **kwargs) -> Dict:
        """调用并解析 JSON 响应"""
        if schema:
            # 使用 GPT 的 response_format 参数
            kwargs['response_format'] = {'type': 'json_object'}
        
        response_text = self.call(prompt, **kwargs)
        
        json_data = self._extract_json(response_text)
        if json_data:
            return json_data
        
        raise ValueError(f"无法解析 LLM 响应为 JSON: {response_text[:500]}")
    
    def _extract_json(self, text: str) -> Optional[Dict]:
        """从文本中提取 JSON 数据"""
        import re
        import json
        
        try:
            return json.loads(text)
        except:
            pass
        
        match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except:
                pass
        
        start = text.find('{')
        end = text.rfind('}') + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except:
                pass
        
        return None


class LLMAdapterFactory:
    """LLM 适配器工厂类"""
    
    _adapters = {
        'qwen': QwenLLMAdapter,
        'qwen-max': QwenLLMAdapter,
        'qwen-plus': QwenLLMAdapter,
        'qwen-turbo': QwenLLMAdapter,
        'gpt': GPTLLMAdapter,
        'gpt-4o': GPTLLMAdapter,
        'gpt-4': GPTLLMAdapter,
    }
    
    @classmethod
    def create(cls, model: str, api_key: str) -> BaseLLMAdapter:
        """创建 LLM 适配器
        
        Args:
            model: 模型名称
            api_key: API Key
            
        Returns:
            LLM 适配器实例
        """
        model_lower = model.lower()
        
        # 通义千问系列
        if model_lower.startswith('qwen'):
            return QwenLLMAdapter(api_key, model)
        
        # GPT 系列
        if model_lower.startswith('gpt'):
            return GPTLLMAdapter(api_key, model)
        
        # 默认使用通义千问
        return QwenLLMAdapter(api_key, model)


def get_llm_adapter(model: str, api_key: str) -> BaseLLMAdapter:
    """获取 LLM 适配器的便捷函数"""
    return LLMAdapterFactory.create(model, api_key)


if __name__ == '__main__':
    # 测试代码
    import sys
    
    api_key = os.environ.get('LLM_API_KEY', '')
    if not api_key:
        print("请设置环境变量 LLM_API_KEY")
        sys.exit(1)
    
    adapter = get_llm_adapter('qwen-max', api_key)
    response = adapter.call("你好，请做个自我介绍")
    print(response)
