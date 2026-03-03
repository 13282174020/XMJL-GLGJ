# -*- coding: utf-8 -*-
"""
配置管理模块
"""

import os
import json
from pathlib import Path
from typing import Any, Optional


class Config:
    """配置管理类"""
    
    def __init__(self, config_path: Optional[str] = None):
        """初始化配置
        
        Args:
            config_path: 配置文件路径，默认使用 backend/app/config.json
        """
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), 'config.json')
        
        self.config_path = config_path
        self._config = {}
        self.load()
    
    def load(self) -> None:
        """加载配置文件"""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._config = json.load(f)
        else:
            # 使用默认配置
            self._config = self._get_default_config()
    
    def _get_default_config(self) -> dict:
        """获取默认配置"""
        base_dir = Path(__file__).parent.parent.parent
        return {
            "app_name": "软件建设方案 AI 生成系统",
            "version": "2.0.0",
            "debug": True,
            "secret_key": os.urandom(24).hex(),
            "database": {
                "type": "sqlite",
                "url": f"sqlite:///{base_dir}/backend/data/app.db"
            },
            "redis": {
                "host": "localhost",
                "port": 6379,
                "db": 0
            },
            "llm": {
                "default_model": "qwen-max",
                "api_key": "",
                "max_tokens": 4000,
                "temperature": 0.7,
                "timeout": 120
            },
            "file_storage": {
                "upload_folder": str(base_dir / "uploads"),
                "output_folder": str(base_dir / "outputs"),
                "max_file_size_mb": 50
            },
            "task": {
                "cleanup_interval_hours": 1,
                "file_retention_hours": 24
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值
        
        Args:
            key: 配置键，支持点号分隔，如 'llm.default_model'
            default: 默认值
            
        Returns:
            配置值
        """
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any) -> None:
        """设置配置值
        
        Args:
            key: 配置键
            value: 配置值
        """
        keys = key.split('.')
        config = self._config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
    
    def save(self) -> None:
        """保存配置文件"""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self._config, f, indent=2, ensure_ascii=False)
    
    @property
    def app_name(self) -> str:
        return self._config.get('app_name', '软件建设方案 AI 生成系统')
    
    @property
    def version(self) -> str:
        return self._config.get('version', '2.0.0')
    
    @property
    def debug(self) -> bool:
        return self._config.get('debug', False)
    
    @property
    def secret_key(self) -> str:
        return self._config.get('secret_key', '')
    
    @property
    def database_url(self) -> str:
        return self.get('database.url', '')
    
    @property
    def llm_api_key(self) -> str:
        return self.get('llm.api_key', '')
    
    @property
    def default_model(self) -> str:
        return self.get('llm.default_model', 'qwen-max')
    
    @property
    def upload_folder(self) -> str:
        return self.get('file_storage.upload_folder', 'uploads')
    
    @property
    def output_folder(self) -> str:
        return self.get('file_storage.output_folder', 'outputs')
    
    @property
    def max_file_size(self) -> int:
        """最大文件大小（字节）"""
        return self.get('file_storage.max_file_size_mb', 50) * 1024 * 1024


# 全局配置实例
config = Config()
