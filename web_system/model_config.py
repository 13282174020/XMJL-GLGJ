# -*- coding: utf-8 -*-
"""
模型配置管理模块
支持多个 AI 模型的配置和管理
"""

import json
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum

# 配置文件路径
CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'model_configs.json')


class ModelProvider(Enum):
    """模型提供商"""
    DASHSCOPE = "dashscope"      # 阿里云百炼
    ZHIPU = "zhipu"              # 智谱 AI
    MOONSHOT = "moonshot"        # 月之暗面 (Kimi)
    MINIMAX = "minimax"          # MiniMax
    OPENAI = "openai"            # OpenAI
    DEEPSEEK = "deepseek"        # DeepSeek (深度求索)
    CUSTOM = "custom"            # 自定义


@dataclass
class ModelConfig:
    """模型配置"""
    id: str                              # 配置ID
    name: str                            # 显示名称
    provider: str                        # 提供商
    model: str                           # 模型名称
    api_key: str                         # API Key
    base_url: str                        # API 基础 URL
    max_tokens: int = 2000               # 最大 token 数
    temperature: float = 0.7             # 温度参数
    timeout: int = 120                   # 超时时间（秒）
    enabled: bool = True                 # 是否启用
    description: str = ""                # 描述
    headers: Dict[str, str] = field(default_factory=dict)  # 自定义请求头
    request_format: str = "openai"       # 请求格式: openai, dashscope, custom
    response_path: str = "choices.0.message.content"  # 响应内容提取路径
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ModelConfig':
        """从字典创建"""
        return cls(**data)


# 预设模型配置
PRESET_MODELS = {
    "qwen-max": ModelConfig(
        id="qwen-max",
        name="通义千问-Max",
        provider=ModelProvider.DASHSCOPE.value,
        model="qwen-max",
        api_key="",
        base_url="https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
        max_tokens=2000,
        temperature=0.7,
        timeout=120,
        enabled=True,
        description="阿里云百炼平台，通义千问最强模型",
        request_format="dashscope",
        response_path="output.text"
    ),
    "qwen-plus": ModelConfig(
        id="qwen-plus",
        name="通义千问-Plus",
        provider=ModelProvider.DASHSCOPE.value,
        model="qwen-plus",
        api_key="",
        base_url="https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
        max_tokens=2000,
        temperature=0.7,
        timeout=120,
        enabled=True,
        description="阿里云百炼平台，通义千问增强模型",
        request_format="dashscope",
        response_path="output.text"
    ),
    "qwen-turbo": ModelConfig(
        id="qwen-turbo",
        name="通义千问-Turbo",
        provider=ModelProvider.DASHSCOPE.value,
        model="qwen-turbo",
        api_key="",
        base_url="https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
        max_tokens=2000,
        temperature=0.7,
        timeout=120,
        enabled=True,
        description="阿里云百炼平台，通义千问快速模型",
        request_format="dashscope",
        response_path="output.text"
    ),
    "glm-4": ModelConfig(
        id="glm-4",
        name="GLM-4",
        provider=ModelProvider.ZHIPU.value,
        model="glm-4",
        api_key="",
        base_url="https://open.bigmodel.cn/api/paas/v4/chat/completions",
        max_tokens=2000,
        temperature=0.7,
        timeout=120,
        enabled=True,
        description="智谱 AI，GLM-4 大模型",
        request_format="openai",
        response_path="choices.0.message.content"
    ),
    "glm-3-turbo": ModelConfig(
        id="glm-3-turbo",
        name="GLM-3-Turbo",
        provider=ModelProvider.ZHIPU.value,
        model="glm-3-turbo",
        api_key="",
        base_url="https://open.bigmodel.cn/api/paas/v4/chat/completions",
        max_tokens=2000,
        temperature=0.7,
        timeout=120,
        enabled=True,
        description="智谱 AI，GLM-3-Turbo 快速模型",
        request_format="openai",
        response_path="choices.0.message.content"
    ),
    "kimi-latest": ModelConfig(
        id="kimi-latest",
        name="Kimi",
        provider=ModelProvider.MOONSHOT.value,
        model="kimi-latest",
        api_key="",
        base_url="https://api.moonshot.cn/v1/chat/completions",
        max_tokens=2000,
        temperature=0.7,
        timeout=120,
        enabled=True,
        description="月之暗面，Kimi 长文本模型",
        request_format="openai",
        response_path="choices.0.message.content"
    ),
    "mini-max": ModelConfig(
        id="mini-max",
        name="MiniMax",
        provider=ModelProvider.MINIMAX.value,
        model="abab6.5-chat",
        api_key="",
        base_url="https://api.minimax.chat/v1/text/chatcompletion_v2",
        max_tokens=2000,
        temperature=0.7,
        timeout=120,
        enabled=True,
        description="MiniMax，通用大模型",
        request_format="openai",
        response_path="choices.0.message.content"
    ),
    "deepseek-chat": ModelConfig(
        id="deepseek-chat",
        name="DeepSeek Chat",
        provider=ModelProvider.DEEPSEEK.value,
        model="deepseek-chat",
        api_key="",
        base_url="https://api.deepseek.com/chat/completions",
        max_tokens=2000,
        temperature=0.7,
        timeout=120,
        enabled=True,
        description="深度求索，DeepSeek Chat 对话模型",
        request_format="openai",
        response_path="choices.0.message.content"
    ),
    "deepseek-coder": ModelConfig(
        id="deepseek-coder",
        name="DeepSeek Coder",
        provider=ModelProvider.DEEPSEEK.value,
        model="deepseek-coder",
        api_key="",
        base_url="https://api.deepseek.com/chat/completions",
        max_tokens=2000,
        temperature=0.7,
        timeout=120,
        enabled=True,
        description="深度求索，DeepSeek Coder 代码专用模型",
        request_format="openai",
        response_path="choices.0.message.content"
    ),
    "deepseek-v2.5": ModelConfig(
        id="deepseek-v2.5",
        name="DeepSeek V2.5",
        provider=ModelProvider.DEEPSEEK.value,
        model="deepseek-v2.5",
        api_key="",
        base_url="https://api.deepseek.com/chat/completions",
        max_tokens=4000,
        temperature=0.7,
        timeout=120,
        enabled=True,
        description="深度求索，DeepSeek V2.5 最新版本",
        request_format="openai",
        response_path="choices.0.message.content"
    ),
    "deepseek-r1": ModelConfig(
        id="deepseek-r1",
        name="DeepSeek R1",
        provider=ModelProvider.DEEPSEEK.value,
        model="deepseek-reasoner",
        api_key="",
        base_url="https://api.deepseek.com/chat/completions",
        max_tokens=8000,
        temperature=0.6,
        timeout=180,
        enabled=True,
        description="深度求索，DeepSeek R1 推理模型（擅长复杂推理、数学、代码任务）",
        request_format="openai",
        response_path="choices.0.message.content"
    ),
    "openrouter-deepseek-r1": ModelConfig(
        id="openrouter-deepseek-r1",
        name="OpenRouter-DeepSeek R1",
        provider=ModelProvider.CUSTOM.value,
        model="deepseek/deepseek-r1",
        api_key="",
        base_url="https://openrouter.ai/api/v1/chat/completions",
        max_tokens=8000,
        temperature=0.6,
        timeout=180,
        enabled=True,
        description="通过 OpenRouter 调用 DeepSeek R1 推理模型",
        request_format="openai",
        response_path="choices.0.message.content"
    ),
}


class ModelConfigManager:
    """模型配置管理器"""
    
    def __init__(self):
        self.configs: Dict[str, ModelConfig] = {}
        self._load_configs()
    
    def _load_configs(self):
        """加载配置"""
        # 先加载预设配置
        self.configs = {k: v for k, v in PRESET_MODELS.items()}
        
        # 加载用户保存的配置（覆盖预设）
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for config_id, config_data in data.items():
                        self.configs[config_id] = ModelConfig.from_dict(config_data)
                print(f'[INFO] 已加载 {len(data)} 个模型配置')
            except Exception as e:
                print(f'[ERROR] 加载模型配置失败: {e}')
    
    def save_configs(self):
        """保存配置到文件"""
        try:
            data = {k: v.to_dict() for k, v in self.configs.items()}
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f'[INFO] 已保存 {len(data)} 个模型配置')
            return True
        except Exception as e:
            print(f'[ERROR] 保存模型配置失败: {e}')
            return False
    
    def get_config(self, config_id: str) -> Optional[ModelConfig]:
        """获取配置"""
        return self.configs.get(config_id)
    
    def get_all_configs(self) -> Dict[str, ModelConfig]:
        """获取所有配置"""
        return self.configs.copy()
    
    def get_enabled_configs(self) -> Dict[str, ModelConfig]:
        """获取启用的配置"""
        return {k: v for k, v in self.configs.items() if v.enabled}
    
    def add_config(self, config: ModelConfig) -> bool:
        """添加配置"""
        self.configs[config.id] = config
        return self.save_configs()
    
    def update_config(self, config_id: str, **kwargs) -> bool:
        """更新配置"""
        if config_id not in self.configs:
            return False
        config = self.configs[config_id]
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
        return self.save_configs()
    
    def delete_config(self, config_id: str) -> bool:
        """删除配置"""
        if config_id in self.configs:
            del self.configs[config_id]
            return self.save_configs()
        return False
    
    def get_config_list(self) -> List[Dict]:
        """获取配置列表（用于前端展示）"""
        return [
            {
                "id": k,
                "name": v.name,
                "provider": v.provider,
                "model": v.model,
                "enabled": v.enabled,
                "description": v.description,
                "has_api_key": bool(v.api_key)
            }
            for k, v in self.configs.items()
        ]


# 全局配置管理器实例
_model_config_manager: Optional[ModelConfigManager] = None


def get_model_config_manager() -> ModelConfigManager:
    """获取模型配置管理器实例"""
    global _model_config_manager
    if _model_config_manager is None:
        _model_config_manager = ModelConfigManager()
    return _model_config_manager


def get_model_config(config_id: str) -> Optional[ModelConfig]:
    """获取模型配置"""
    return get_model_config_manager().get_config(config_id)


def get_enabled_models() -> List[Dict]:
    """获取启用的模型列表"""
    manager = get_model_config_manager()
    configs = manager.get_enabled_configs()
    return [
        {
            "id": k,
            "name": v.name,
            "provider": v.provider,
            "model": v.model,
            "description": v.description
        }
        for k, v in configs.items()
    ]


# 测试代码
if __name__ == '__main__':
    manager = get_model_config_manager()
    print("可用模型:")
    for model in manager.get_config_list():
        print(f"  - {model['name']} ({model['id']}): {model['description']}")
