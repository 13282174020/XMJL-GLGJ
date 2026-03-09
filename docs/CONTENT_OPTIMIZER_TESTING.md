# 内容优化功能测试说明

## 概述

内容优化模块 (`content_optimizer.py`) 提供了三大核心功能：

1. **Few-shot 示例库** - 为常见章节类型提供优质示例
2. **章节类型识别** - 自动识别章节类型并应用针对性策略
3. **内容去重检测** - 检测章节间重复内容

## 运行测试

### 方法 1: 运行完整测试套件

```bash
cd e:\Qwen\xmjl\web_system
python tests\test_content_optimizer.py
```

测试将验证：
- 章节类型识别准确性（10 种章节类型）
- Few-shot 示例库完整性（10 个示例）
- 内容去重检测功能（相似度算法）
- Prompt 增强集成（类型指导+Few-shot 示例）
- 关键词映射配置（CHAPTER_TYPE_MAP）

### 方法 2: 直接运行模块测试

```bash
cd e:\Qwen\xmjl\web_system
python services\content_optimizer.py
```

这将运行模块内置的快速测试。

### 方法 3: 在 Python 中交互式测试

```python
from services.content_optimizer import ContentOptimizer

# 创建优化器实例
optimizer = ContentOptimizer()

# 测试章节类型识别
result = optimizer.identify_section_type('政策法规依据')
print(f"类型：{result['type']}")      # 输出：list
print(f"子类型：{result['subtype']}")  # 输出：list_policy

# 获取 Few-shot 示例
example = optimizer.get_example_for_section('项目概况')
if example:
    print(f"示例：{example.section_title}")
    print(f"内容：{example.example_content[:100]}...")

# 测试内容去重
optimizer.add_generated_content('项目概况', '项目名称：测试项目，总投资 100 万元。')
duplicate = '项目名称为测试项目，总投资额 100 万元。'
result = optimizer.check_duplicate(duplicate)
print(f"是否重复：{result['is_duplicate']}")  # 输出：True
print(f"相似度：{result['duplicate_sections'][0]['similarity']:.1%}")  # 输出：约 85%
```

## 功能详解

### 1. Few-shot 示例库

内置 10 种章节类型的示例：

| 类型 | 子类型 | 示例章节 |
|------|--------|----------|
| 列表型 | list_policy | 政策法规依据 |
| 列表型 | list_tech_standard | 技术规范标准 |
| 列表型 | list_problems | 现状问题分析 |
| 列表型 | list_requirements | 项目建设需求 |
| 描述型 | desc_project_overview | 项目概况 |
| 描述型 | desc_project_background | 项目背景 |
| 描述型 | desc_construction_objectives | 项目建设目标 |
| 描述型 | desc_technical_solution | 技术方案概述 |
| 表格型 | table_investment | 投资估算 |
| 表格型 | table_schedule | 建设进度计划 |

每个示例包含：
- 格式特征（4 条）
- 示例内容（200-400 字）
- 生成技巧（3 条）

### 2. 章节类型识别

基于标题关键词自动识别章节类型：

```python
# 识别章节类型
result = optimizer.identify_section_type('技术方案概述')
print(result)
# 输出：
# {
#     'section_title': '技术方案概述',
#     'type': 'desc',           # 描述型
#     'subtype': 'desc_technical_solution',
#     'format_strategy': '使用连贯的段落描述，语言简洁专业',
#     'prompt_guidance': '...',
#     'matched_keywords': ['方案']
# }
```

**注意**：映射表顺序很重要！更具体的规则应该放在前面。
例如，"技术方案概述"优先匹配"方案"（描述型），而不是"技术"（列表型）。

### 3. 内容去重检测

使用 SequenceMatcher 算法检测重复内容：

```python
# 添加历史内容
optimizer.add_generated_content('章节 1', '内容 A')

# 检测新内容是否重复
result = optimizer.check_duplicate('内容 B', threshold=0.6)
print(result)
# 输出：
# {
#     'is_duplicate': True/False,
#     'duplicate_sections': [{'section_title': '章节 1', 'similarity': 0.85}],
#     'similarity_scores': [...],
#     'suggestion': '...'
# }
```

**参数说明**：
- `threshold`: 重复度阈值（0-1），默认 0.6（60% 相似度）
- 相似度 > 阈值 认为重复

## 集成到 AI 引擎

内容优化功能已集成到 `ai_engine.py`：

1. **Prompt 增强**：在 `build_desc_field_prompt()` 中自动注入
   - 章节类型识别结果
   - Few-shot 示例
   - 格式策略指导

2. **内容去重**：在 `generate_section_content_with_ai()` 中检测
   - 每章生成后自动检测重复
   - 记录到历史但不阻止生成
   - 由后续审校处理

## 自定义扩展

### 添加新的章节类型示例

```python
from services.content_optimizer import SectionExample, FEW_SHOT_EXAMPLES

# 创建新示例
new_example = SectionExample(
    section_type='列表型',
    section_title='风险评估',
    description='列举项目可能面临的风险',
    format_features=[
        '使用数字编号列表',
        '每条包含风险名称和应对措施'
    ],
    example_content='''1. 技术风险
   - 新技术应用可能存在不确定性
   - 应对措施：选择成熟技术，进行充分测试

2. 管理风险
   - 项目周期长，人员可能变动
   - 应对措施：建立文档管理制度，确保知识传承''',
    tips=[
        '按风险严重程度排序',
        '每条风险都要有应对措施'
    ]
)

# 添加到示例库
FEW_SHOT_EXAMPLES['list_risks'] = new_example
```

### 添加关键词映射

```python
from services.content_optimizer import CHAPTER_TYPE_MAP

# 添加新的映射规则（注意顺序！）
CHAPTER_TYPE_MAP['list_risks'] = ['风险', '评估', '应对']
```

## 常见问题

### Q: 为什么某些章节识别不准确？

A: 检查 `CHAPTER_TYPE_MAP` 中的关键词映射。如果标题包含多个关键词，可能匹配到错误的类型。解决方法：
1. 调整映射表顺序，让更具体的规则优先
2. 使用更独特的关键词

### Q: 如何调整去重检测的灵敏度？

A: 修改 `check_duplicate()` 的 `threshold` 参数：
- `threshold=0.5`：更宽松（50% 相似度即认为重复）
- `threshold=0.7`：更严格（70% 相似度才认为重复）

### Q: Few-shot 示例没有生效？

A: 检查：
1. 章节标题是否匹配示例库中的关键词
2. 使用 `get_example_for_section()` 确认是否返回示例
3. 确认 Prompt 中包含"参考示例"部分

## 测试通过标准

所有测试应该通过：
- [x] 章节类型识别 - 11/11 通过
- [x] Few-shot 示例 - 14/14 通过
- [x] 内容去重检测 - 5/5 通过
- [x] Prompt 增强 - 3/3 通过
- [x] 关键词映射 - 1/1 通过

总计：**5/5 测试通过**
