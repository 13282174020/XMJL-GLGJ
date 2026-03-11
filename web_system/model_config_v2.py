# -*- coding: utf-8 -*-
"""
模型配置管理模块 v2.0
支持：
1. 按厂商分类（千问、GLM、Kimi、DeepSeek 等）
2. 自定义添加厂商
3. 每个厂商下支持多个子模型（文本推理、PPT 生成、视频生成等）
4. 预设主流厂商和模型配置
"""

import json
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum

# 配置文件路径
CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'model_configs_v2.json')


class ModelType(Enum):
    """模型类型"""
    TEXT = "text"                    # 文本推理
    IMAGE = "image"                  # 图像生成
    VIDEO = "video"                  # 视频生成
    AUDIO = "audio"                  # 音频生成
    PPT = "ppt"                      # PPT 生成
    CODE = "code"                    # 代码生成
    EMBEDDING = "embedding"          # 嵌入模型
    RERANK = "rerank"               # 重排序模型
    CUSTOM = "custom"                # 自定义


# 预设厂商配置
PRESET_PROVIDERS = {
    "dashscope": {
        "name": "阿里云百炼",
        "icon": "🌐",
        "base_url": "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
        "models": [
            {
                "id": "qwen-max",
                "name": "Qwen-Max",
                "type": "text",
                "model": "qwen-max",
                "max_tokens": 2000,
                "temperature": 0.7,
                "description": "通义千问最强模型"
            },
            {
                "id": "qwen-plus",
                "name": "Qwen-Plus",
                "type": "text",
                "model": "qwen-plus",
                "max_tokens": 2000,
                "temperature": 0.7,
                "description": "通义千问增强模型"
            },
            {
                "id": "qwen-turbo",
                "name": "Qwen-Turbo",
                "type": "text",
                "model": "qwen-turbo",
                "max_tokens": 2000,
                "temperature": 0.7,
                "description": "通义千问快速模型"
            },
            {
                "id": "qwen-vl-max",
                "name": "Qwen-VL-Max",
                "type": "image",
                "model": "qwen-vl-max",
                "max_tokens": 2000,
                "temperature": 0.7,
                "description": "通义千问视觉模型"
            }
        ]
    },
    "zhipu": {
        "name": "智谱 AI",
        "icon": "🧠",
        "base_url": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        "models": [
            {
                "id": "glm-4",
                "name": "GLM-4",
                "type": "text",
                "model": "glm-4",
                "max_tokens": 2000,
                "temperature": 0.7,
                "description": "智谱 AI 最新大模型"
            },
            {
                "id": "glm-4-flash",
                "name": "GLM-4-Flash",
                "type": "text",
                "model": "glm-4-flash",
                "max_tokens": 2000,
                "temperature": 0.7,
                "description": "GLM-4 快速版本"
            },
            {
                "id": "glm-4v",
                "name": "GLM-4V",
                "type": "image",
                "model": "glm-4v",
                "max_tokens": 2000,
                "temperature": 0.7,
                "description": "GLM-4 视觉模型"
            },
            {
                "id": "cogview-3",
                "name": "CogView-3",
                "type": "image",
                "model": "cogview-3",
                "max_tokens": 2000,
                "temperature": 0.7,
                "description": "智谱 AI 文生图模型"
            }
        ]
    },
    "moonshot": {
        "name": "月之暗面 (Kimi)",
        "icon": "🌙",
        "base_url": "https://api.moonshot.cn/v1/chat/completions",
        "models": [
            {
                "id": "kimi-latest",
                "name": "Kimi",
                "type": "text",
                "model": "kimi-latest",
                "max_tokens": 2000,
                "temperature": 0.7,
                "description": "Kimi 长文本模型"
            },
            {
                "id": "kimi-k2",
                "name": "Kimi-K2",
                "type": "text",
                "model": "kimi-k2",
                "max_tokens": 2000,
                "temperature": 0.7,
                "description": "Kimi 最新 K2 模型"
            }
        ]
    },
    "deepseek": {
        "name": "深度求索 (DeepSeek)",
        "icon": "🔬",
        "base_url": "https://api.deepseek.com/chat/completions",
        "models": [
            {
                "id": "deepseek-chat",
                "name": "DeepSeek Chat",
                "type": "text",
                "model": "deepseek-chat",
                "max_tokens": 2000,
                "temperature": 0.7,
                "description": "DeepSeek 对话模型"
            },
            {
                "id": "deepseek-coder",
                "name": "DeepSeek Coder",
                "type": "code",
                "model": "deepseek-coder",
                "max_tokens": 2000,
                "temperature": 0.7,
                "description": "DeepSeek 代码模型"
            },
            {
                "id": "deepseek-r1",
                "name": "DeepSeek R1",
                "type": "text",
                "model": "deepseek-reasoner",
                "max_tokens": 8000,
                "temperature": 0.6,
                "description": "DeepSeek R1 推理模型"
            },
            {
                "id": "deepseek-v2.5",
                "name": "DeepSeek V2.5",
                "type": "text",
                "model": "deepseek-v2.5",
                "max_tokens": 4000,
                "temperature": 0.7,
                "description": "DeepSeek V2.5 最新版本"
            }
        ]
    },
    "minimax": {
        "name": "MiniMax",
        "icon": "🤖",
        "base_url": "https://api.minimax.chat/v1/text/chatcompletion_v2",
        "models": [
            {
                "id": "abab6.5-chat",
                "name": "Abab6.5",
                "type": "text",
                "model": "abab6.5-chat",
                "max_tokens": 2000,
                "temperature": 0.7,
                "description": "MiniMax 通用大模型"
            },
            {
                "id": "video-01",
                "name": "Video-01",
                "type": "video",
                "model": "video-01",
                "max_tokens": 2000,
                "temperature": 0.7,
                "description": "MiniMax 视频生成模型"
            }
        ]
    },
    "openai": {
        "name": "OpenAI",
        "icon": "🟢",
        "base_url": "https://api.openai.com/v1/chat/completions",
        "models": [
            {
                "id": "gpt-4o",
                "name": "GPT-4o",
                "type": "text",
                "model": "gpt-4o",
                "max_tokens": 2000,
                "temperature": 0.7,
                "description": "OpenAI 最新旗舰模型"
            },
            {
                "id": "gpt-4-turbo",
                "name": "GPT-4 Turbo",
                "type": "text",
                "model": "gpt-4-turbo",
                "max_tokens": 2000,
                "temperature": 0.7,
                "description": "GPT-4 快速版本"
            },
            {
                "id": "gpt-3.5-turbo",
                "name": "GPT-3.5 Turbo",
                "type": "text",
                "model": "gpt-3.5-turbo",
                "max_tokens": 2000,
                "temperature": 0.7,
                "description": "GPT-3.5 快速版本"
            },
            {
                "id": "dall-e-3",
                "name": "DALL-E 3",
                "type": "image",
                "model": "dall-e-3",
                "max_tokens": 2000,
                "temperature": 0.7,
                "description": "OpenAI 文生图模型"
            }
        ]
    },
    "openrouter": {
        "name": "OpenRouter",
        "icon": "🌉",
        "base_url": "https://openrouter.ai/api/v1/chat/completions",
        "models": [
            {
                "id": "openrouter-auto",
                "name": "OpenRouter Auto",
                "type": "text",
                "model": "openrouter/auto",
                "max_tokens": 2000,
                "temperature": 0.7,
                "description": "OpenRouter 自动选择模型"
            },
            {
                "id": "openrouter-deepseek-r1",
                "name": "DeepSeek R1 (via OpenRouter)",
                "type": "text",
                "model": "deepseek/deepseek-r1",
                "max_tokens": 8000,
                "temperature": 0.6,
                "description": "通过 OpenRouter 调用 DeepSeek R1"
            }
        ]
    },
    "ollama": {
        "name": "Ollama (本地)",
        "icon": "🦙",
        "base_url": "http://localhost:11434/api/chat",
        "models": [
            {
                "id": "ollama-glm-4-7-flash-q4",
                "name": "GLM-4.7-Flash-Q4 (Ollama)",
                "type": "text",
                "model": "modelscope.cn/unsloth/GLM-4.7-Flash-GGUF:Q4_K_M",
                "max_tokens": 2000,
                "temperature": 0.7,
                "description": "Ollama 本地部署的 GLM-4.7-Flash Q4_K_M 量化模型"
            },
            {
                "id": "ollama-glm-4-flash",
                "name": "GLM-4-Flash (Ollama)",
                "type": "text",
                "model": "glm-4-flash",
                "max_tokens": 2000,
                "temperature": 0.7,
                "description": "Ollama 本地部署的 GLM-4-Flash 模型"
            },
            {
                "id": "ollama-glm-4-flash-q4",
                "name": "GLM-4-Flash-Q4 (Ollama)",
                "type": "text",
                "model": "glm-4-flash-q4",
                "max_tokens": 2000,
                "temperature": 0.7,
                "description": "Ollama 本地部署的 GLM-4-Flash Q4 量化模型"
            },
            {
                "id": "ollama-qwen2.5",
                "name": "Qwen2.5 (Ollama)",
                "type": "text",
                "model": "qwen2.5",
                "max_tokens": 2000,
                "temperature": 0.7,
                "description": "Ollama 本地部署的 Qwen2.5 模型"
            },
            {
                "id": "ollama-deepseek-r1-14b",
                "name": "DeepSeek-R1-14B (Ollama)",
                "type": "text",
                "model": "modelscope.cn/unsloth/DeepSeek-R1-Distill-Qwen-14B-GGUF:Q4_K_M",
                "max_tokens": 4000,
                "temperature": 0.7,
                "description": "Ollama 本地部署的 DeepSeek-R1-Distill-Qwen-14B-GGUF Q4_K_M 量化模型"
            },
            {
                "id": "ollama-deepseek-r1-14b-q6",
                "name": "DeepSeek-R1-14B-Q6_K (Ollama)",
                "type": "text",
                "model": "modelscope.cn/unsloth/DeepSeek-R1-Distill-Qwen-14B-GGUF:Q6_K",
                "max_tokens": 4000,
                "temperature": 0.7,
                "description": "Ollama 本地部署的 DeepSeek-R1-Distill-Qwen-14B-GGUF Q6_K 量化模型（更高精度）"
            },
            {
                "id": "ollama-qwen2.5-14b-instruct",
                "name": "Qwen2.5-14B-Instruct (Ollama)",
                "type": "text",
                "model": "modelscope.cn/Qwen/Qwen2.5-14B-Instruct-GGUF:Q6_K",
                "max_tokens": 4000,
                "temperature": 0.5,
                "description": "Ollama 本地部署的通义千问 2.5-14B 指令微调模型 Q6_K 量化版本"
            },
            {
                "id": "ollama-qwen3-14b-instruct",
                "name": "Qwen3-14B-Instruct (Ollama)",
                "type": "text",
                "model": "modelscope.cn/mradermacher/Ophiuchi-Qwen3-14B-Instruct-i1-GGUF:i1-Q6_K",
                "max_tokens": 4000,
                "temperature": 0.5,
                "description": "Ollama 本地部署的 Ophiuchi-Qwen3-14B-Instruct i1-Q6_K 量化版本"
            },
            {
                "id": "ollama-llama3",
                "name": "Llama3 (Ollama)",
                "type": "text",
                "model": "llama3",
                "max_tokens": 2000,
                "temperature": 0.7,
                "description": "Ollama 本地部署的 Llama3 模型"
            }
        ]
    }
}


@dataclass
class ModelConfig:
    """模型配置"""
    id: str                              # 配置 ID（全局唯一）
    provider_id: str                     # 所属厂商 ID
    name: str                            # 显示名称
    type: str                            # 模型类型
    model: str                           # 模型名称
    api_key: str = ""                    # API Key
    base_url: str = ""                   # API 基础 URL
    max_tokens: int = 2000               # 最大 token 数
    temperature: float = 0.7             # 温度参数
    timeout: int = 120                   # 超时时间（秒）
    enabled: bool = False                # 是否启用（默认关闭）
    description: str = ""                # 描述
    headers: Dict[str, str] = field(default_factory=dict)  # 自定义请求头
    request_format: str = "openai"       # 请求格式
    response_path: str = "choices.0.message.content"  # 响应内容提取路径
    is_custom: bool = False              # 是否自定义模型
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ModelConfig':
        return cls(**data)


@dataclass
class ProviderConfig:
    """厂商配置"""
    id: str                              # 厂商 ID
    name: str                            # 厂商名称
    icon: str                            # 图标 emoji
    base_url: str                        # 默认 API 基础 URL
    models: List[ModelConfig] = field(default_factory=list)  # 模型列表
    is_custom: bool = False              # 是否自定义厂商
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        data['models'] = [m.to_dict() if isinstance(m, ModelConfig) else m for m in self.models]
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ProviderConfig':
        models_data = data.pop('models', [])
        models = [ModelConfig.from_dict(m) if isinstance(m, dict) else m for m in models_data]
        return cls(**data, models=models)


class ModelConfigManagerV2:
    """模型配置管理器 v2"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self.providers: Dict[str, ProviderConfig] = {}
            self._load_configs()
    
    def _load_configs(self):
        """加载配置"""
        # 先加载预设配置
        for provider_id, provider_data in PRESET_PROVIDERS.items():
            models = []
            for model_data in provider_data['models']:
                # 根据提供商确定请求格式
                if provider_id == 'dashscope':
                    request_format = 'dashscope'
                    response_path = 'output.text'
                elif provider_id == 'ollama':
                    request_format = 'ollama'
                    response_path = 'message.content'
                else:
                    request_format = 'openai'
                    response_path = 'choices.0.message.content'
                
                model = ModelConfig(
                    id=model_data['id'],
                    provider_id=provider_id,
                    name=model_data['name'],
                    type=model_data['type'],
                    model=model_data['model'],
                    max_tokens=model_data['max_tokens'],
                    temperature=model_data['temperature'],
                    description=model_data['description'],
                    base_url=provider_data.get('base_url', ''),  # 使用厂商的 base_url
                    request_format=request_format,
                    response_path=response_path
                )
                models.append(model)
            
            provider = ProviderConfig(
                id=provider_id,
                name=provider_data['name'],
                icon=provider_data['icon'],
                base_url=provider_data['base_url'],
                models=models
            )
            self.providers[provider_id] = provider
        
        # 加载用户自定义配置（覆盖预设）
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for provider_id, provider_data in data.items():
                        if provider_id in self.providers:
                            # 合并现有厂商的配置
                            existing_provider = self.providers[provider_id]
                            for model_data in provider_data.get('models', []):
                                # 检查是否是自定义模型
                                if model_data.get('is_custom', False):
                                    model = ModelConfig.from_dict(model_data)
                                    existing_provider.models.append(model)
                                else:
                                    # 更新现有模型配置（如 API Key）
                                    for existing_model in existing_provider.models:
                                        if existing_model.id == model_data['id']:
                                            if model_data.get('api_key'):
                                                existing_model.api_key = model_data['api_key']
                                            if model_data.get('enabled') is not None:
                                                existing_model.enabled = model_data['enabled']
                        else:
                            # 添加自定义厂商
                            provider = ProviderConfig.from_dict(provider_data)
                            provider.is_custom = True
                            self.providers[provider_id] = provider
                
                print(f'[INFO] 已加载 {len(self.providers)} 个厂商配置')
            except Exception as e:
                print(f'[ERROR] 加载模型配置失败：{e}')
    
    def save_configs(self) -> bool:
        """保存配置到文件（只保存用户自定义部分）"""
        try:
            data = {}
            for provider_id, provider in self.providers.items():
                # 只保存自定义厂商或包含自定义模型的厂商
                custom_models = [m for m in provider.models if m.is_custom]
                if provider.is_custom or custom_models:
                    provider_data = provider.to_dict()
                    # 只保留自定义模型
                    provider_data['models'] = [m.to_dict() for m in provider.models if m.is_custom or m.api_key or not m.enabled]
                    data[provider_id] = provider_data
            
            os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f'[INFO] 已保存 {len(data)} 个厂商配置')
            return True
        except Exception as e:
            print(f'[ERROR] 保存模型配置失败：{e}')
            return False
    
    def get_provider(self, provider_id: str) -> Optional[ProviderConfig]:
        """获取厂商配置"""
        return self.providers.get(provider_id)
    
    def get_all_providers(self) -> Dict[str, ProviderConfig]:
        """获取所有厂商"""
        return self.providers.copy()
    
    def get_model(self, model_id: str) -> Optional[ModelConfig]:
        """获取模型配置"""
        for provider in self.providers.values():
            for model in provider.models:
                if model.id == model_id:
                    return model
        return None
    
    def add_custom_provider(self, provider: ProviderConfig) -> bool:
        """添加自定义厂商"""
        if provider.id in self.providers:
            return False
        provider.is_custom = True
        self.providers[provider.id] = provider
        return self.save_configs()
    
    def add_custom_model(self, provider_id: str, model: ModelConfig) -> bool:
        """添加自定义模型到指定厂商"""
        if provider_id not in self.providers:
            return False
        model.is_custom = True
        model.provider_id = provider_id
        self.providers[provider_id].models.append(model)
        return self.save_configs()
    
    def update_model_config(self, model_id: str, **kwargs) -> bool:
        """更新模型配置"""
        model = self.get_model(model_id)
        if not model:
            return False
        for key, value in kwargs.items():
            if hasattr(model, key):
                setattr(model, key, value)
        return self.save_configs()
    
    def delete_custom_model(self, model_id: str) -> bool:
        """删除自定义模型"""
        for provider in self.providers.values():
            for i, model in enumerate(provider.models):
                if model.id == model_id and model.is_custom:
                    provider.models.pop(i)
                    return self.save_configs()
        return False
    
    def get_enabled_models(self, model_type: Optional[str] = None) -> List[Dict]:
        """获取启用的模型列表"""
        result = []
        for provider in self.providers.values():
            for model in provider.models:
                if model.enabled and (model_type is None or model.type == model_type):
                    result.append({
                        'id': model.id,
                        'provider_id': provider.id,
                        'provider_name': provider.name,
                        'provider_icon': provider.icon,
                        'name': model.name,
                        'type': model.type,
                        'model': model.model,
                        'description': model.description,
                        'has_api_key': bool(model.api_key)
                    })
        return result
    
    def get_models_by_provider(self, provider_id: str) -> List[Dict]:
        """获取指定厂商的所有模型"""
        provider = self.get_provider(provider_id)
        if not provider:
            return []
        
        return [
            {
                'id': model.id,
                'name': model.name,
                'type': model.type,
                'model': model.model,
                'api_key': model.api_key,
                'enabled': model.enabled,
                'description': model.description,
                'is_custom': model.is_custom
            }
            for model in provider.models
        ]
    
    def get_model_types(self) -> List[Dict]:
        """获取所有模型类型"""
        type_map = {
            'text': '文本推理',
            'image': '图像生成',
            'video': '视频生成',
            'audio': '音频生成',
            'ppt': 'PPT 生成',
            'code': '代码生成',
            'embedding': '嵌入模型',
            'rerank': '重排序模型',
            'custom': '自定义'
        }
        return [{'id': k, 'name': v} for k, v in type_map.items()]


# 全局实例
_model_config_manager_v2: Optional[ModelConfigManagerV2] = None


def get_model_config_manager_v2() -> ModelConfigManagerV2:
    """获取模型配置管理器实例"""
    global _model_config_manager_v2
    if _model_config_manager_v2 is None:
        _model_config_manager_v2 = ModelConfigManagerV2()
    return _model_config_manager_v2


def get_model_config_v2(model_id: str):
    """获取模型配置（用于生成文档时）"""
    manager = get_model_config_manager_v2()
    return manager.get_model(model_id)


# 测试代码
if __name__ == '__main__':
    manager = get_model_config_manager_v2()
    
    print("="*60)
    print("模型配置管理 v2.0")
    print("="*60)
    
    print(f"\n共加载 {len(manager.providers)} 个厂商配置\n")
    
    for provider_id, provider in manager.providers.items():
        print(f"{provider.icon} {provider.name} ({provider_id})")
        print(f"   基础 URL: {provider.base_url}")
        print(f"   模型数量：{len(provider.models)}")
        for model in provider.models:
            status = "✓" if model.enabled else "✗"
            key_status = "🔑" if model.api_key else "⚠️"
            print(f"     {status} {key_status} {model.name} ({model.type}) - {model.description}")
        print()
