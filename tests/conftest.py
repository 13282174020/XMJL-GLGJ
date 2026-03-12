# -*- coding: utf-8 -*-
"""pytest 配置文件"""
import pytest
from pathlib import Path
import sys

# 添加项目根目录和 web_system 到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / 'web_system'))

# 测试数据目录
TEST_DATA_DIR = Path(__file__).parent / 'fixtures'


@pytest.fixture
def test_data_dir():
    """返回测试数据目录路径"""
    return TEST_DATA_DIR


@pytest.fixture
def sample_standard_doc(test_data_dir):
    """标准格式样本文档（使用 Heading 1-6 样式）"""
    return test_data_dir / 'sample_standard.docx'


@pytest.fixture
def sample_nonstandard_doc(test_data_dir):
    """非标准格式样本文档（使用自定义样式）"""
    return test_data_dir / 'sample_nonstandard.docx'


@pytest.fixture
def output_dir(tmp_path):
    """测试输出目录"""
    output = tmp_path / 'output'
    output.mkdir(exist_ok=True)
    return output
