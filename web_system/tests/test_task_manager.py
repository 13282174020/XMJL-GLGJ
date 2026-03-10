# -*- coding: utf-8 -*-
"""
任务管理器测试用例 (SKILL-008)

测试标准：
1. 任务创建
2. 状态查询
3. 任务取消
4. 任务重试
5. 持久化验证
"""

import unittest
import os
import sys
import json
import time

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from task_manager import (
    get_task_manager, 
    TaskInfo, 
    ChapterStatus, 
    MAX_REGENERATE_COUNT,
    TASKS_ROOT
)


class TestTaskManager(unittest.TestCase):
    """任务管理器测试"""
    
    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        cls.manager = get_task_manager()
        cls.test_task_id = None
    
    @classmethod
    def tearDownClass(cls):
        """测试后清理"""
        # 清理测试任务目录
        if cls.test_task_id:
            import shutil
            task_dir = os.path.join(TASKS_ROOT, cls.test_task_id)
            if os.path.exists(task_dir):
                shutil.rmtree(task_dir)
                print(f'\n[CLEANUP] 清理测试任务目录：{task_dir}')
    
    def test_01_create_task(self):
        """测试 1: 创建任务"""
        print('\n' + '='*60)
        print('[TEST] 测试创建任务')
        print('='*60)
        
        task_id = self.manager.create_task(
            template_type='future_community',
            user_prompt='测试任务',
            model='glm-4'
        )
        
        TestTaskManager.test_task_id = task_id
        
        # 验证任务创建成功
        self.assertIsNotNone(task_id)
        print(f'[OK] 任务创建成功：{task_id}')
        
        # 验证任务目录存在
        task_dir = self.manager._get_task_directory(task_id)
        self.assertTrue(os.path.exists(task_dir))
        print(f'[OK] 任务目录已创建：{task_dir}')
        
        # 验证 task_info.json 存在
        task_info_path = os.path.join(task_dir, 'task_info.json')
        self.assertTrue(os.path.exists(task_info_path))
        print(f'[OK] task_info.json 已创建')
        
        # 验证任务信息内容
        task_info = self.manager.load_task_info(task_id)
        self.assertIsNotNone(task_info)
        self.assertEqual(task_info.template_type, 'future_community')
        self.assertEqual(task_info.user_prompt, '测试任务')
        self.assertEqual(task_info.model, 'glm-4')
        self.assertEqual(task_info.status, 'pending')
        print(f'[OK] 任务信息验证通过')
        
        print(f'\n[TASK] 任务信息:')
        print(f'  - task_id: {task_info.task_id}')
        print(f'  - template_type: {task_info.template_type}')
        print(f'  - model: {task_info.model}')
        print(f'  - status: {task_info.status}')
    
    def test_02_initialize_chapters(self):
        """测试 2: 初始化章节列表"""
        print('\n' + '='*60)
        print('[TEST] 测试初始化章节列表')
        print('='*60)
        
        task_id = TestTaskManager.test_task_id
        
        # 初始化章节
        chapter_titles = [
            '第一章 项目概况',
            '第二章 建设背景',
            '第三章 建设必要性',
            '第四章 建设目标'
        ]
        
        self.manager.initialize_chapters(task_id, chapter_titles)
        print(f'[OK] 章节列表初始化完成：{len(chapter_titles)} 章')
        
        # 验证章节保存
        chapters = self.manager.load_chapters(task_id)
        self.assertEqual(len(chapters), len(chapter_titles))
        print(f'[OK] 章节加载成功：{len(chapters)} 章')
        
        # 验证章节内容
        for i, chapter in enumerate(chapters):
            self.assertEqual(chapter.index, i)
            self.assertEqual(chapter.title, chapter_titles[i])
            self.assertEqual(chapter.status, 'pending')
        print(f'[OK] 章节内容验证通过')
        
        # 验证任务信息更新
        task_info = self.manager.load_task_info(task_id)
        self.assertEqual(task_info.total_chapters, len(chapter_titles))
        print(f'[OK] 任务信息已更新：total_chapters={task_info.total_chapters}')
    
    def test_03_update_chapter_status(self):
        """测试 3: 更新章节状态"""
        print('\n' + '='*60)
        print('[TEST] 测试更新章节状态')
        print('='*60)
        
        task_id = TestTaskManager.test_task_id
        
        # 更新第 1 章为完成状态
        test_content = '这是第一章的测试内容，共 100 字。'
        self.manager.update_chapter_status(
            task_id, 0,
            status='completed',
            content=test_content,
            word_count=len(test_content)
        )
        print(f'[OK] 第 1 章状态更新为 completed')
        
        # 验证章节状态
        chapters = self.manager.load_chapters(task_id)
        chapter = chapters[0]
        self.assertEqual(chapter.status, 'completed')
        self.assertEqual(chapter.content, test_content)
        self.assertEqual(chapter.word_count, len(test_content))
        self.assertIsNotNone(chapter.generated_at)
        print(f'[OK] 章节状态验证通过')
        
        # 更新第 2 章为失败状态
        self.manager.update_chapter_status(
            task_id, 1,
            status='failed',
            error_message='API 调用超时'
        )
        print(f'[OK] 第 2 章状态更新为 failed')
        
        # 验证任务进度更新
        task_info = self.manager.load_task_info(task_id)
        self.assertEqual(task_info.completed_chapters, 1)
        self.assertEqual(task_info.failed_chapters, [1])
        self.assertGreater(task_info.progress, 0)
        print(f'[OK] 任务进度更新：{task_info.progress}%')
    
    def test_04_get_task_status(self):
        """测试 4: 获取任务状态（轮询接口）"""
        print('\n' + '='*60)
        print('[TEST] 测试获取任务状态')
        print('='*60)

        task_id = TestTaskManager.test_task_id

        status = self.manager.get_task_status(task_id)

        self.assertIsNotNone(status)
        self.assertEqual(status['task_id'], task_id)
        self.assertIn(status['status'], ['pending', 'generating', 'completed', 'partially_completed'])
        print(f'[OK] 任务状态获取成功')

        # 验证返回数据结构
        required_fields = [
            'task_id', 'status', 'progress', 'total_chapters',
            'completed_chapters', 'chapters', 'created_at', 'updated_at',
            'message', 'output_filename'
        ]
        for field in required_fields:
            self.assertIn(field, status)
        print(f'[OK] 返回数据结构验证通过 - 包含 message 和 output_filename 字段')

        # 验证章节状态
        self.assertEqual(len(status['chapters']), 4)
        for chapter in status['chapters']:
            self.assertIn('index', chapter)
            self.assertIn('title', chapter)
            self.assertIn('status', chapter)
        print(f'[OK] 章节状态验证通过')
        
        print(f'\n[TASK] 任务状态:')
        print(f'  - status: {status["status"]}')
        print(f'  - progress: {status["progress"]}%')
        print(f'  - completed: {status["completed_chapters"]}/{status["total_chapters"]}')
    
    def test_05_pause_and_continue(self):
        """测试 5: 暂停和继续任务"""
        print('\n' + '='*60)
        print('[TEST] 测试暂停和继续任务')
        print('='*60)
        
        task_id = TestTaskManager.test_task_id
        
        # 暂停任务
        self.manager.pause_task(task_id)
        task_info = self.manager.load_task_info(task_id)
        self.assertEqual(task_info.status, 'paused')
        print(f'[OK] 任务已暂停')
        
        # 验证暂停状态
        self.assertTrue(self.manager.is_paused(task_id))
        print(f'[OK] 暂停状态验证通过')
        
        # 继续任务
        self.manager.continue_task(task_id)
        task_info = self.manager.load_task_info(task_id)
        self.assertEqual(task_info.status, 'generating')
        print(f'[OK] 任务已继续')
        
        # 验证继续状态
        self.assertFalse(self.manager.is_paused(task_id))
        print(f'[OK] 继续状态验证通过')
    
    def test_06_cancel_task(self):
        """测试 6: 取消任务"""
        print('\n' + '='*60)
        print('[TEST] 测试取消任务')
        print('='*60)
        
        task_id = self.manager.create_task(
            template_type='future_community',
            user_prompt='测试取消',
            model='glm-4'
        )
        
        # 取消任务
        self.manager.cancel_task(task_id)
        task_info = self.manager.load_task_info(task_id)
        self.assertEqual(task_info.status, 'cancelled')
        print(f'[OK] 任务已取消')
        
        # 验证取消状态
        self.assertTrue(self.manager.is_cancelled(task_id))
        print(f'[OK] 取消状态验证通过')
        
        # 清理测试任务
        import shutil
        task_dir = self.manager._get_task_directory(task_id)
        if os.path.exists(task_dir):
            shutil.rmtree(task_dir)
    
    def test_07_regenerate_limit(self):
        """测试 7: 重新生成次数限制"""
        print('\n' + '='*60)
        print('[TEST] 测试重新生成次数限制')
        print('='*60)
        
        task_id = TestTaskManager.test_task_id
        
        # 验证初始可以重新生成
        can_regenerate = self.manager.can_regenerate(task_id, 3)
        self.assertTrue(can_regenerate)
        print(f'[OK] 初始可以重新生成')
        
        # 模拟重新生成 2 次
        for i in range(MAX_REGENERATE_COUNT):
            self.manager.update_chapter_status(
                task_id, 3,
                status='completed',
                content=f'第{i+1}次重新生成的内容',
                regenerated_count=i+1
            )
            print(f'[OK] 第{MAX_REGENERATE_COUNT}次重新生成')
        
        # 验证达到上限后不能重新生成
        can_regenerate = self.manager.can_regenerate(task_id, 3)
        self.assertFalse(can_regenerate)
        print(f'[OK] 达到重新生成上限，不能再次重新生成')
        
        # 验证其他章节仍可重新生成
        can_regenerate = self.manager.can_regenerate(task_id, 2)
        self.assertTrue(can_regenerate)
        print(f'[OK] 其他章节仍可重新生成')
    
    def test_08_get_failed_chapters(self):
        """测试 8: 获取失败章节列表"""
        print('\n' + '='*60)
        print('[TEST] 测试获取失败章节列表')
        print('='*60)
        
        task_id = TestTaskManager.test_task_id
        
        # 获取失败章节
        failed_chapters = self.manager.get_failed_chapters(task_id)
        
        # 验证失败章节
        self.assertEqual(len(failed_chapters), 1)
        self.assertEqual(failed_chapters[0].index, 1)
        self.assertEqual(failed_chapters[0].status, 'failed')
        self.assertEqual(failed_chapters[0].error_message, 'API 调用超时')
        print(f'[OK] 失败章节获取成功：{len(failed_chapters)} 章')
        
        print(f'\n[FAILED CHAPTERS]')
        for chapter in failed_chapters:
            print(f'  - 第{chapter.index+1}章：{chapter.error_message}')

    def test_08b_progress_and_message_update(self):
        """测试 8b: 进度和消息字段更新"""
        print('\n' + '='*60)
        print('[TEST] 测试进度和消息字段更新')
        print('='*60)

        task_id = self.manager.create_task(
            template_type='future_community',
            user_prompt='测试进度消息',
            model='glm-4'
        )

        self.manager.initialize_chapters(task_id, ['第 1 章', '第 2 章', '第 3 章'])

        # 验证初始 message 字段
        status = self.manager.get_task_status(task_id)
        self.assertIn('message', status)
        print(f'[OK] message 字段存在')

        # 更新进度和消息
        self.manager.update_task_status(task_id, status='generating', progress=10, message='正在生成第 1 章...')
        status = self.manager.get_task_status(task_id)
        self.assertEqual(status['status'], 'generating')
        self.assertEqual(status['progress'], 10)
        self.assertEqual(status['message'], '正在生成第 1 章...')
        print(f'[OK] 进度和消息更新成功：progress={status["progress"]}%, message={status["message"]}')

        # 更新当前章节索引
        self.manager.update_task_status(task_id, current_chapter_index=0)
        self.manager.update_chapter_status(task_id, 0, status='generating')
        status = self.manager.get_task_status(task_id)
        self.assertEqual(status['current_chapter'], '第 1 章')
        print(f'[OK] current_chapter 更新成功：{status["current_chapter"]}')

        # 完成第 1 章
        self.manager.update_chapter_status(task_id, 0, status='completed', content='测试内容', word_count=100)
        status = self.manager.get_task_status(task_id)
        self.assertEqual(status['completed_chapters'], 1)
        self.assertGreater(status['progress'], 0)
        print(f'[OK] 第 1 章完成，进度={status["progress"]}%')

        # 验证 output_filename 字段
        self.manager.update_task_status(task_id, output_filename='test_output.docx')
        status = self.manager.get_task_status(task_id)
        self.assertEqual(status['output_filename'], 'test_output.docx')
        print(f'[OK] output_filename 更新成功')

        # 清理
        import shutil
        task_dir = self.manager._get_task_directory(task_id)
        if os.path.exists(task_dir):
            shutil.rmtree(task_dir)

    def test_09_persistence(self):
        """测试 9: 持久化验证"""
        print('\n' + '='*60)
        print('[TEST] 测试持久化')
        print('='*60)
        
        task_id = TestTaskManager.test_task_id
        
        # 验证文件存在
        task_dir = self.manager._get_task_directory(task_id)
        task_info_file = os.path.join(task_dir, 'task_info.json')
        chapters_file = os.path.join(task_dir, 'chapters.json')
        
        self.assertTrue(os.path.exists(task_info_file))
        self.assertTrue(os.path.exists(chapters_file))
        print(f'[OK] 持久化文件存在')
        
        # 验证 JSON 格式
        with open(task_info_file, 'r', encoding='utf-8') as f:
            task_info_data = json.load(f)
        self.assertIsInstance(task_info_data, dict)
        print(f'[OK] task_info.json 格式正确')
        
        with open(chapters_file, 'r', encoding='utf-8') as f:
            chapters_data = json.load(f)
        self.assertIsInstance(chapters_data, dict)
        self.assertIn('chapters', chapters_data)
        print(f'[OK] chapters.json 格式正确')
        
        # 验证重新加载后数据一致
        new_manager = get_task_manager()
        reloaded_task = new_manager.load_task_info(task_id)
        reloaded_chapters = new_manager.load_chapters(task_id)
        
        self.assertIsNotNone(reloaded_task)
        self.assertEqual(reloaded_task.task_id, task_id)
        self.assertEqual(len(reloaded_chapters), 4)
        print(f'[OK] 重新加载后数据一致')


class TestTaskManagerEdgeCases(unittest.TestCase):
    """边界情况测试"""
    
    def test_load_nonexistent_task(self):
        """测试加载不存在的任务"""
        print('\n' + '='*60)
        print('[TEST] 测试加载不存在的任务')
        print('='*60)
        
        manager = get_task_manager()
        task_info = manager.load_task_info('nonexistent_task_id')
        self.assertIsNone(task_info)
        print(f'[OK] 加载不存在的任务返回 None')
    
    def test_update_nonexistent_chapter(self):
        """测试更新不存在的章节"""
        print('\n' + '='*60)
        print('[TEST] 测试更新不存在的章节')
        print('='*60)

        manager = get_task_manager()
        task_id = manager.create_task(template_type='test')

        # 尝试更新不存在的章节
        try:
            manager.update_chapter_status(task_id, 999, status='completed')
            print(f'[OK] 更新不存在的章节未抛出异常')
        except Exception as e:
            print(f'[WARN] 更新不存在的章节抛出异常：{e}')

        # 清理
        import shutil
        task_dir = manager._get_task_directory(task_id)
        if os.path.exists(task_dir):
            shutil.rmtree(task_dir)

    def test_task_monitor_api_format(self):
        """测试 10: 任务监控中心 API 数据格式验证"""
        print('\n' + '='*60)
        print('[TEST] 测试任务监控中心 API 数据格式')
        print('='*60)

        manager = get_task_manager()
        task_id = manager.create_task(
            template_type='future_community',
            user_prompt='测试任务监控数据格式',
            model='qwen-max'
        )

        # 初始化章节列表
        chapter_titles = ['第 1 章 项目概况', '第 2 章 建设背景', '第 3 章 建设必要性']
        manager.initialize_chapters(task_id, chapter_titles)

        # ========== 场景 1: 任务刚开始，所有章节都是 pending ==========
        print('\n--- 场景 1: 任务刚开始 ---')
        status = manager.get_task_status(task_id)
        
        # 验证返回数据格式
        self.assertIn('task_id', status)
        self.assertIn('status', status)
        self.assertIn('progress', status)
        self.assertIn('current_chapter', status)
        self.assertIn('total_chapters', status)
        self.assertIn('completed_chapters', status)
        self.assertIn('chapters', status)
        print(f'[OK] 返回数据格式正确')
        
        # 验证字段类型
        self.assertIsInstance(status['completed_chapters'], int, 'completed_chapters 应该是整数')
        self.assertIsInstance(status['total_chapters'], int, 'total_chapters 应该是整数')
        print(f'[OK] completed_chapters 和 total_chapters 类型正确')
        
        # 验证初始值
        self.assertEqual(status['completed_chapters'], 0, '初始完成章节数应为 0')
        self.assertEqual(status['total_chapters'], 3, '总章节数应为 3')
        self.assertIsNone(status['current_chapter'], '初始当前章节应为 None')
        print(f'[OK] 初始值正确：completed={status["completed_chapters"]}, total={status["total_chapters"]}, current={status["current_chapter"]}')

        # ========== 场景 2: 正在生成第 1 章 ==========
        print('\n--- 场景 2: 正在生成第 1 章 ---')
        manager.update_task_status(task_id, status='generating', current_chapter_index=0)
        manager.update_chapter_status(task_id, 0, status='generating')
        
        status = manager.get_task_status(task_id)
        self.assertEqual(status['current_chapter'], '第 1 章 项目概况', '当前章节应该是第 1 章')
        self.assertEqual(status['completed_chapters'], 0, '完成章节数应为 0')
        print(f'[OK] 生成中状态正确：current={status["current_chapter"]}, completed={status["completed_chapters"]}')

        # ========== 场景 3: 第 1 章完成，开始生成第 2 章 ==========
        print('\n--- 场景 3: 第 1 章完成，开始生成第 2 章 ---')
        manager.update_chapter_status(task_id, 0, status='completed', content='第 1 章内容', word_count=100)
        manager.update_task_status(task_id, current_chapter_index=1)
        manager.update_chapter_status(task_id, 1, status='generating')
        
        status = manager.get_task_status(task_id)
        self.assertEqual(status['current_chapter'], '第 2 章 建设背景', '当前章节应该是第 2 章')
        self.assertEqual(status['completed_chapters'], 1, '完成章节数应为 1')
        print(f'[OK] 第 1 章完成后状态正确：current={status["current_chapter"]}, completed={status["completed_chapters"]}')

        # ========== 场景 4: 第 2 章完成，开始生成第 3 章 ==========
        print('\n--- 场景 4: 第 2 章完成，开始生成第 3 章 ---')
        manager.update_chapter_status(task_id, 1, status='completed', content='第 2 章内容', word_count=200)
        manager.update_task_status(task_id, current_chapter_index=2)
        manager.update_chapter_status(task_id, 2, status='generating')
        
        status = manager.get_task_status(task_id)
        self.assertEqual(status['current_chapter'], '第 3 章 建设必要性', '当前章节应该是第 3 章')
        self.assertEqual(status['completed_chapters'], 2, '完成章节数应为 2')
        self.assertEqual(status['progress'], 66, '进度应为 66%')
        print(f'[OK] 第 2 章完成后状态正确：current={status["current_chapter"]}, completed={status["completed_chapters"]}, progress={status["progress"]}%')

        # ========== 场景 5: 所有章节完成 ==========
        print('\n--- 场景 5: 所有章节完成 ---')
        manager.update_chapter_status(task_id, 2, status='completed', content='第 3 章内容', word_count=150)
        
        status = manager.get_task_status(task_id)
        self.assertEqual(status['completed_chapters'], 3, '完成章节数应为 3')
        self.assertEqual(status['total_chapters'], 3, '总章节数应为 3')
        self.assertEqual(status['status'], 'completed', '任务状态应为 completed')
        # 所有章节完成后，current_chapter 应该为 None 或最后一章
        self.assertIn(status['current_chapter'], [None, '第 3 章 建设必要性'], '完成后当前章节应为 None 或最后一章')
        print(f'[OK] 任务完成状态正确：completed={status["completed_chapters"]}/{status["total_chapters"]}, status={status["status"]}')

        # ========== 场景 6: 验证前端计算公式 ==========
        print('\n--- 场景 6: 验证前端显示公式 ---')
        # 前端使用：`${task.completed_chapters}/${task.total_chapters}`
        # 这应该显示为 "3/3"
        display_text = f'{status["completed_chapters"]}/{status["total_chapters"]}'
        self.assertEqual(display_text, '3/3', '前端应显示 "3/3"')
        print(f'[OK] 前端显示公式验证通过：{display_text}')

        # 清理
        import shutil
        task_dir = manager._get_task_directory(task_id)
        if os.path.exists(task_dir):
            shutil.rmtree(task_dir)
        print(f'\n[CLEANUP] 测试数据已清理')


if __name__ == '__main__':
    print('\n' + '='*60)
    print('  任务管理器测试用例 (SKILL-008)')
    print('='*60)
    
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试
    suite.addTests(loader.loadTestsFromTestCase(TestTaskManager))
    suite.addTests(loader.loadTestsFromTestCase(TestTaskManagerEdgeCases))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出结果
    print('\n' + '='*60)
    print('  测试结果')
    print('='*60)
    print(f'  运行：{result.testsRun} 个测试')
    print(f'  成功：{result.testsRun - len(result.failures) - len(result.errors)} 个')
    print(f'  失败：{len(result.failures)} 个')
    print(f'  错误：{len(result.errors)} 个')
    print('='*60 + '\n')
    
    # 退出码
    sys.exit(0 if result.wasSuccessful() else 1)
