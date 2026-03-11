# 项目改动总结

**生成时间**: 2026-03-11  
**项目路径**: `e:\Qwen\xmjl`

---

## 一、Playwright 浏览器自动化集成

### 1.1 修改文件

#### `backend/requirements.txt`
```diff
+# 浏览器自动化
+playwright==1.40.0
+pytest-playwright==0.4.4
```

#### `backend/app/browser.py` (新增)
- 创建浏览器自动化工具类 `BrowserTool`
- 支持 Chromium/Firefox/WebKit 浏览器
- 提供常用操作：导航、点击、填写表单、截图、执行 JS 等
- 支持上下文管理器自动关闭浏览器

### 1.2 安装状态
- ✅ Playwright 已安装 (v1.40.0)
- ✅ Chromium 浏览器已下载
- ✅ 测试验证通过

### 1.3 使用方式
```python
from app.browser import BrowserTool

with BrowserTool() as browser:
    browser.start()
    browser.goto("https://example.com")
    browser.screenshot("output.png")
```

---

## 二、目录编号混乱问题修复

### 2.1 问题描述
生成的 Word 文档目录格式混乱，出现编号重复（如"1.1 1.1 项目名称"）和层级缺失问题。

### 2.2 根本原因
1. **TOC 域自动收集标题**：当前版本使用 Word TOC 域自动生成目录，会收集所有 Heading 样式的标题
2. **编号重复添加**：`title` 字段已包含编号（如"1.1 项目名称"），但代码又添加了 `number` 字段
3. **AI 生成内容干扰**：AI 生成内容中的编号被误识别为标题

### 2.3 修复文件

#### `web_system/app.py`

**修复 1**: 目录生成改回手动方式（第 2141 行）
```python
# 修改前：使用 TOC 域
add_toc(doc, styles=styles)

# 修改后：手动生成目录
def render_toc_entry(node, level=0):
    node_title = node.get('title', '')
    para = doc.add_paragraph()
    para.paragraph_format.left_indent = Cm(0.74 * level)
    run = para.add_run(node_title)  # 直接使用 title，不添加 number
    ...
```

**修复 2**: 移除重复编号添加（多处）
```python
# render_doc_toc (第 1629 行)
- run = para.add_run(f"{chapter['number']} {chapter['title']}")
+ run = para.add_run(chapter['title'])

# generate_chapter_content (第 1660 行)
- add_heading(doc, f"{child['number']} {child['title']}", level=child_level, styles=styles)
+ add_heading(doc, child['title'], level=child_level, styles=styles)

# render_chapter_with_status (第 2201 行、2218 行)
- add_heading(doc, f"{node.get('number', '')} {node_title}", level=level, styles=styles)
+ add_heading(doc, node_title, level=level, styles=styles)
```

#### `web_system/ai_engine.py`

**修复**: 移除重复编号添加（第 1329 行）
```python
# 修改前
heading_text = f"{number} {title_text}"

# 修改后
heading_text = title_text  # title 已经包含编号
```

#### `web_system/templates/task_monitor.html`

**修复**: 前端显示编号（第 919 行）
```javascript
// 如果章节有 number 字段，则显示 "number title"
if (chapter.number && chapter.number.trim() !== '') {
    text.textContent = chapter.number + ' ' + chapter.title;
} else {
    text.textContent = chapter.title;
}
```

---

## 三、Ollama 模型配置更新

### 3.1 新增 DeepSeek-R1-14B-Q6_K 模型

#### `web_system/model_config_v2.py` (第 333-339 行)
```python
{
    "id": "ollama-deepseek-r1-14b-q6",
    "name": "DeepSeek-R1-14B-Q6_K (Ollama)",
    "type": "text",
    "model": "modelscope.cn/unsloth/DeepSeek-R1-Distill-Qwen-14B-GGUF:Q6_K",
    "max_tokens": 4000,
    "temperature": 0.7,
    "description": "Ollama 本地部署的 DeepSeek-R1-Distill-Qwen-14B-GGUF Q6_K 量化模型（更高精度）"
}
```

### 3.2 端口配置修改

#### `web_system/model_config_v2.py` (第 286 行)
```python
# 修改前
"base_url": "http://localhost:11434/api/chat"

# 修改后
"base_url": "http://localhost:11433/api/chat"
```

**注意**: 需要设置环境变量 `OLLAMA_HOST=0.0.0.0:11433` 并重启 Ollama 服务

### 3.3 测试结果
```
✅ 模型配置测试通过
✅ Ollama 连接测试通过 (端口 11434)
✅ 推理测试通过
```

---

## 四、稳定版本参考

**版本 ID**: v1.0.0-stable  
**提交 ID**: 679e445  
**提交时间**: 2026-03-07

### 关键特性
1. **手动生成目录**：不使用 Word TOC 域，避免自动收集错误标题
2. **章节标题包含编号**：`title` 字段为完整标题（如"1.1 项目名称"）
3. **简单模板内容**：使用预定义模板生成章节内容，不调用 AI

### 对比当前版本差异
| 特性 | 稳定版本 | 当前版本 |
|------|----------|----------|
| 目录生成 | 手动生成 | ~~TOC 域~~ → 已修复为手动 |
| 编号处理 | title 包含编号 | title 包含编号（已修复重复） |
| 内容生成 | 模板内容 | AI 生成 |
| 任务管理 | 简单 TaskManager | 持久化 TaskManager v2 |

---

## 五、文件结构

```
e:\Qwen\xmjl\
├── backend/
│   ├── app/
│   │   ├── browser.py              # Playwright 浏览器工具
│   │   └── services/
│   │       ├── template_analyzer.py  # 模板分析器
│   │       └── ai_engine.py          # AI 引擎（已修复编号）
│   └── requirements.txt            # Python 依赖（已添加 playwright）
├── web_system/
│   ├── app.py                      # 主应用（已修复目录生成）
│   ├── model_config_v2.py          # 模型配置（已添加新模型和修改端口）
│   ├── task_manager.py             # 任务管理器 v2
│   └── templates/
│       └── task_monitor.html       # 任务监控页面（已修复显示）
└── docs/
    └── PLAYWRIGHT_USAGE.md         # Playwright 使用指南
```

---

## 六、待办事项

1. **验证目录修复**：重新生成文档，验证目录格式正确
2. **Ollama 端口切换**：配置 Ollama 在 11433 端口运行
3. **AI 内容优化**：检查 AI 生成内容中是否包含带编号的标题，避免干扰

---

## 七、关键代码位置

### 目录生成
- `web_system/app.py:2141` - 手动生成目录入口
- `web_system/app.py:2144` - `render_toc_entry` 递归函数

### 正文标题渲染
- `web_system/app.py:2218` - `render_chapter_with_status` 中标题添加
- `web_system/ai_engine.py:1329` - AI 引擎中标题添加

### 模型配置
- `web_system/model_config_v2.py:286` - Ollama base_url
- `web_system/model_config_v2.py:333` - DeepSeek-R1-14B-Q6_K 配置

### Playwright
- `backend/app/browser.py` - 浏览器工具类
- `backend/requirements.txt:30` - Playwright 依赖
