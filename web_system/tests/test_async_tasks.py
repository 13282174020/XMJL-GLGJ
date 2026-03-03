# -*- coding: utf-8 -*-
"""
异步任务管理模块测试用例
"""

import unittest
import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import TaskManager, TaskStatus


class TestTaskManager(unittest.TestCase):
    """任务管理器测试"""

    def setUp(self):
        """测试前准备"""
        self.task_manager = TaskManager()

    def tearDown(self):
        """测试后清理"""
        pass

    # ========== 正常业务场景测试 ==========

    def test_create_task_success(self):
        """测试创建任务成功"""
        task_id = self.task_manager.create_task(
            task_type='future_community',
            user_prompt='测试需求',
            api_key='sk-test123',
            model='qwen-max'
        )
        self.assertIsNotNone(task_id)
        self.assertEqual(len(task_id), 32)

    def test_get_task_status_exists(self):
        """测试获取已存在任务状态"""
        task_id = self.task_manager.create_task(
            task_type='future_community',
            user_prompt='测试需求'
        )
        status = self.task_manager.get_task_status(task_id)
        self.assertIsNotNone(status)
        self.assertEqual(status['task_id'], task_id)
        self.assertEqual(status['status'], TaskStatus.PENDING.value)

    def test_update_task_progress(self):
        """测试更新任务进度"""
        task_id = self.task_manager.create_task(
            task_type='general_project',
            user_prompt='测试更新进度'
        )
        success = self.task_manager.update_task_progress(
            task_id,
            progress=50,
            message='处理中'
        )
        self.assertTrue(success)
        status = self.task_manager.get_task_status(task_id)
        self.assertEqual(status['progress'], 50)
        self.assertEqual(status['message'], '处理中')

    # ========== 边界条件测试 ==========

    def test_get_task_status_not_exists(self):
        """测试获取不存在的任务状态"""
        status = self.task_manager.get_task_status('non_existent_task_id')
        self.assertIsNone(status)

    def test_update_task_progress_not_exists(self):
        """测试更新不存在的任务进度"""
        success = self.task_manager.update_task_progress(
            'non_existent_task_id',
            progress=50,
            message='测试'
        )
        self.assertFalse(success)

    def test_create_task_with_empty_prompt(self):
        """测试创建空提示词的任务"""
        task_id = self.task_manager.create_task(
            task_type='future_community',
            user_prompt=''
        )
        self.assertIsNotNone(task_id)
        status = self.task_manager.get_task_status(task_id)
        self.assertEqual(status['user_prompt'], '')

    def test_create_task_with_long_prompt(self):
        """测试创建超长提示词的任务"""
        long_prompt = '测试内容' * 500  # 2000 字符
        task_id = self.task_manager.create_task(
            task_type='future_community',
            user_prompt=long_prompt
        )
        self.assertIsNotNone(task_id)
        status = self.task_manager.get_task_status(task_id)
        # 提示词会被完整保存
        self.assertEqual(len(status['user_prompt']), 2000)

    # ========== 异常处理测试 ==========

    def test_update_progress_invalid_task_id(self):
        """测试使用无效任务 ID 更新进度"""
        success = self.task_manager.update_task_progress(
            None,
            progress=50,
            message='测试'
        )
        self.assertFalse(success)

    def test_update_progress_negative_value(self):
        """测试使用负数进度更新"""
        task_id = self.task_manager.create_task(
            task_type='future_community',
            user_prompt='测试负数进度'
        )
        success = self.task_manager.update_task_progress(
            task_id,
            progress=-10,
            message='负数测试'
        )
        self.assertTrue(success)  # 应该能更新，但进度会被限制
        status = self.task_manager.get_task_status(task_id)
        self.assertGreaterEqual(status['progress'], 0)

    def test_update_progress_over_100(self):
        """测试使用超过 100 的进度更新"""
        task_id = self.task_manager.create_task(
            task_type='future_community',
            user_prompt='测试超 100 进度'
        )
        success = self.task_manager.update_task_progress(
            task_id,
            progress=150,
            message='超 100 测试'
        )
        self.assertTrue(success)
        status = self.task_manager.get_task_status(task_id)
        self.assertLessEqual(status['progress'], 100)

    def test_mark_task_completed(self):
        """测试标记任务完成"""
        task_id = self.task_manager.create_task(
            task_type='future_community',
            user_prompt='测试完成'
        )
        success = self.task_manager.mark_task_completed(
            task_id,
            output_filename='test_output.docx'
        )
        self.assertTrue(success)
        status = self.task_manager.get_task_status(task_id)
        self.assertEqual(status['status'], TaskStatus.COMPLETED.value)
        self.assertEqual(status['progress'], 100)
        self.assertEqual(status['output_filename'], 'test_output.docx')

    def test_mark_task_failed(self):
        """测试标记任务失败"""
        task_id = self.task_manager.create_task(
            task_type='future_community',
            user_prompt='测试失败'
        )
        success = self.task_manager.mark_task_failed(
            task_id,
            error_message='模拟错误'
        )
        self.assertTrue(success)
        status = self.task_manager.get_task_status(task_id)
        self.assertEqual(status['status'], TaskStatus.FAILED.value)
        self.assertEqual(status['error_message'], '模拟错误')

    def test_cancel_task(self):
        """测试取消任务"""
        task_id = self.task_manager.create_task(
            task_type='future_community',
            user_prompt='测试取消'
        )
        success = self.task_manager.cancel_task(task_id)
        self.assertTrue(success)
        status = self.task_manager.get_task_status(task_id)
        self.assertEqual(status['status'], TaskStatus.CANCELLED.value)

    def test_get_task_list(self):
        """测试获取任务列表"""
        # 创建 3 个任务
        for i in range(3):
            self.task_manager.create_task(
                task_type='future_community',
                user_prompt=f'测试任务{i}'
            )
        task_list = self.task_manager.get_task_list(page=1, page_size=10)
        self.assertIn('tasks', task_list)
        self.assertIn('total', task_list)
        self.assertGreaterEqual(task_list['total'], 3)

    def test_get_task_list_with_keyword(self):
        """测试带关键词搜索任务列表"""
        # 创建一个新任务
        task_id = self.task_manager.create_task(
            task_type='future_community',
            user_prompt='测试任务'
        )
        # 使用 task_id 作为关键词搜索（当前实现只搜索 task_id 和 template_type）
        task_list = self.task_manager.get_task_list(
            page=1,
            page_size=10,
            keyword=task_id[:8]  # 使用前 8 个字符作为关键词
        )
        self.assertGreater(task_list['total'], 0)


class TestTaskStatus(unittest.TestCase):
    """任务状态枚举测试"""

    def test_task_status_values(self):
        """测试任务状态枚举值"""
        self.assertEqual(TaskStatus.PENDING.value, 'pending')
        self.assertEqual(TaskStatus.PROCESSING.value, 'processing')
        self.assertEqual(TaskStatus.PARSING_FILE.value, 'parsing_file')
        self.assertEqual(TaskStatus.GENERATING_AI.value, 'generating_ai')
        self.assertEqual(TaskStatus.CREATING_DOC.value, 'creating_doc')
        self.assertEqual(TaskStatus.COMPLETED.value, 'completed')
        self.assertEqual(TaskStatus.FAILED.value, 'failed')
        self.assertEqual(TaskStatus.CANCELLED.value, 'cancelled')

    def test_task_status_count(self):
        """测试任务状态数量"""
        self.assertEqual(len(TaskStatus), 8)


if __name__ == '__main__':
    unittest.main()
