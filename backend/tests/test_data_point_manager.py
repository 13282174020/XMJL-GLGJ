# -*- coding: utf-8 -*-
"""
数据点管理器测试用例
"""

import unittest
import os
import sys

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.data_point_manager import DataPointManager


class TestDataPointManager(unittest.TestCase):
    """数据点管理器测试"""

    def setUp(self):
        """测试前准备"""
        self.manager = DataPointManager()
    
    def tearDown(self):
        """测试后清理"""
        self.manager.clear()

    # ========== 正常业务场景测试 ==========

    def test_extract_investment(self):
        """测试提取投资金额"""
        text = "总投资 1200 万元。"
        result = self.manager.extract_from_text(text)
        
        self.assertIn('total_investment', result)
        # 格式可能是"1200 万元"或"1200 万元"
        self.assertIn('万元', result['total_investment'])

    def test_extract_population(self):
        """测试提取人口数据"""
        text = "服务人口约 1.1 万人。"
        result = self.manager.extract_from_text(text)
        
        self.assertIn('population', result)

    def test_extract_construction_period(self):
        """测试提取建设工期"""
        text = "建设工期为 12 个月。"
        result = self.manager.extract_from_text(text)
        
        self.assertIn('construction_period', result)

    # ========== 边界条件测试 ==========

    def test_extract_no_data(self):
        """测试无数据可提取"""
        text = "这是一个没有数据点的文本。"
        result = self.manager.extract_from_text(text)
        
        self.assertEqual(result, {})

    def test_extract_empty_text(self):
        """测试空文本"""
        result = self.manager.extract_from_text('')
        self.assertEqual(result, {})

    # ========== 数据点更新测试 ==========

    def test_update_data_points(self):
        """测试更新数据点"""
        new_points = {
            'total_investment': '1200 万元',
            'population': '约 1.1 万人'
        }
        
        conflicts = self.manager.update(new_points)
        
        self.assertEqual(len(conflicts), 0)
        self.assertEqual(self.manager.get('total_investment'), '1200 万元')

    def test_update_with_conflict(self):
        """测试数据冲突检测"""
        # 先添加一个数据点
        self.manager.update({'total_investment': '1000 万元'})
        
        # 添加冲突数据（差异超过 10%）
        new_points = {'total_investment': '2000 万元'}
        conflicts = self.manager.update(new_points)
        
        self.assertGreater(len(conflicts), 0)

    def test_update_same_value(self):
        """测试相同值不冲突"""
        self.manager.update({'total_investment': '1200 万元'})
        
        # 添加相同数据
        new_points = {'total_investment': '1200 万元'}
        conflicts = self.manager.update(new_points)
        
        self.assertEqual(len(conflicts), 0)

    # ========== 辅助方法测试 ==========

    def test_get_all(self):
        """测试获取所有数据点"""
        self.manager.update({'total_investment': '1200 万元'})
        self.manager.update({'population': '约 1.1 万人'})
        
        all_points = self.manager.get_all()
        
        self.assertEqual(len(all_points), 2)
        self.assertIn('total_investment', all_points)

    def test_get_with_default(self):
        """测试获取不存在的键"""
        result = self.manager.get('non_existent', 'default_value')
        self.assertEqual(result, 'default_value')

    def test_to_prompt_string(self):
        """测试转换为 Prompt 字符串"""
        self.manager.update({'total_investment': '1200 万元'})
        
        prompt_str = self.manager.to_prompt_string()
        
        self.assertIn('总投资', prompt_str)
        self.assertIn('1200 万元', prompt_str)

    def test_clear(self):
        """测试清空数据点"""
        self.manager.update({'total_investment': '1200 万元'})
        self.manager.clear()
        
        all_points = self.manager.get_all()
        self.assertEqual(len(all_points), 0)


if __name__ == '__main__':
    unittest.main()
