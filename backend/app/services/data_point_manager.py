# -*- coding: utf-8 -*-
"""
数据点管理服务 - SKILL-005
维护和管理全局数据点字典，确保全文数据一致性
"""

import re
from typing import Dict, Any, List, Optional
from datetime import datetime


class DataPointManager:
    """数据点管理器类"""
    
    # 数据点类型定义
    DATA_POINT_TYPES = {
        'total_investment': '总投资',
        'hardware_cost': '硬件费用',
        'software_cost': '软件费用',
        'population': '服务人口',
        'households': '户数',
        'construction_period': '建设工期',
        'camera_count': '摄像头数量',
        'energy_saving_target': '节能目标',
        'area': '面积',
        'staff_count': '人员数量',
    }
    
    def __init__(self):
        """初始化数据点管理器"""
        self.data_points: Dict[str, Any] = {}
        self.history: List[Dict] = []
    
    def extract_from_text(self, text: str) -> Dict[str, str]:
        """从文本中提取数据点
        
        Args:
            text: 文本内容
            
        Returns:
            提取的数据点字典
        """
        extracted = {}
        
        # 金额模式
        if re.search(r'总投资.*?(\d+(?:\.\d+)?)\s*亿元', text):
            match = re.search(r'总投资.*?(\d+(?:\.\d+)?)\s*亿元', text)
            extracted['total_investment'] = f"{float(match.group(1)) * 10000}万元"
        elif re.search(r'总投资.*?(\d+(?:\.\d+)?)\s*万元', text):
            match = re.search(r'总投资.*?(\d+(?:\.\d+)?)\s*万元', text)
            extracted['total_investment'] = f"{match.group(1)}万元"
        elif re.search(r'投资.*?(\d+(?:\.\d+)?)\s*万元', text) and '硬件' not in text and '软件' not in text:
            match = re.search(r'投资.*?(\d+(?:\.\d+)?)\s*万元', text)
            extracted['total_investment'] = f"{match.group(1)}万元"
        
        # 人口模式 - 修复空格问题
        pop_match = re.search(r'约\s*(\d+\.\d+)\s*万人', text)
        if pop_match:
            extracted['population'] = f"约{pop_match.group(1)}万人"
        
        # 户数模式
        house_match = re.search(r'(\d+)\s*户', text)
        if house_match:
            extracted['households'] = f"约{house_match.group(1)}户"
        
        # 工期模式
        period_match = re.search(r'(\d+)\s*个月', text)
        if period_match:
            extracted['construction_period'] = f"{period_match.group(1)}个月"
        
        return extracted
    
    def update(self, new_points: Dict[str, Any]) -> List[str]:
        """更新数据点"""
        conflicts = []
        for key, value in new_points.items():
            if key in self.data_points:
                if self.data_points[key] != value:
                    conflicts.append(f"{key}: {self.data_points[key]} vs {value}")
            self.data_points[key] = value
        
        self.history.append({
            'timestamp': datetime.now().isoformat(),
            'updates': new_points,
            'conflicts': conflicts
        })
        return conflicts
    
    def get(self, key: str, default: Any = None) -> Any:
        return self.data_points.get(key, default)
    
    def get_all(self) -> Dict[str, Any]:
        return self.data_points.copy()
    
    def clear(self) -> None:
        self.data_points.clear()
        self.history.clear()
    
    def to_prompt_string(self) -> str:
        if not self.data_points:
            return "暂无已确立的数据点"
        lines = []
        for key, value in self.data_points.items():
            name = self.DATA_POINT_TYPES.get(key, key)
            lines.append(f"- {name}: {value}")
        return '\n'.join(lines)


def create_data_point_manager() -> DataPointManager:
    return DataPointManager()


if __name__ == '__main__':
    manager = DataPointManager()
    test_text = "项目总投资为 1200 万元。服务人口约 1.1 万人，覆盖 3000 户居民。建设工期 12 个月。"
    print(manager.extract_from_text(test_text))
