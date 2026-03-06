# AI 生成 Word 文档 - 内容优化方案

> 版本：V1.0  
> 创建时间：2026 年 3 月 7 日  
> 状态：待实施

---

## 一、项目背景

### 1.1 当前问题

AI 生成的 Word 文档存在以下问题：

| 问题 | 表现 | 影响 |
|------|------|------|
| **内容空洞** | 套话多，实质性内容少 | 文档可用性低 |
| **缺乏针对性** | 没有围绕需求文档中的具体场景 | 无法满足用户需求 |
| **数据不一致** | 前后金额、数字对不上 | 文档可信度低 |
| **需求覆盖不足** | 需求文档中的关键点没有回应 | 文档不完整 |

### 1.2 核心需求

**通用化设计要求：**
- ❌ 不能写死任何特定领域（如"未来社区"）
- ❌ 不能预设任何固定字段
- ✅ 所有信息从用户上传的文档中动态提取
- ✅ 算法和逻辑领域无关，适用于各类项目

---

## 二、优化目标

### 2.1 数据一致性管理

**目标：** 确保全文中关键数据保持一致

**示例：**
- 项目名称：全文统一为"智慧社区管理平台建设项目"
- 总投资：全文统一为"500 万元"
- 建设工期：全文统一为"12 个月"

### 2.2 需求覆盖度检查

**目标：** 确保需求文档中的所有关键点都有回应

**示例：**
- 需求文档提到"监控老化问题" → 建设必要性章节回应
- 需求文档提到"电瓶车防盗" → 建设内容章节回应
- 需求文档提到"流动人口管理" → 建设内容章节回应

---

## 三、总体架构

```
┌─────────────────────────────────────────────────────────┐
│                    用户上传文档                          │
│  - 需求文档.docx                                        │
│  - 模板文档.docx                                        │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│              第一步：文档解析与信息提取                  │
│                                                          │
│  extract_requirements(requirement_text)                 │
│  ├─ 提取数据点（正则 + AI）                              │
│  ├─ 提取需求点（AI）                                     │
│  └─ 提取目标（AI）                                       │
│                                                          │
│  输出：                                                  │
│  {                                                       │
│    "data_points": {...},                                │
│    "pain_points": [...],                                │
│    "requirements": [...],                               │
│    "goals": [...]                                       │
│  }                                                       │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│              第二步：目录结构分析                        │
│                                                          │
│  analyze_template(template_text)                        │
│  ├─ 提取章节树                                           │
│  ├─ 识别章节类型                                         │
│  └─ 建立章节 - 需求映射                                  │
│                                                          │
│  输出：                                                  │
│  {                                                       │
│    "chapters": [...],                                   │
│    "chapter_requirement_map": {...}                     │
│  }                                                       │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│              第三步：逐章生成（带数据注入）              │
│                                                          │
│  for chapter in chapters:                               │
│    ├─ 注入 data_points                                  │
│    ├─ 注入本章应回应的需求点                            │
│    ├─ 调用 AI 生成内容                                     │
│    ├─ 提取新数据点 → 更新字典                           │
│    └─ 检查需求覆盖度                                    │
│                                                          │
│  输出：                                                  │
│  {                                                       │
│    "generated_chapters": [...],                         │
│    "final_data_points": {...},                          │
│    "uncovered_requirements": [...]                      │
│  }                                                       │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│              第四步：全文审校                            │
│                                                          │
│  review_full_text(generated_content, requirements)      │
│  ├─ 数据一致性检查                                       │
│  ├─ 需求覆盖度检查                                       │
│  └─ 输出审校报告                                         │
│                                                          │
│  输出：                                                  │
│  {                                                       │
│    "consistency_issues": [...],                         │
│    "uncovered_requirements": [...]                      │
│  }                                                       │
└─────────────────────────────────────────────────────────┘
```

---

## 四、详细设计

### 4.1 数据一致性管理

#### 4.1.1 数据点提取（动态识别）

**不预设任何字段**，从文档中自动识别。

**提取方法：**

1. **正则匹配** - 识别数字 + 单位模式
   ```python
   patterns = [
       r'([\d\.]+)\s*万?元',           # 金额
       r'([\d]+)\s*[个年月天]',        # 时间
       r'约 ([\d\.]+)\s*万?人',        # 人口
       r'([^\n]+小区 | 社区 | 项目)',   # 项目名称
   ]
   ```

2. **AI 提取** - 识别关键数据点
   ```
   Prompt:
   "请从以下文本中提取需要全文保持一致的关键数据，
   按以下 JSON 格式输出：
   {
     "data_points": {
       "数据项名称": "数据值"
     }
   }"
   ```

3. **输出示例：**
   ```json
   {
     "data_points": {
       "项目名称": "智慧社区管理平台建设项目",
       "总人口": "约 1.1 万人",
       "总户数": "3000 多户",
       "建设工期": "12 个月",
       "总投资": "500 万元",
       "建设单位": "XX 科技有限公司"
     }
   }
   ```

#### 4.1.2 数据点注入（Prompt 模板）

**通用 Prompt 模板：**

```
【任务】请为【{chapter_title}】撰写内容

【已确立的关键数据】
（以下数据已在文中确立，引用时必须保持一致）
{data_points_json}

【需求文档内容】
{requirement_text}

【输出要求】
1. 内容要专业、准确、逻辑清晰
2. 使用正式的公文语言
3. 不要输出章节标题
4. 字数控制在 200-400 字

【请开始撰写】
```

#### 4.1.3 数据点更新（增量维护）

**每章生成后：**

1. 提取新出现的数据
   ```
   Prompt:
   "以下文本中是否有需要全文保持一致的关键数据？
   如有请提取，按 JSON 格式输出。"
   ```

2. 更新数据点字典
   ```python
   def update_data_points(existing, new):
       for key, value in new.items():
           if key not in existing:
               existing[key] = value
           elif existing[key] != value:
               # 数据冲突，记录日志
               log_conflict(key, existing[key], value)
       return existing
   ```

---

### 4.2 需求覆盖度检查

#### 4.2.1 需求点提取（动态识别）

**不预设任何需求类型**，从文档中自动提取。

**提取 Prompt：**

```
请分析以下需求文档，提取所有明确的需求点和痛点，
按以下 JSON 格式输出：

{
  "pain_points": ["痛点 1", "痛点 2", ...],
  "requirements": ["需求 1", "需求 2", ...],
  "goals": ["目标 1", "目标 2", ...]
}
```

**输出示例：**

```json
{
  "pain_points": [
    "监控设备老化，存在安全隐患",
    "电瓶车盗窃问题频发",
    "流动人口管理困难"
  ],
  "requirements": [
    "建设高清监控系统",
    "建设电瓶车防盗系统",
    "建设流动人口管理平台"
  ],
  "goals": [
    "提升社区安全水平",
    "改善居民生活品质"
  ]
}
```

#### 4.2.2 章节 - 需求映射（通用规则）

**基于章节标题关键词自动映射：**

```python
CHAPTER_REQUIREMENT_MAP = {
    # 章节标题关键词 → 应回应的需求类型
    '必要性': ['pain_points'],
    '需求': ['requirements'],
    '目标': ['goals'],
    '建设内容': ['requirements'],
    '方案': ['requirements'],
}
```

**映射逻辑：**

```python
def map_chapter_requirements(chapter_title, extracted_requirements):
    """
    根据章节标题，返回本章应回应的需求点
    """
    requirements_to_cover = []
    
    for keyword, req_types in CHAPTER_REQUIREMENT_MAP.items():
        if keyword in chapter_title:
            for req_type in req_types:
                requirements_to_cover.extend(
                    extracted_requirements.get(req_type, [])
                )
    
    return requirements_to_cover
```

#### 4.2.3 覆盖度检查（AI 审校）

**生成后检查 Prompt：**

```
请检查以下内容是否回应了以下需求点：

【需求点列表】
1. 监控设备老化，存在安全隐患
2. 电瓶车盗窃问题频发
3. 流动人口管理困难

【待检查内容】
{chapter_content}

请输出：
{
  "covered": ["已回应的需求"],
  "uncovered": ["未回应的需求"],
  "analysis": "简要分析"
}
```

**输出处理：**

- 如果有未回应需求 → 记录到待补充列表
- 在后续章节中补充生成
- 全文完成后输出审校报告

---

### 4.3 全文审校

#### 4.3.1 数据一致性检查

**Prompt：**

```
请检查以下内容中关键数据是否前后一致：

【全文内容】
{full_text}

请输出：
{
  "data_items": [
    {"name": "项目名称", "values": ["值 1", "值 2"], "consistent": true/false},
    {"name": "总投资", "values": ["500 万元", "800 万元"], "consistent": false}
  ],
  "inconsistencies": ["总投资前后不一致：500 万元 vs 800 万元"]
}
```

#### 4.3.2 需求覆盖度检查

**Prompt：**

```
请检查全文是否覆盖了以下需求点：

【需求点列表】
{all_requirements}

【全文内容摘要】
{full_text_summary}

请输出未覆盖的需求点列表及建议补充的章节。
```

---

## 五、实施计划

### 5.1 第一阶段：数据一致性管理

**目标：** 实现数据点动态提取、注入、更新

**任务列表：**

| 任务 | 说明 | 预计工作量 |
|------|------|------------|
| 5.1.1 | 创建 `data_point_manager.py` 模块 | 2 小时 |
| 5.1.2 | 实现 `extract_data_points()` 函数（正则+AI） | 2 小时 |
| 5.1.3 | 实现 `update_data_points()` 函数 | 1 小时 |
| 5.1.4 | 修改 `ai_engine.py` 注入数据点 | 2 小时 |
| 5.1.5 | 编写测试用例 | 2 小时 |
| **合计** | | **9 小时** |

**验收标准：**
- ✅ 能从需求文档提取数据点
- ✅ 每章生成时注入数据点
- ✅ 生成后能提取新数据点
- ✅ 数据冲突能检测并记录

---

### 5.2 第二阶段：需求覆盖度检查

**目标：** 实现需求点动态提取、映射、审校

**任务列表：**

| 任务 | 说明 | 预计工作量 |
|------|------|------------|
| 5.2.1 | 创建 `requirement_analyzer.py` 模块 | 2 小时 |
| 5.2.2 | 实现 `extract_requirements()` 函数 | 2 小时 |
| 5.2.3 | 实现 `map_chapter_requirements()` 函数 | 2 小时 |
| 5.2.4 | 实现 `check_coverage()` 函数 | 2 小时 |
| 5.2.5 | 修改 `ai_engine.py` 注入需求点 | 2 小时 |
| 5.2.6 | 编写测试用例 | 2 小时 |
| **合计** | | **12 小时** |

**验收标准：**
- ✅ 能从需求文档提取需求点
- ✅ 每章生成时注入相关需求点
- ✅ 生成后能检查覆盖度
- ✅ 输出未覆盖需求列表

---

### 5.3 第三阶段：全文审校

**目标：** 实现全文审校和报告输出

**任务列表：**

| 任务 | 说明 | 预计工作量 |
|------|------|------------|
| 5.3.1 | 创建 `quality_reviewer.py` 模块 | 2 小时 |
| 5.3.2 | 实现 `review_consistency()` 函数 | 2 小时 |
| 5.3.3 | 实现 `review_coverage()` 函数 | 2 小时 |
| 5.3.4 | 集成到生成流程 | 2 小时 |
| 5.3.5 | 编写测试用例 | 2 小时 |
| **合计** | | **10 小时** |

**验收标准：**
- ✅ 能检测数据不一致
- ✅ 能检测需求未覆盖
- ✅ 输出审校报告
- ✅ 可选择性补充生成

---

## 六、代码结构

### 6.1 新增模块

```
web_system/
├── ai_engine.py              # 现有，修改
├── services/
│   ├── data_point_manager.py    # 新增：数据点管理
│   ├── requirement_analyzer.py  # 新增：需求分析
│   └── quality_reviewer.py      # 新增：质量审校
└── tests/
    ├── test_data_point_manager.py
    ├── test_requirement_analyzer.py
    └── test_quality_reviewer.py
```

### 6.2 核心接口

#### DataPointManager

```python
class DataPointManager:
    def extract_from_text(self, text: str) -> Dict[str, str]:
        """从文本中提取数据点"""
        
    def update(self, new_points: Dict[str, str]) -> None:
        """更新数据点字典"""
        
    def get_all(self) -> Dict[str, str]:
        """获取所有数据点"""
        
    def get_conflicts(self) -> List[Dict]:
        """获取数据冲突列表"""
```

#### RequirementAnalyzer

```python
class RequirementAnalyzer:
    def extract(self, requirement_text: str) -> Dict:
        """提取需求点"""
        
    def map_to_chapter(self, chapter_title: str, requirements: Dict) -> List[str]:
        """映射章节应回应的需求点"""
        
    def check_coverage(self, content: str, requirements: List[str]) -> Dict:
        """检查内容覆盖度"""
```

#### QualityReviewer

```python
class QualityReviewer:
    def review_consistency(self, full_text: str, data_points: Dict) -> Dict:
        """审校数据一致性"""
        
    def review_coverage(self, full_text: str, requirements: List[str]) -> Dict:
        """审校需求覆盖度"""
        
    def generate_report(self) -> str:
        """生成审校报告"""
```

---

## 七、测试计划

### 7.1 单元测试

| 模块 | 测试用例数 | 覆盖范围 |
|------|------------|----------|
| DataPointManager | 10 | 提取、更新、冲突检测 |
| RequirementAnalyzer | 10 | 提取、映射、覆盖检查 |
| QualityReviewer | 8 | 一致性、覆盖度审校 |

### 7.2 集成测试

| 测试场景 | 输入 | 预期输出 |
|----------|------|----------|
| 数据一致性 | 需求文档 + 模板文档 | 数据点字典正确，全文一致 |
| 需求覆盖度 | 需求文档 + 模板文档 | 需求点全部覆盖 |
| 全文审校 | 生成的全文 | 审校报告准确 |

### 7.3 真实场景测试

使用真实项目文档测试：
- 未来社区项目
- 智慧园区项目
- 信息化改造项目

---

## 八、风险评估

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| AI 提取准确率低 | 数据点/需求点提取不准确 | 增加人工确认环节 |
| 性能问题 | 多次 AI 调用耗时长 | 批量调用、缓存结果 |
| 数据冲突处理复杂 | 难以判断哪个值正确 | 记录冲突，人工决策 |

---

## 九、明日待办

### 9.1 第一阶段实施

- [ ] 创建 `services/` 目录
- [ ] 实现 `data_point_manager.py`
- [ ] 编写单元测试
- [ ] 集成到 `ai_engine.py`
- [ ] 测试验证

### 9.2 第二阶段实施

- [ ] 实现 `requirement_analyzer.py`
- [ ] 编写单元测试
- [ ] 集成到 `ai_engine.py`
- [ ] 测试验证

### 9.3 第三阶段实施

- [ ] 实现 `quality_reviewer.py`
- [ ] 编写单元测试
- [ ] 集成到生成流程
- [ ] 测试验证

---

## 十、附录

### 10.1 相关文件

- `web_system/ai_engine.py` - AI 引擎模块
- `web_system/app.py` - 主应用
- `web_system/field_config.json` - 字段配置（第一阶段后废弃）

### 10.2 参考资料

- 阿里云百炼 API 文档
- Python 正则表达式指南
- JSON Schema 规范

---

**文档结束**
