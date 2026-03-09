# -*- coding: utf-8 -*-
"""
数据点管理模块 - 实现数据一致性管理

功能：
1. 从文本中动态提取数据点（正则 + AI）
2. 维护数据点字典，确保全文数据一致
3. 检测并记录数据冲突
4. 为 AI 生成提供数据注入

设计原则：
- 不预设任何特定字段，完全动态识别
- 支持增量更新，每章生成后可提取新数据点
- 冲突检测，帮助人工决策
"""

import re
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class DataConflict:
    """数据冲突记录"""
    key: str
    existing_value: str
    new_value: str
    chapter: str = ""  # 发生冲突的章节
    
    def __str__(self):
        return f"数据冲突 [{self.key}]: '{self.existing_value}' vs '{self.new_value}'"


class DataPointManager:
    """数据点管理器
    
    管理文档中需要保持一致的关键数据，如：
    - 项目名称、建设单位
    - 总投资、建设工期
    - 人口数量、户数等
    """
    
    # 正则表达式模式 - 用于识别常见数据类型
    # 注意：这些模式用于辅助识别，不预设具体字段名
    PATTERNS = {
        'amount': [
            r'([\d\.]+)\s*万?元',  # 金额：500万元、1000元
            r'投资[\s:：]*([\d\.]+)\s*万?元',  # 总投资：500万元
        ],
        'duration': [
            r'([\d]+)\s*个?[年月天]',  # 工期：12个月
            r'工期[\s:：]*([\d]+)\s*个?[年月天]',  # 建设工期：12个月
        ],
        'population': [
            r'约?\s*([\d\.]+)\s*万?人',  # 人口：约1.1万人
            r'([\d]+)\s*户',  # 户数：3000户
        ],
        'project_name': [
            r'项目名称[\s:：]*([^\n]+)',  # 项目名称：XXX
            r'项目[\s:：]*名[\s:：]*称[\s:：]*([^\n]+)',  # 兼容各种格式
        ],
        'organization': [
            r'建设单位[\s:：]*([^\n]+)',  # 建设单位：XXX
            r'业主单位[\s:：]*([^\n]+)',  # 业主单位：XXX
            r'实施单位[\s:：]*([^\n]+)',  # 实施单位：XXX
        ],
    }
    
    def __init__(self):
        """初始化数据点管理器"""
        self._data_points: Dict[str, str] = {}
        self._conflicts: List[DataConflict] = []
        self._extraction_history: List[Dict] = []  # 记录提取历史
    
    def extract_from_text(self, text: str, chapter: str = "") -> Dict[str, str]:
        """从文本中提取数据点（正则 + 启发式规则）
        
        Args:
            text: 待分析的文本
            chapter: 文本来源章节（用于冲突记录）
            
        Returns:
            提取到的数据点字典 {数据项名称: 数据值}
        """
        extracted = {}
        
        if not text:
            return extracted
        
        # 1. 使用正则表达式提取常见数据
        for data_type, patterns in self.PATTERNS.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    value = match.group(1).strip() if match.groups() else match.group(0).strip()
                    
                    # 根据匹配类型生成数据项名称
                    key = self._infer_key_from_context(text, match.start(), data_type)
                    if key and value:
                        extracted[key] = value
        
        # 2. 启发式规则：识别"XXX：YYY"格式的键值对
        kv_pattern = r'^\s*([^：:\n]{2,20})[\s:：]+([^\n]{1,50})$'
        for line in text.split('\n'):
            match = re.match(kv_pattern, line.strip())
            if match:
                key = match.group(1).strip()
                value = match.group(2).strip()
                # 过滤掉非数据项（如标题、说明等）
                if self._is_likely_data_point(key, value):
                    extracted[key] = value
        
        # 记录提取历史
        self._extraction_history.append({
            'chapter': chapter,
            'extracted': extracted.copy()
        })
        
        return extracted
    
    def extract_with_ai(self, text: str, ai_call_func, chapter: str = "") -> Dict[str, str]:
        """使用 AI 提取数据点
        
        Args:
            text: 待分析的文本
            ai_call_func: AI 调用函数，接收 prompt 返回字符串
            chapter: 文本来源章节
            
        Returns:
            提取到的数据点字典
        """
        if not text or not ai_call_func:
            return {}
        
        prompt = f"""请分析以下文本，提取需要全文保持一致的关键数据点。

【文本内容】
{text[:2000]}

【提取要求】
1. 提取所有具体的数值、名称、时间等关键信息
2. 数据项名称要简洁明确（如"项目名称"、"总投资"、"建设工期"）
3. 只提取事实性数据，不提取描述性内容
4. 如果同一数据有多个表述，选择最完整的一个

【输出格式】
请以 JSON 格式输出，不要包含其他内容：
{{
  "数据项名称1": "数据值1",
  "数据项名称2": "数据值2"
}}

如果没有提取到数据点，输出空对象 {{}}"""
        
        try:
            result = ai_call_func(prompt)
            # 尝试解析 JSON
            # 先尝试直接解析
            try:
                data_points = json.loads(result)
            except json.JSONDecodeError:
                # 尝试从文本中提取 JSON
                json_match = re.search(r'\{[\s\S]*\}', result)
                if json_match:
                    data_points = json.loads(json_match.group(0))
                else:
                    data_points = {}
            
            # 记录提取历史
            if data_points:
                self._extraction_history.append({
                    'chapter': chapter,
                    'extracted': data_points.copy(),
                    'method': 'ai'
                })
            
            return data_points if isinstance(data_points, dict) else {}
            
        except Exception as e:
            print(f"[DataPointManager] AI 提取失败: {e}")
            return {}
    
    def update(self, new_points: Dict[str, str], chapter: str = "") -> List[DataConflict]:
        """更新数据点字典
        
        Args:
            new_points: 新提取的数据点
            chapter: 数据来源章节（用于冲突记录）
            
        Returns:
            本次更新产生的冲突列表
        """
        new_conflicts = []
        
        for key, value in new_points.items():
            if not key or not value:
                continue
                
            key = key.strip()
            value = value.strip()
            
            if key not in self._data_points:
                # 新增数据点
                self._data_points[key] = value
            elif self._data_points[key] != value:
                # 数据冲突
                conflict = DataConflict(
                    key=key,
                    existing_value=self._data_points[key],
                    new_value=value,
                    chapter=chapter
                )
                self._conflicts.append(conflict)
                new_conflicts.append(conflict)
                # 不自动覆盖，保留原有值（人工决策）
        
        return new_conflicts
    
    def get_all(self) -> Dict[str, str]:
        """获取所有数据点
        
        Returns:
            数据点字典的副本
        """
        return self._data_points.copy()
    
    def get(self, key: str, default: str = "") -> str:
        """获取指定数据点的值
        
        Args:
            key: 数据项名称
            default: 默认值
            
        Returns:
            数据值或默认值
        """
        return self._data_points.get(key, default)
    
    def set(self, key: str, value: str) -> None:
        """手动设置数据点（用于人工修正）
        
        Args:
            key: 数据项名称
            value: 数据值
        """
        self._data_points[key.strip()] = value.strip()
    
    def get_conflicts(self) -> List[DataConflict]:
        """获取所有数据冲突
        
        Returns:
            冲突列表的副本
        """
        return self._conflicts.copy()
    
    def resolve_conflict(self, key: str, use_new: bool = False) -> bool:
        """解决数据冲突
        
        Args:
            key: 数据项名称
            use_new: 是否使用新值（False 则保留原值）
            
        Returns:
            是否成功解决
        """
        # 找到相关冲突
        related_conflicts = [c for c in self._conflicts if c.key == key]
        
        if not related_conflicts:
            return False
        
        if use_new:
            # 使用最新值
            latest = related_conflicts[-1]
            self._data_points[key] = latest.new_value
        
        # 移除已解决的冲突
        self._conflicts = [c for c in self._conflicts if c.key != key]
        
        return True
    
    def get_formatted_prompt_text(self) -> str:
        """获取格式化的数据点文本（用于 Prompt 注入）
        
        Returns:
            格式化的数据点文本
        """
        if not self._data_points:
            return "（暂无已确立的关键数据）"
        
        lines = ["【已确立的关键数据】", "（以下数据已在文中确立，引用时必须保持一致）", ""]
        
        for key, value in sorted(self._data_points.items()):
            lines.append(f"- {key}：{value}")
        
        return "\n".join(lines)
    
    def get_formatted_json(self) -> str:
        """获取格式化的 JSON 字符串（用于 Prompt 注入）
        
        Returns:
            JSON 格式的数据点
        """
        return json.dumps(self._data_points, ensure_ascii=False, indent=2)
    
    def clear(self) -> None:
        """清空所有数据点和冲突记录"""
        self._data_points.clear()
        self._conflicts.clear()
        self._extraction_history.clear()
    
    def _infer_key_from_context(self, text: str, position: int, data_type: str) -> Optional[str]:
        """根据上下文推断数据项名称
        
        Args:
            text: 完整文本
            position: 匹配位置
            data_type: 数据类型
            
        Returns:
            推断的数据项名称
        """
        # 向前查找关键词（最多向前 50 个字符）
        start = max(0, position - 50)
        context = text[start:position]
        
        # 根据数据类型和上下文推断
        if data_type == 'amount':
            if '投资' in context or '总投' in context:
                return '总投资'
            elif '预算' in context or '估算' in context:
                return '投资估算'
            elif '资金' in context:
                return '资金金额'
        
        elif data_type == 'duration':
            if '工期' in context or '周期' in context:
                return '建设工期'
            elif '时间' in context:
                return '建设周期'
        
        elif data_type == 'population':
            if '户' in context:
                return '总户数'
            elif '人' in context or '人口' in context:
                return '总人口'
        
        elif data_type == 'project_name':
            return '项目名称'
        
        elif data_type == 'organization':
            if '建设' in context:
                return '建设单位'
            elif '业主' in context:
                return '业主单位'
            elif '实施' in context:
                return '实施单位'
        
        return None
    
    def _is_likely_data_point(self, key: str, value: str) -> bool:
        """判断键值对是否可能是数据点
        
        Args:
            key: 键
            value: 值
            
        Returns:
            是否可能是数据点
        """
        # 排除明显的非数据项
        non_data_keywords = [
            '说明', '备注', '注意', '提示', '详见', '参见',
            '如下', '如下所示', '如图', '如表', '附件',
            '引言', '前言', '总结', '结论', '建议'
        ]
        
        for keyword in non_data_keywords:
            if keyword in key:
                return False
        
        # 键应该像是一个数据项名称
        # 通常包含名词，长度适中
        if len(key) < 2 or len(key) > 20:
            return False
        
        # 值应该有实质内容
        if len(value) < 1 or len(value) > 100:
            return False
        
        return True
    
    def get_extraction_summary(self) -> Dict:
        """获取提取历史摘要
        
        Returns:
            提取摘要信息
        """
        return {
            'total_data_points': len(self._data_points),
            'total_conflicts': len(self._conflicts),
            'extraction_count': len(self._extraction_history),
            'data_points': self._data_points.copy(),
            'conflicts': [
                {
                    'key': c.key,
                    'existing_value': c.existing_value,
                    'new_value': c.new_value,
                    'chapter': c.chapter
                }
                for c in self._conflicts
            ]
        }


# 便捷函数
def create_data_point_manager() -> DataPointManager:
    """创建数据点管理器实例"""
    return DataPointManager()


# 测试代码
if __name__ == '__main__':
    # 简单测试
    manager = DataPointManager()
    
    # 测试文本
    test_text = """
    项目名称：智慧社区管理平台建设项目
    建设单位：XX科技有限公司
    总投资：500万元
    建设工期：12个月
    社区总人口约1.1万人，总户数3000多户。
    """
    
    # 提取数据点
    extracted = manager.extract_from_text(test_text, "测试章节")
    print("提取的数据点：")
    for k, v in extracted.items():
        print(f"  {k}: {v}")
    
    # 更新数据点
    manager.update(extracted, "测试章节")
    
    # 显示格式化文本
    print("\n格式化输出：")
    print(manager.get_formatted_prompt_text())
