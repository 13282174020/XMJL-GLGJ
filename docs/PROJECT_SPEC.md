# 软件建设方案 AI 生成系统 - 项目开发规范

> 版本：V2.0  
> 最后更新：2026 年 3 月  
> 状态：强制执行

---

## 一、核心红线

**违反任何一条均视为交付不合格，必须无条件遵守：**

### 1.1 真实性红线
- **绝对禁止编造测试结果、模拟测试输出、隐瞒报错信息、美化测试结论**
- 所有测试必须真实执行，仅认可 VS Code 终端的原始终端输出
- 不接受任何口头描述的"测试通过"
- 测试失败时必须完整展示错误堆栈，不得自行删减

### 1.2 完整性红线
- **绝对禁止使用占位符、省略核心逻辑、生成需要用户自行补全的代码**
- 所有交付的代码必须可直接一键运行
- 所有依赖必须固定版本并写入 requirements.txt
- 禁止出现 TODO、FIXME、pass 等未完成标记（除非是明确标注的扩展点）

### 1.3 规范性红线
- **绝对禁止脱离本项目的固定技术栈、业务规范编写代码**
- 所有功能必须符合本项目定义的技术架构和开发规范
- 不得自由发挥、引入未授权的技术栈
- 代码风格必须与项目现有代码保持一致

---

## 二、强制开发流程

### 2.1 测试驱动开发（TDD）铁则

**所有功能开发必须按以下顺序执行，不得颠倒：**

#### 第一步：定义接口规范
明确以下内容：
- 函数名/类名/方法名
- 入参类型和含义
- 出参类型和含义
- 业务边界条件
- 异常处理规则
- 错误码定义

#### 第二步：编写完整测试用例
在 `tests/` 目录下创建对应的 `test_xxx.py` 文件，测试用例必须包含：
- **正常业务场景用例**（不少于 3 组）
- **边界条件用例**（如空文本、超长分镜、API 调用失败等）
- **异常处理用例**（如文件不存在、参数类型错误、网络超时等）

#### 第三步：编写功能实现代码
基于接口规范和测试用例，编写功能实现代码

#### 第四步：执行测试验证
- 必须在 VS Code 终端执行测试命令
- 直到所有测试用例 100% 通过，方可交付
- 测试不通过必须修复后重新执行

### 2.2 真实测试执行强制要求

1. **环境一致性**：必须使用本项目的本地环境，在 VS Code 终端执行测试，执行前必须先确认环境与项目配置一致

2. **输出完整性**：测试执行后，必须把**完整、未经任何修改、删减、美化的终端原始输出**（含所有通过/失败条目、报错堆栈、日志信息）完整粘贴给用户，不得自行总结

3. **迭代修复**：若测试不通过，必须基于真实报错逐行修复，重新执行测试并再次粘贴完整终端日志，直到全量通过

4. **禁止造假**：禁止使用文本模拟测试、AI 生成的假执行日志、非本地环境的测试结果

### 2.3 五阶段生成流程

系统核心功能开发必须严格遵循以下五阶段流程：

| 阶段 | 名称 | 输入 | 输出 | 核心操作 |
|------|------|------|------|----------|
| 阶段一 | 文档解析与信息提取 | 需求文档 (.docx) | 结构化需求数据 (JSON) | LLM 提取关键信息 |
| 阶段二 | 模板结构分析 | 模板文档 (.docx) | 章节结构树 (JSON) | LLM 分析模板章节层级 |
| 阶段三 | 分章节内容生成 | 需求数据 + 章节结构 + 用户指令 | 各章节内容 (JSON) | 逐章调用 LLM 生成 |
| 阶段四 | 质量审校 | 全文内容 (JSON) | 审校意见 + 修正后内容 (JSON) | LLM 检查一致性 |
| 阶段五 | Word 文档渲染 | 审校后内容 (JSON) + 样式配置 | 最终.docx 文件 | python-docx 渲染 |

### 2.4 分层分段生成原则

- **任务单一原则**：每次 LLM 调用只完成一个明确的任务
- **上下文充分原则**：每次调用提供完成任务所需的全部信息
- **输出约束原则**：通过 JSON Schema 严格控制输出格式
- **质量锚定原则**：通过 Few-shot 示例锚定输出质量

---

## 三、交付要求

### 3.1 代码交付要求

1. **可运行性**：代码必须可直接运行，无需用户补充任何内容
2. **依赖固定**：所有 Python 依赖必须固定版本号
3. **测试覆盖**：核心功能必须有对应的测试用例
4. **文档完整**：README.md 必须包含完整的安装、配置、使用说明

### 3.2 测试交付要求

1. **测试通过率**：所有测试用例必须 100% 通过
2. **测试报告**：必须提供完整的测试执行日志
3. **边界覆盖**：必须覆盖正常、边界、异常三类场景

### 3.3 文档交付要求

1. **API 文档**：所有接口必须有完整的文档说明
2. **数据字典**：数据库表结构必须有详细说明
3. **部署文档**：必须有完整的部署步骤说明

---

## 四、技术架构规范

### 4.1 系统分层架构

```
┌─────────────────────────────────────────────────────────┐
│                    前端展示层                             │
│  (Vue3 + Element Plus / Flask Templates)                │
│  用户交互、文件上传、进度展示、结果预览                    │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                    后端服务层                             │
│  (Python FastAPI / Flask)                               │
│  API 接口、任务调度、业务逻辑、数据持久化                  │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                    AI 引擎层                              │
│  (LLM Adapter + Prompt Template)                        │
│  文档解析、Prompt 编排、LLM 调用、结果校验                 │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                    文档渲染层                             │
│  (python-docx + 模板引擎)                                │
│  Word 文档生成、格式控制、模板管理                         │
└─────────────────────────────────────────────────────────┘
```

### 4.2 技术栈规范

#### 后端技术栈
| 类别 | 技术选型 | 说明 |
|------|----------|------|
| Web 框架 | Python FastAPI / Flask | 异步支持好，适合 AI 推理场景 |
| 数据库 | PostgreSQL / SQLite | 支持 JSON 字段 |
| 任务队列 | Celery + Redis | 异步任务处理 |
| 文件存储 | 本地文件系统 / MinIO | 存储上传文档和生成结果 |
| 文档解析 | python-docx | 读取和提取 Word 文档 |
| 文档生成 | python-docx | 生成格式化 Word 文档 |

#### AI 引擎技术栈
| 类别 | 技术选型 | 说明 |
|------|----------|------|
| LLM 接口层 | OpenAI SDK / 各厂商 SDK | 统一封装多种 LLM API |
| 默认模型 | GPT-4o / 通义千问-Max | 长上下文、结构化输出能力强 |
| Prompt 管理 | Jinja2 模板引擎 | Prompt 模板化管理 |
| 输出约束 | JSON Schema | 强制 LLM 按预定义结构输出 |

#### 前端技术栈
| 类别 | 技术选型 | 说明 |
|------|----------|------|
| 框架 | Vue3 + TypeScript | 响应式框架，组件化开发 |
| UI 组件库 | Element Plus | 成熟的企业级 UI 组件 |
| 文件上传 | el-upload | 支持拖拽上传、格式校验 |
| 进度展示 | SSE (Server-Sent Events) | 实时推送生成进度 |
| 文档预览 | docx-preview | 浏览器端 Word 文档预览 |

### 4.3 核心设计理念

#### 内容与格式解耦
- LLM 只负责文本内容生成，输出结构化 JSON 数据
- python-docx 只负责格式渲染，根据 JSON 数据生成 Word 文档
- 两者通过统一的 JSON 中间格式桥接，互不干扰

#### 模板驱动、配置化
- 文档格式通过预制 Word 样式模板和配置化的样式参数控制
- 支持不同的排版规范需求
- 新模板的接入只需配置样式映射，无需修改代码逻辑

#### 数据点传递机制
- 全局维护一份已确立的关键数据字典
- 每生成一个章节后自动提取新数据点并更新字典
- 后续章节的 Prompt 中强制注入已有数据点，确保数据一致性

---

## 五、项目目录结构

```
xmjl/
├── backend/                          # 后端服务
│   ├── app/
│   │   ├── main.py                  # FastAPI/Flask入口
│   │   ├── config.py                # 配置管理
│   │   ├── models/                  # 数据库模型
│   │   │   ├── task.py
│   │   │   ├── template.py
│   │   │   └── document.py
│   │   ├── api/                     # API 路由
│   │   │   ├── tasks.py
│   │   │   ├── documents.py
│   │   │   └── templates.py
│   │   ├── services/                # 业务服务层
│   │   │   ├── document_parser.py   # 文档解析
│   │   │   ├── ai_engine.py         # AI 引擎主控
│   │   │   ├── llm_adapter.py       # LLM 适配器
│   │   │   ├── prompt_manager.py    # Prompt 管理
│   │   │   ├── chapter_generator.py # 章节生成器
│   │   │   ├── data_point_manager.py# 数据点管理
│   │   │   ├── quality_reviewer.py  # 质量审校
│   │   │   └── doc_renderer.py      # 文档渲染引擎
│   │   ├── prompts/                 # Prompt 模板目录
│   │   │   ├── extract_requirements.j2
│   │   │   ├── analyze_template.j2
│   │   │   ├── generate_chapter.j2
│   │   │   └── review_quality.j2
│   │   └── utils/
│   │       ├── doc_builder.py       # DocBuilder 工具类
│   │       └── style_config.py      # 样式配置加载
│   ├── templates/                   # Word 样式模板目录
│   │   └── default_template.docx
│   ├── styles/                      # 样式配置文件目录
│   │   └── default_styles.json
│   ├── examples/                    # Few-shot 示例目录
│   ├── tests/                       # 测试目录
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                         # 前端项目 (可选)
│   ├── src/
│   │   ├── views/
│   │   ├── components/
│   │   ├── api/
│   │   └── stores/
│   ├── package.json
│   └── Dockerfile
├── docs/                             # 文档目录
│   ├── PROJECT_SPEC.md              # 项目开发规范 (本文件)
│   ├── SKILLS.md                    # Skills 配置
│   └── API.md                       # API 文档
├── uploads/                          # 上传文件存储
├── outputs/                          # 生成文件存储
├── README.md                         # 项目说明
└── requirements.txt                  # Python 依赖
```

---

## 六、API 接口规范

### 6.1 接口总览

| 接口 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 上传文档 | POST | /api/v1/documents/upload | 上传需求文档或模板文档 |
| 创建生成任务 | POST | /api/v1/tasks | 创建文档生成任务 |
| 查询任务状态 | GET | /api/v1/tasks/{task_id} | 获取任务详情和进度 |
| 任务进度推送 | GET | /api/v1/tasks/{task_id}/progress | SSE 实时进度推送 |
| 下载生成文档 | GET | /api/v1/tasks/{task_id}/download | 下载生成的 Word 文件 |
| 取消任务 | POST | /api/v1/tasks/{task_id}/cancel | 取消正在执行的任务 |
| 重试任务 | POST | /api/v1/tasks/{task_id}/retry | 重试失败的任务 |

### 6.2 核心接口定义

#### 创建生成任务

**请求：** `POST /api/v1/tasks`

```json
{
  "requirement_doc_id": "uuid-of-uploaded-requirement-doc",
  "template_id": "uuid-of-template",
  "user_instruction": "项目名称为 XX，投资规模约 XX 万，重点关注 XX 场景",
  "llm_model": "qwen-max",
  "options": {
    "enable_review": true,
    "target_word_count": 30000,
    "language": "zh-CN"
  }
}
```

**响应：**
```json
{
  "task_id": "generated-uuid",
  "status": "pending",
  "message": "任务已创建，即将开始处理",
  "estimated_time_minutes": 15
}
```

---

## 七、数据模型规范

### 7.1 核心数据实体

| 实体 | 说明 | 主要字段 |
|------|------|----------|
| GenerationTask | 生成任务 | id, status, progress, input_files, output_file |
| DocumentTemplate | 格式模板 | id, name, template_file, style_config |
| UploadedDocument | 上传的文档 | id, file_path, file_type, extracted_text |
| ChapterContent | 章节内容 | id, task_id, chapter_number, json_content |
| DataPointDict | 数据点字典 | id, task_id, data_points_json |

### 7.2 生成任务状态

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

---

## 八、Prompt 设计规范

### 8.1 Prompt 模板体系

```
prompts/
├── extract_requirements.j2      # 阶段一：需求信息提取
├── analyze_template.j2          # 阶段二：模板结构分析
├── generate_chapter.j2          # 阶段三：章节内容生成
├── generate_chapter_table.j2    # 阶段三：含表格的章节生成
├── extract_data_points.j2       # 阶段三：数据点提取
├── review_consistency.j2        # 阶段四：数据一致性审校
├── review_coverage.j2           # 阶段四：需求覆盖度审校
└── review_quality.j2            # 阶段四：整体质量审校
```

### 8.2 核心 Prompt 示例

```jinja2
你是一位资深的项目方案编写专家，拥有丰富的政府信息化项目方案编写经验。

【任务】请为以下章节撰写内容。

【项目背景信息】
{{ project_context | tojson }}

【当前章节要求】
- 章节编号：{{ chapter.number }}
- 章节标题：{{ chapter.title }}
- 内容类型：{{ chapter.content_type }}
- 目标字数：{{ chapter.estimated_words }}字

【已确立的关键数据点】（引用时必须保持一致）
{{ data_points | tojson }}

【前文摘要】
{{ prev_summary }}

【用户补充要求】
{{ user_instruction }}

【输出格式要求】
严格按以下 JSON 格式输出，不要输出任何其他内容：
{{ output_schema | tojson }}
```

---

## 九、质量审校规范

### 9.1 审校维度

| 检查维度 | 检查内容 | 处理方式 |
|----------|----------|----------|
| 数据一致性 | 金额、数量、百分比前后是否一致 | 自动修正为数据点字典中的值 |
| 需求覆盖度 | 需求文档中的每个要点是否有回应 | 标记未覆盖项，补充生成 |
| 逻辑完整性 | 论述是否存在逻辑跳跃、自相矛盾 | 标记问题点，重新生成 |
| 专业规范性 | 术语使用是否准确 | 标记并建议修正 |
| 字数达标 | 各章节字数是否达到要求 | 不达标的章节扩写补充 |

### 9.2 审校流程

1. 数据一致性检查 → 自动修正
2. 需求覆盖度检查 → 标记补充
3. 逻辑完整性检查 → 标记修正
4. 专业规范性检查 → 建议优化
5. 字数达标检查 → 扩写补充

---

## 十、版本管理

### 10.1 Git 提交规范

```
feat: 新功能
fix: 修复 bug
docs: 文档更新
style: 代码格式调整
refactor: 重构代码
test: 测试相关
chore: 构建/工具/配置相关
```

### 10.2 版本命名

```
主版本。次版本。修订版
  ↑      ↑      ↑
 重大变更  新功能  Bug 修复
```

---

## 十一、附则

1. 本规范自发布之日起强制执行
2. 所有新功能开发必须遵循 TDD 流程
3. 所有代码提交必须通过 CI/CD 检查
4. 违反核心红线的代码不予验收

---

**编制单位：** 系统开发团队  
**生效日期：** 2026 年 3 月
