# 软件建设方案 AI 生成系统 - Skills 配置

> 版本：V2.0  
> 最后更新：2026 年 3 月

---

## Skills 总览

本系统包含以下核心 Skills，每个 Skill 对应一个独立的功能模块：

| Skill ID | 名称 | 说明 | 负责人 |
|----------|------|------|--------|
| SKILL-001 | 文档解析技能 | 解析 Word 文档，提取文本和结构信息 | 系统核心 |
| SKILL-002 | 信息提取技能 | 从需求文档中提取结构化项目信息 | AI 引擎 |
| SKILL-003 | 模板分析技能 | 分析模板文档的章节结构 | AI 引擎 |
| SKILL-004 | 章节生成技能 | 逐章生成方案内容 | AI 引擎 |
| SKILL-005 | 数据点管理技能 | 维护和管理全局数据点字典 | AI 引擎 |
| SKILL-006 | 质量审校技能 | 审校生成内容的质量和一致性 | AI 引擎 |
| SKILL-007 | 文档渲染技能 | 将 JSON 渲染为 Word 文档 | 文档引擎 |
| SKILL-008 | 任务管理技能 | 管理生成任务的全生命周期 | 后端服务 |
| SKILL-009 | Prompt 管理技能 | 管理 Prompt 模板库 | AI 引擎 |
| SKILL-010 | 示例库管理技能 | 管理 Few-shot 示例库 | AI 引擎 |

---

## SKILL-001: 文档解析技能

### 功能描述
解析用户上传的 Word 文档，提取文本内容、表格数据、标题层级等信息。

### 输入
- 文件路径：`str` - Word 文档的绝对路径
- 文件类型：`str` - `requirement`（需求文档）或`template`（模板文档）

### 输出
- 提取的文本内容：`str`
- 段落层级信息：`List[Dict]`
- 表格数据：`List[Dict]`

### 处理流程
1. 使用 python-docx 打开文档
2. 遍历所有段落，提取文本和样式信息
3. 识别标题层级（通过样式名或字体大小）
4. 提取表格数据（如果有）
5. 处理超长文档（超过 12 万字符时分段）

### 代码位置
`backend/app/services/document_parser.py`

### 依赖
- python-docx >= 1.1.0

### 测试用例
- 正常文档解析
- 空文档处理
- 超长文档分段
- 含表格文档解析

---

## SKILL-002: 信息提取技能

### 功能描述
调用 LLM 从需求文档中提取结构化的项目信息。

### 输入
- 需求文档文本：`str`
- JSON Schema：`Dict` - 定义输出格式

### 输出
```json
{
  "project_info": {
    "name": "项目名称",
    "location": "项目地点",
    "scale": "建设规模",
    "population": "服务人口",
    "budget": "投资预算"
  },
  "org_info": {
    "org_name": "建设单位名称",
    "contacts": "联系人",
    "responsibilities": "职责"
  },
  "pain_points": ["痛点 1", "痛点 2", ...],
  "requirements": ["需求 1", "需求 2", ...],
  "constraints": ["约束 1", "约束 2", ...],
  "special_notes": ["特殊说明 1", ...]
}
```

### Prompt 模板
`prompts/extract_requirements.j2`

### 代码位置
`backend/app/services/ai_engine.py`

### 依赖
- LLM API（通义千问/GPT-4o 等）
- Jinja2 >= 3.1

### 测试用例
- 完整需求文档提取
- 信息不足时的处理
- 超长文档分批提取

---

## SKILL-003: 模板分析技能

### 功能描述
调用 LLM 分析模板文档的章节结构，输出章节结构树。

### 输入
- 模板文档文本：`str`

### 输出
```json
{
  "chapters": [
    {
      "number": "第一章",
      "title": "项目概况",
      "level": 1,
      "subsections": [
        {
          "number": "1.1",
          "title": "项目名称",
          "level": 2,
          "content_type": "text",
          "estimated_words": 50
        }
      ]
    }
  ]
}
```

### Prompt 模板
`prompts/analyze_template.j2`

### 代码位置
`backend/app/services/ai_engine.py`

### 测试用例
- 标准模板分析
- 复杂嵌套结构分析
- 非标准编号规则处理

---

## SKILL-004: 章节生成技能

### 功能描述
按照章节结构树，逐章调用 LLM 生成内容。

### 输入
- 项目上下文信息：`Dict`
- 当前章节要求：`Dict`
- 已确立的数据点：`Dict`
- 前文摘要：`str`
- 用户补充要求：`str`

### 输出
```json
{
  "chapter_number": "第五章",
  "chapter_title": "项目建设方案",
  "subsections": [
    {
      "number": "5.1",
      "title": "总体思路",
      "level": 2,
      "type": "text",
      "paragraphs": ["段落 1", "段落 2", ...]
    },
    {
      "number": "5.3.1",
      "title": "未来邻里场景",
      "level": 3,
      "type": "mixed",
      "paragraphs": ["段落 1"],
      "table_data": {
        "headers": ["序号", "建设内容", "说明"],
        "rows": [["1", "共享书房", "配备智能借阅系统..."]]
      }
    }
  ]
}
```

### Prompt 模板
`prompts/generate_chapter.j2`

### 代码位置
`backend/app/services/chapter_generator.py`

### 核心机制
- **数据点传递**：每章生成后提取关键数据，后续章节保持一致
- **前文摘要**：压缩已生成章节的核心内容，作为上下文传入
- **Few-shot 示例**：根据章节类型匹配最相关的示例

### 测试用例
- 纯文本章节生成
- 含表格章节生成
- 数据一致性验证
- 超长章节生成

---

## SKILL-005: 数据点管理技能

### 功能描述
维护全局数据点字典，确保全文数据一致性。

### 输入
- 当前章节内容：`Dict`

### 输出
- 更新后的数据点字典：`Dict`

### 数据点类型
```json
{
  "total_investment": "1200 万元",
  "hardware_cost": "480 万元",
  "software_cost": "320 万元",
  "population": "约 1.1 万人",
  "households": "3000 余户",
  "construction_period": "12 个月",
  "camera_count": "约 200 路",
  "energy_saving_target": "降低 20% 以上"
}
```

### 提取规则
- 金额：XX 万元、XX 亿元
- 数量：约 XX 个、XX 余户
- 百分比：XX%、降低/提升 XX%
- 时间：XX 个月、XX 年

### 代码位置
`backend/app/services/data_point_manager.py`

### 测试用例
- 数据点提取
- 数据点更新
- 数据冲突检测

---

## SKILL-006: 质量审校技能

### 功能描述
对生成的全文内容进行质量审校，检查数据一致性、需求覆盖度、逻辑完整性等。

### 审校维度

| 维度 | 检查内容 | 处理方式 |
|------|----------|----------|
| 数据一致性 | 金额、数量、百分比前后是否一致 | 自动修正为数据点字典中的值 |
| 需求覆盖度 | 需求文档中的每个要点是否有回应 | 标记未覆盖项，补充生成 |
| 逻辑完整性 | 论述是否存在逻辑跳跃 | 标记问题点，重新生成 |
| 专业规范性 | 术语使用是否准确 | 标记并建议修正 |
| 字数达标 | 各章节字数是否达到要求 | 不达标的章节扩写补充 |

### Prompt 模板
- `prompts/review_consistency.j2` - 数据一致性审校
- `prompts/review_coverage.j2` - 需求覆盖度审校
- `prompts/review_quality.j2` - 整体质量审校

### 代码位置
`backend/app/services/quality_reviewer.py`

### 测试用例
- 数据不一致检测与修正
- 需求覆盖度检查
- 逻辑问题检测

---

## SKILL-007: 文档渲染技能

### 功能描述
将结构化 JSON 内容渲染为格式化的 Word 文档。

### 输入
- 章节内容 JSON：`Dict`
- 样式配置：`Dict`
- 模板路径：`str`

### 输出
- Word 文档路径：`str`

### DocBuilder 核心接口

| 方法 | 参数 | 说明 |
|------|------|------|
| `__init__(template_path)` | template_path: str | 加载 Word 样式模板 |
| `add_cover(project_info)` | project_info: dict | 生成封面页 |
| `add_toc(chapters)` | chapters: list | 生成目录页 |
| `add_chapter(title)` | title: str | 添加章标题 |
| `add_section(title)` | title: str | 添加节标题 |
| `add_subsection(title)` | title: str | 添加小节标题 |
| `add_body(text)` | text: str | 添加正文段落 |
| `add_table(headers, rows)` | headers: list, rows: list | 添加格式化表格 |
| `add_page_break()` | 无 | 添加分页符 |
| `save(output_path)` | output_path: str | 保存 docx 文件 |

### 样式配置示例
```json
{
  "page": {
    "width_cm": 21,
    "height_cm": 29.7,
    "top_margin_cm": 2.54,
    "bottom_margin_cm": 2.54,
    "left_margin_cm": 3.17,
    "right_margin_cm": 3.17
  },
  "styles": {
    "chapter_title": {
      "font": "黑体",
      "size_pt": 16,
      "bold": true,
      "alignment": "center",
      "space_before_pt": 18,
      "space_after_pt": 12
    },
    "body_text": {
      "font": "仿宋",
      "size_pt": 12,
      "bold": false,
      "alignment": "justify",
      "first_indent_chars": 2,
      "line_spacing": 1.5
    }
  }
}
```

### 代码位置
`backend/app/utils/doc_builder.py`

### 测试用例
- 封面生成
- 目录生成
- 正文渲染
- 表格渲染
- 完整文档渲染

---

## SKILL-008: 任务管理技能

### 功能描述
管理文档生成任务的全生命周期，包括任务创建、状态跟踪、进度推送等。

### 任务状态

| 状态 | 说明 |
|------|------|
| pending | 等待处理 |
| parsing | 文档解析中 |
| analyzing | 模板分析中 |
| generating | 章节生成中 |
| reviewing | 质量审校中 |
| rendering | 文档渲染中 |
| completed | 已完成 |
| failed | 失败 |
| cancelled | 已取消 |

### 核心接口

| 接口 | 方法 | 说明 |
|------|------|------|
| 创建任务 | POST /api/v1/tasks | 创建新的生成任务 |
| 查询状态 | GET /api/v1/tasks/{id} | 获取任务详情和进度 |
| 进度推送 | GET /api/v1/tasks/{id}/progress | SSE 实时推送进度 |
| 取消任务 | POST /api/v1/tasks/{id}/cancel | 取消正在执行的任务 |
| 重试任务 | POST /api/v1/tasks/{id}/retry | 重试失败的任务 |

### 代码位置
`backend/app/services/task_manager.py`

### 测试用例
- 任务创建
- 状态查询
- 任务取消
- 任务重试

---

## SKILL-009: Prompt 管理技能

### 功能描述
管理所有 LLM 使用的 Prompt 模板，支持参数化、版本化、A/B 测试。

### Prompt 模板目录
```
backend/app/prompts/
├── extract_requirements.j2
├── analyze_template.j2
├── generate_chapter.j2
├── generate_chapter_table.j2
├── extract_data_points.j2
├── review_consistency.j2
├── review_coverage.j2
└── review_quality.j2
```

### 核心功能
- Jinja2 模板渲染
- 模板版本管理
- 模板热更新
- A/B 测试支持

### 代码位置
`backend/app/services/prompt_manager.py`

### 测试用例
- 模板加载
- 模板渲染
- 变量替换

---

## SKILL-010: 示例库管理技能

### 功能描述
管理 Few-shot 示例库，支持示例的上传、分类、检索、启用/禁用。

### 示例分类

| 章节类型 | 示例特征 | 示例来源 |
|----------|----------|----------|
| 背景必要性类 | 政策引用准确、逻辑层次清晰 | 优秀项目方案摘选 |
| 需求分析类 | 问题描述具体、数据引用充分 | 优秀项目方案摘选 |
| 技术方案类 | 方案描述详实、技术选型有依据 | 优秀项目方案摘选 |
| 投资估算类 | 数据精确、分类合理、前后一致 | 优秀项目方案摘选 |
| 效益分析类 | 量化指标明确、逻辑链完整 | 优秀项目方案摘选 |

### 核心接口

| 接口 | 方法 | 说明 |
|------|------|------|
| 示例列表 | GET /api/v1/examples | 获取示例列表 |
| 添加示例 | POST /api/v1/examples | 添加新示例 |
| 更新示例 | PUT /api/v1/examples/{id} | 更新示例内容 |
| 删除示例 | DELETE /api/v1/examples/{id} | 删除示例 |
| 启用/禁用 | POST /api/v1/examples/{id}/toggle | 切换启用状态 |

### 代码位置
`backend/app/services/example_manager.py`

### 测试用例
- 示例检索
- 示例匹配
- 示例 CRUD

---

## Skill 调用关系图

```
                    ┌─────────────────┐
                    │  用户发起任务   │
                    └────────┬────────┘
                             ↓
                    ┌─────────────────┐
                    │  SKILL-008      │
                    │  任务管理技能   │
                    └────────┬────────┘
                             ↓
           ┌─────────────────┼─────────────────┐
           ↓                 ↓                 ↓
    ┌────────────┐   ┌────────────┐   ┌────────────┐
    │ SKILL-001  │   │ SKILL-002  │   │ SKILL-003  │
    │ 文档解析   │   │ 信息提取   │   │ 模板分析   │
    └────────────┘   └────────────┘   └────────────┘
                             ↓
                    ┌─────────────────┐
                    │  SKILL-009      │
                    │  Prompt 管理    │
                    └────────┬────────┘
                             ↓
           ┌─────────────────┼─────────────────┐
           ↓                 ↓                 ↓
    ┌────────────┐   ┌────────────┐   ┌────────────┐
    │ SKILL-004  │   │ SKILL-005  │   │ SKILL-010  │
    │ 章节生成   │   │ 数据点管理 │   │ 示例库管理 │
    └────────────┘   └────────────┘   └────────────┘
                             ↓
                    ┌─────────────────┐
                    │  SKILL-006      │
                    │  质量审校       │
                    └────────┬────────┘
                             ↓
                    ┌─────────────────┐
                    │  SKILL-007      │
                    │  文档渲染       │
                    └─────────────────┘
```

---

## Skill 开发规范

### 1. 接口定义
每个 Skill 必须有清晰的输入输出定义

### 2. 测试覆盖
每个 Skill 必须有对应的测试用例

### 3. 错误处理
每个 Skill 必须有完善的异常处理

### 4. 日志记录
每个 Skill 必须记录关键操作日志

### 5. 文档说明
每个 Skill 必须有详细的文档说明

---

**编制单位：** 系统开发团队  
**生效日期：** 2026 年 3 月
