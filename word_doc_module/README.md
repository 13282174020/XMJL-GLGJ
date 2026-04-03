# Word 文档 AI 生成模块

一个独立的 Python 模块，用于实现：
1. **Word 模板扫描** - 提取章节结构、样式信息
2. **Word 样式设置** - 设置标题字体、段落格式、大纲级别
3. **AI 章节生成** - 调用 AI 根据需求文档和模板生成章节内容

---

## 目录

- [快速开始](#快速开始)
- [安装依赖](#安装依赖)
- [模块结构](#模块结构)
- [使用指南](#使用指南)
  - [模板扫描](#模板扫描)
  - [样式设置](#样式设置)
  - [AI 生成](#ai-生成)
  - [Prompt 架构](#prompt-架构)
- [AI 编码工具接入指南](#ai-编码工具接入指南)
- [API 参考](#api-参考)
- [自定义扩展](#自定义扩展)
- [常见问题](#常见问题)

---

## 快速开始

### 5 分钟上手

```python
from word_doc_module import TemplateScanner, StyleManager, AIChapterGenerator, ModelConfig

# 1. 配置 AI 模型
config = ModelConfig(
    model='qwen-max',
    api_key='your-api-key',
    base_url='https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation',
)

# 2. 扫描模板
scanner = TemplateScanner()
result = scanner.scan('template.docx')
chapters = result['chapters_flat']
print(f"发现 {len(chapters)} 个章节")

# 3. 创建 AI 生成器
generator = AIChapterGenerator(
    model_config=config,
    requirement_text='项目名称：智慧社区\n总投资：500万元\n建设工期：12个月',
    template_text=scanner.get_template_text('template.docx')
)

# 4. 生成章节内容
for chapter in chapters:
    content = generator.generate(section_title=chapter['title'])
    print(f"生成章节：{chapter['title']}")

# 5. 生成 Word 文档
manager = StyleManager()
doc = manager.create_document()
manager.add_cover_title(doc, '智慧社区可行性研究报告')
manager.add_page_break(doc)

for chapter in chapters:
    manager.add_heading(doc, chapter['title'], level=chapter['level'])
    content = generator.generate(section_title=chapter['title'])
    manager.add_normal_paragraph(doc, content)

manager.apply_styles_to_document(doc)
doc.save('output.docx')
```

---

## 安装依赖

```bash
pip install python-docx requests
```

> **注意**：python-docx 用于 Word 文档操作，requests 用于 AI API 调用。如果你使用其他 HTTP 库，可以自行修改 `ai_engine.py` 中的 `_call_api` 方法。

---

## 模块结构

```
word_doc_module/
├── __init__.py              # 模块入口
├── template_scanner.py      # 模板扫描：提取章节结构、样式信息
├── style_manager.py         # 样式管理：设置字体、段落、大纲级别
├── ai_engine.py             # AI 引擎：Prompt 构建、API 调用、输出清理
├── services/
│   ├── __init__.py
│   ├── content_optimizer.py # 章节类型识别、Few-shot 示例
│   ├── requirement_analyzer.py # 需求点提取与映射
│   └── data_point_manager.py # 数据点一致性管理
└── README.md
```

---

## 使用指南

### 模板扫描

从 Word 模板中提取章节结构：

```python
from word_doc_module import TemplateScanner

scanner = TemplateScanner()

# 扫描模板文件
result = scanner.scan('template.docx')

# 获取章节树（嵌套结构）
for chapter in result['chapters']:
    print(f"{'#' * chapter['level']} {chapter['number']} {chapter['title']}")
    for child in chapter.get('children', []):
        print(f"  {'#' * child['level']} {child['title']}")

# 获取展平的章节列表
for chapter in result['chapters_flat']:
    print(f"Level {chapter['level']}: {chapter['title']}")

# 获取模板全文（用于 AI 生成时参考）
template_text = scanner.get_template_text('template.docx')
```

**支持的章节标题格式**：
- 数字编号：`1.1`, `1.2.3`, `1.2.3.4`
- 中文章节：`第一章`, `第一节`, `第1章`
- 括号编号：`(一)`, `(1)`, `【标题】`

**返回结果**：
```python
{
    'success': True,
    'chapters': [          # 嵌套树结构
        {
            'level': 1,
            'number': '第一章',
            'title': '项目概况',
            'style': 'Heading 1',
            'children': [
                {'level': 2, 'number': '1.1', 'title': '项目背景', ...}
            ]
        }
    ],
    'chapters_flat': [...],  # 展平列表
    'styles_usage': {...},   # 样式使用统计
    'total_paragraphs': 150,
    'heading_count': 20
}
```

---

### 样式设置

创建带样式的 Word 文档：

```python
from word_doc_module import StyleManager, Document

manager = StyleManager()

# 创建文档
doc = manager.create_document()

# 添加封面标题
manager.add_cover_title(doc, '智慧社区可行性研究报告', font_size=36)
manager.add_page_break(doc)

# 添加章节标题
manager.add_heading(doc, '第一章 项目概况', level=1)
manager.add_heading(doc, '1.1 项目背景', level=2)
manager.add_heading(doc, '1.2 建设必要性', level=2)

# 添加正文（自动首行缩进）
manager.add_normal_paragraph(doc, '随着城镇化进程加快...')
manager.add_normal_paragraph(doc, '本项目的建设具有以下意义...')

# 添加表格
table = manager.add_table(doc, rows=3, cols=3)
table.cell(0, 0).text = '序号'
table.cell(0, 1).text = '项目'
table.cell(0, 2).text = '金额'

# 应用样式（设置大纲级别，支持自动目录）
manager.apply_styles_to_document(doc)

# 保存
doc.save('output.docx')
```

**默认样式配置**：

| 样式 | 字体 | 字号 | 对齐 | 特性 |
|------|------|------|------|------|
| heading1 | 黑体 | 22pt | 居中 | 加粗 |
| heading2 | 楷体 | 16pt | 左对齐 | 加粗 |
| heading3 | 楷体 | 14pt | 左对齐 | 加粗 |
| normal | 仿宋 | 10.5pt | 左对齐 | 首行缩进、行距1.5 |

**自定义样式**：

```python
custom_styles = {
    'heading1': {'font_name': '微软雅黑', 'font_size': 24, 'bold': True},
    'normal': {'font_name': '宋体', 'font_size': 12},
}

manager = StyleManager(custom_styles=custom_styles)
```

---

### AI 生成

#### 基本用法

```python
from word_doc_module import AIChapterGenerator, ModelConfig

# 配置模型
config = ModelConfig(
    model='qwen-max',
    api_key='your-api-key',
    base_url='https://api.example.com/v1/chat/completions',
)

# 创建生成器
generator = AIChapterGenerator(
    model_config=config,
    requirement_text=open('requirement.txt').read(),
    template_text=open('template.txt').read()
)

# 生成单个章节
content = generator.generate(
    section_title='项目概况',
    user_instruction='请突出智慧社区的特点'
)

# 批量生成
for chapter in chapters:
    content = generator.generate(section_title=chapter['title'])
    print(f"✓ {chapter['title']}")
```

#### 自定义 API 调用

如果你的 AI API 不是 OpenAI 兼容格式，可以自定义调用函数：

```python
def my_api_call(prompt):
    # 你的自定义 API 调用逻辑
    response = your_http_client.post(
        url='your-api-endpoint',
        json={'prompt': prompt}
    )
    return response.content

# 使用自定义调用函数
content = generator.generate(
    section_title='项目概况',
    api_call_func=my_api_call
)
```

---

### Prompt 架构

AI 生成章节内容的 Prompt 包含以下关键组件：

#### 1. 角色设定

```
你是一位专业的可行性研究报告编写专家。
```

#### 2. 任务说明

```
【任务】请为【{章节标题}】这一章节撰写内容。
```

#### 3. 约束规则

```
【重要提示】
- **内容来源**：必须严格基于【需求文档内容】
- **模板用途**：仅用于学习格式，不要复制业务信息
- **输出格式**：直接输出正文，不要 Markdown、不要思考过程
```

#### 4. 项目上下文

```python
# 自动识别项目类型和业务场景
project_type = extract_project_type(requirement_text)  # "智慧社区"
business_scenes = extract_business_scenes(requirement_text)  # ["智慧安防", "人员管理"]
```

#### 5. 数据点注入

```
【已确立的关键数据】
- 项目名称：智慧社区管理平台
- 总投资：500 万元
- 建设工期：12 个月
```

#### 6. 需求点映射

```
【本章应回应的需求点】
1. 视频监控全覆盖
2. 流动人口管理
3. 智能安防预警
```

#### 7. Few-shot 示例

```
【参考示例】
以下是「政策法规依据」的示例：
1. 《中华人民共和国网络安全法》（2017年7月1日施行）
   - 为网络安全提供了法律保障...
...
【示例要点】
- 优先列出国家法律法规
- 每条注明发布时间和核心要点
```

#### 8. 章节类型识别

自动识别章节类型并提供格式指导：

| 类型 | 关键词 | 格式策略 |
|------|--------|---------|
| 列表型 | 政策、法规、问题、需求 | 数字编号列表（1. 2. 3.） |
| 描述型 | 概况、背景、目标 | 连贯段落描述 |
| 表格型 | 投资、进度、计划 | 表格形式呈现 |

---

## AI 编码工具接入指南

### 给 AI 的上下文说明

当你需要 AI 编码工具帮你使用这个模块时，请提供以下说明：

#### 1. 模块功能概述

```
这是一个 Word 文档 AI 生成模块，包含三个核心功能：
1. 模板扫描：从 Word 模板提取章节结构
2. 样式设置：创建带样式的 Word 文档
3. AI 生成：调用 AI 根据需求和模板生成章节内容
```

#### 2. 文件位置

```
word_doc_module/
├── template_scanner.py    # 模板扫描
├── style_manager.py       # 样式管理
├── ai_engine.py           # AI 引擎
└── services/
    ├── content_optimizer.py    # 章节类型识别
    ├── requirement_analyzer.py # 需求分析
    └── data_point_manager.py   # 数据点管理
```

#### 3. 核心 API 用法

**模板扫描**：
```python
from word_doc_module import TemplateScanner
scanner = TemplateScanner()
result = scanner.scan('template.docx')
chapters = result['chapters_flat']  # 获取展平的章节列表
```

**样式设置**：
```python
from word_doc_module import StyleManager
manager = StyleManager()
doc = manager.create_document()
manager.add_heading(doc, '标题', level=1)
manager.add_normal_paragraph(doc, '正文内容')
manager.apply_styles_to_document(doc)
doc.save('output.docx')
```

**AI 生成**：
```python
from word_doc_module import AIChapterGenerator, ModelConfig
config = ModelConfig(model='your-model', api_key='...', base_url='...')
generator = AIChapterGenerator(config, requirement_text='...', template_text='...')
content = generator.generate(section_title='项目概况')
```

#### 4. 完整生成流程

```python
from word_doc_module import TemplateScanner, StyleManager, AIChapterGenerator, ModelConfig

# Step 1: 扫描模板
scanner = TemplateScanner()
template_result = scanner.scan('template.docx')
template_text = scanner.get_template_text('template.docx')

# Step 2: 配置 AI
config = ModelConfig(model='...', api_key='...', base_url='...')
generator = AIChapterGenerator(config, requirement_text=req_text, template_text=template_text)

# Step 3: 创建文档
manager = StyleManager()
doc = manager.create_document()

# Step 4: 生成内容
manager.add_cover_title(doc, '可行性研究报告')
manager.add_page_break(doc)

for chapter in template_result['chapters_flat']:
    # 生成章节内容
    content = generator.generate(section_title=chapter['title'])

    # 添加到文档
    manager.add_heading(doc, chapter['title'], level=chapter['level'])
    manager.add_normal_paragraph(doc, content)
    manager.add_page_break(doc)

# Step 5: 保存
manager.apply_styles_to_document(doc)
doc.save('output.docx')
```

---

## API 参考

### TemplateScanner

```python
class TemplateScanner:
    def scan(self, file_path=None, file_stream=None) -> Dict
        """扫描 Word 模板，返回章节结构"""

    def get_template_text(self, file_path=None, file_stream=None) -> str
        """获取模板全文文本"""
```

### StyleManager

```python
class StyleManager:
    def create_document(self, template_path=None) -> Document
        """创建 Word 文档"""

    def add_heading(self, doc, text, level=1) -> Paragraph
        """添加标题"""

    def add_normal_paragraph(self, doc, text, indent=True) -> Paragraph
        """添加正文段落"""

    def add_cover_title(self, doc, title, font_size=36) -> Paragraph
        """添加封面标题"""

    def add_page_break(self, doc)
        """添加分页符"""

    def add_table(self, doc, rows, cols, data=None) -> Table
        """添加表格"""

    def apply_styles_to_document(self, doc)
        """应用样式（设置大纲级别）"""
```

### AIChapterGenerator

```python
class AIChapterGenerator:
    def __init__(self, model_config, requirement_text='', template_text='')
        """初始化生成器"""

    def generate(self, section_title, requirement_text=None, template_text=None,
                user_instruction='', api_call_func=None) -> str
        """生成章节内容"""

    def reset(self)
        """重置状态"""
```

### ModelConfig

```python
class ModelConfig:
    def __init__(self, model='qwen-max', api_key='', base_url='',
                max_tokens=2000, temperature=0.7, **kwargs)
        """配置 AI 模型"""
```

---

## 自定义扩展

### 1. 添加新的章节类型和示例

编辑 `services/content_optimizer.py`：

```python
# 添加新示例
FEW_SHOT_EXAMPLES['my_custom'] = SectionExample(
    section_type='描述型',
    section_title='自定义章节',
    description='...',
    format_features=['...'],
    example_content='...',
    tips=['...']
)

# 添加类型映射
CHAPTER_TYPE_MAP['my_custom'] = ['关键词1', '关键词2']
```

### 2. 添加数据提取模式

编辑 `services/data_point_manager.py`：

```python
PATTERNS: Dict[str, List[str]] = {
    # ... 现有模式
    'my_data_type': [
        r'我的数据[\s:：]*([^\n]+)',  # 新模式
    ],
}
```

### 3. 自定义 Prompt

```python
from word_doc_module import build_desc_field_prompt, AIChapterGenerator

# 继承并覆盖 Prompt 构建
class MyGenerator(AIChapterGenerator):
    def generate(self, section_title, **kwargs):
        prompt = build_desc_field_prompt(
            section_title,
            self.requirement_text,
            self.template_text,
            user_instruction=kwargs.get('user_instruction', ''),
            dp_manager=self.dp_manager,
            req_analyzer=self.req_analyzer,
            optimizer=self.optimizer
        )
        # 添加自定义 Prompt 后缀
        prompt += "\n\n【额外要求】\n请使用更正式的语言风格。"

        content = self._call_api(prompt)
        return clean_ai_content(content, section_title)
```

---

## 常见问题

### Q: 如何支持其他 AI 模型？

A: 有三种方式：

1. **使用 OpenAI 兼容格式**（推荐）：
   ```python
   config = ModelConfig(
       model='your-model',
       api_key='your-key',
       base_url='https://api.openai.com/v1'
   )
   ```

2. **自定义 API 调用**：
   ```python
   def my_call(prompt):
       # 你的调用逻辑
       return result

   generator.generate(section_title='...', api_call_func=my_call)
   ```

3. **覆盖 `_call_api` 方法**：
   ```python
   class MyGenerator(AIChapterGenerator):
       def _call_api(self, prompt, max_tokens):
           # 自定义实现
           return your_api_call(prompt)
   ```

### Q: 如何设置中文字体？

A: 使用 `qn('w:eastAsia')` 设置中文字体：

```python
run._element.rPr.rFonts.set(qn('w:eastAsia'), '黑体')
```

支持的字体：`黑体`、`宋体`、`仿宋`、`楷体`、`微软雅黑` 等。

### Q: 如何让 Word 自动生成目录？

A: 调用 `apply_styles_to_document()` 设置大纲级别：

```python
manager.apply_styles_to_document(doc)
```

这会为 Heading 1-9 设置 `outlineLvl` 属性，Word 的目录功能会自动收集。

### Q: 生成的文档出现乱码？

A: 确保保存时指定编码：

```python
doc.save('output.docx')  # python-docx 默认 UTF-8
```

---

## 许可证

MIT License

---

## 更新日志

### v1.0.0 (2026-04-03)
- 初始版本
- 支持模板扫描、样式设置、AI 生成
- 内置需求分析、数据点管理、Few-shot 示例
