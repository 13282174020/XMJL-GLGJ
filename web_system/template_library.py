# -*- coding: utf-8 -*-
"""模板库管理模块"""
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict
from dataclasses import dataclass, asdict


@dataclass
class TemplateInfo:
    """模板信息"""
    id: str
    name: str
    type: str
    file_path: str
    chapter_structure: Dict
    style_config: Dict
    created_at: str
    is_default: bool = False
    
    def to_dict(self):
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data):
        return cls(**data)


class TemplateLibrary:
    """模板库管理器"""
    
    def __init__(self, base_dir: str = 'templates'):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)
        self.metadata_file = self.base_dir / 'metadata.json'
        self.templates = self._load_metadata()
    
    def _load_metadata(self) -> Dict[str, TemplateInfo]:
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return {k: TemplateInfo.from_dict(v) for k, v in data.items()}
        return {}
    
    def _save_metadata(self):
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump({k: v.to_dict() for k, v in self.templates.items()}, 
                     f, ensure_ascii=False, indent=2)
    
    def add_template(self, 
                     name: str,
                     file_path: str,
                     template_type: str,
                     chapter_structure: Dict,
                     style_config: Dict,
                     is_default: bool = False) -> TemplateInfo:
        import uuid
        template_id = f'template_{uuid.uuid4().hex[:8]}'
        
        # 复制文件到模板库
        dest_path = self.base_dir / f'{template_id}.docx'
        shutil.copy2(file_path, dest_path)
        
        info = TemplateInfo(
            id=template_id,
            name=name,
            type=template_type,
            file_path=str(dest_path),
            chapter_structure=chapter_structure,
            style_config=style_config,
            created_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            is_default=is_default
        )
        
        self.templates[template_id] = info
        self._save_metadata()
        return info
    
    def get_all_templates(self) -> List[TemplateInfo]:
        return list(self.templates.values())
    
    def get_template(self, template_id: str) -> Optional[TemplateInfo]:
        return self.templates.get(template_id)
    
    def delete_template(self, template_id: str) -> bool:
        if template_id in self.templates:
            template = self.templates[template_id]
            file_path = Path(template.file_path)
            if file_path.exists():
                file_path.unlink()
            del self.templates[template_id]
            self._save_metadata()
            return True
        return False
    
    def download_template(self, template_id: str, output_path: str) -> bool:
        template = self.get_template(template_id)
        if not template:
            return False
        file_path = Path(template.file_path)
        if not file_path.exists():
            return False
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file_path, output_path)
        return True
