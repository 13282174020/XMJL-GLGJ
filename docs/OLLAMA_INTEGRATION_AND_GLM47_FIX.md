# Ollama 本地模型集成与 GLM-4.7 修复总结

## 时间
2026-03-10

---

## 一、Ollama 本地模型集成

### 1. 添加 Ollama 厂商配置

**文件**: `web_system/model_config_v2.py`

在 `PRESET_PROVIDERS` 中添加 Ollama 厂商配置：

```python
"ollama": {
    "name": "Ollama (本地)",
    "icon": "🦙",
    "base_url": "http://localhost:11434/v1/chat/completions",
    "models": [
        {
            "id": "ollama-glm-4-7-flash-q4",
            "name": "GLM-4.7-Flash-Q4 (Ollama)",
            "type": "text",
            "model": "modelscope.cn/unsloth/GLM-4.7-Flash-GGUF:Q4_K_M",
            "max_tokens": 2000,
            "temperature": 0.7,
            "description": "Ollama 本地部署的 GLM-4.7-Flash Q4_K_M 量化模型"
        },
        # ... 其他模型
    ]
}
```

### 2. 修改 API Key 验证逻辑

**问题**: Ollama 本地模型不需要 API Key，但代码强制验证导致无法使用。

**修改文件**:
- `web_system/app.py` (3 处)
- `web_system/ai_engine.py` (1 处)

**修改内容**:
```python
# 原代码
if not model_config.api_key:
    return jsonify({'success': False, 'message': 'API Key 未配置'})

# 修改后
if model_config.provider_id != 'ollama' and not model_config.api_key:
    return jsonify({'success': False, 'message': 'API Key 未配置'})
```

### 3. 修复 Ollama API 调用格式

**问题**: Ollama 使用原生 API 格式 `/api/chat`，而非 OpenAI 兼容格式 `/v1/chat/completions`。

**修改文件**: `web_system/ai_engine.py`

**修改内容**:
```python
# Ollama 原生 API 格式
if model_config.provider_id == 'ollama':
    # 自动切换到原生 API 端点
    if '/api/chat' not in base_url:
        base_url = "http://localhost:11434/api/chat"
    
    payload = {
        'model': model_config.model,
        'messages': [{'role': 'user', 'content': prompt}],
        'stream': False
    }
```

**响应提取**:
```python
def _extract_ai_response(result: Dict, model_config: ModelConfig) -> str:
    # Ollama 原生格式：message.content
    if model_config.provider_id == 'ollama':
        if 'message' in result and isinstance(result['message'], dict):
            content = result['message'].get('content', '')
            if content:
                return content
    # ... 其他格式
```

### 4. 撤销参数优化

**说明**: 尝试添加 `top_p`、`top_k`、`repeat_penalty` 等参数优化，但效果更差，已恢复原始配置。

**恢复的配置**:
- `max_tokens`: 2000
- `temperature`: 0.7

---

## 二、任务取消功能修复

### 问题
点击取消任务后，任务仍继续执行，AI 调用未停止。

### 修改文件
`web_system/app.py`

### 修复内容

在以下位置添加任务取消检查：

1. **`render_chapter_with_status()` 函数**
   - 每次递归前检查
   - 生成内容前检查

2. **`generate_chapter_content()` 函数**
   - AI 调用前检查
   - AI 返回后检查

3. **`generate_chapters_with_template()` 函数**
   - AI 调用前检查
   - AI 返回后检查

4. **`regenerate_chapter()` 函数**
   - AI 调用前检查
   - AI 返回后检查

**修改模式**:
```python
# AI 调用前检查
task_info = task_manager.load_task_info(task_id)
if task_info and task_info.status == 'cancelled':
    print(f'[CANCEL] 任务已取消，停止生成')
    return

# AI 调用
content = generate_section_content_with_ai(...)

# AI 返回后检查
task_info = task_manager.load_task_info(task_id)
if task_info and task_info.status == 'cancelled':
    print(f'[CANCEL] 任务已取消，停止生成')
    return
```

---

## 三、GLM-4.7-Flash 思考模式问题

### 问题
GLM-4.7-Flash 默认启用思考模式（thinking），导致：
- `reasoning_content` 占用大量 token
- `content` 字段为空或内容极少
- 测试失败：`[API 返回格式异常] 无法提取内容`

### 日志示例
```json
{
  "choices": [{
    "message": {
      "content": "",  // 空！
      "reasoning_content": "1. **分析请求：**..."  // 思考过程
    }
  }],
  "usage": {
    "completion_tokens": 300,
    "completion_tokens_details": {"reasoning_tokens": 297}  // 297/300 用于思考
  }
}
```

### 修改文件
`web_system/ai_engine.py`

### 修复内容

```python
# 智谱 AI GLM-4.7 需要 thinking 参数
# 注意：GLM-4.7-Flash 等快速模型默认启用 thinking，需要显式禁用
if model_config.provider_id == "zhipu" and "glm-4" in model_config.model.lower():
    # GLM-4.7-Flash 默认启用 thinking，需要显式禁用
    if "flash" in model_config.model.lower():
        payload['thinking'] = {"type": "disabled"}
    # 只有非 Flash 版本且 max_tokens 足够大时才启用 thinking
    elif model_config.max_tokens > 200:
        payload['thinking'] = {"type": "enabled"}
```

### 测试参数调整

**文件**: `web_system/app.py`

```python
# 创建临时模型配置用于测试
# GLM-4.7-Flash 等模型会输出 reasoning_content，需要更多 token
test_max_tokens = 300 if "glm-4.7" in model.model.lower() else 100
temp_config = ModelConfig(
    # ...
    max_tokens=test_max_tokens,
    # ...
)
```

---

## 四、修复的导入问题

### 问题
`ImportError: cannot import name 'get_chapter_content_template' from 'ai_engine'`

### 修改文件
- `web_system/ai_engine.py`
- `web_system/app.py`

### 修复内容

1. **将函数移动到 `ai_engine.py`**（第 1066 行）
2. **删除 `app.py` 中的函数定义**
3. **在 `app.py` 顶部添加导入**:
   ```python
   from ai_engine import get_chapter_content_template
   ```

---

## 五、文件清单

| 文件 | 修改内容 |
|------|----------|
| `model_config_v2.py` | 添加 Ollama 厂商配置 |
| `ai_engine.py` | 1. Ollama 原生 API 支持<br>2. API Key 验证修改<br>3. GLM-4.7 thinking 控制<br>4. 响应提取增强<br>5. 添加 `get_chapter_content_template` 函数 |
| `app.py` | 1. API Key 验证修改（3 处）<br>2. 任务取消检查（多处）<br>3. 导入修复<br>4. 测试参数调整 |

---

## 六、使用说明

### Ollama 本地模型配置

1. 确保 Ollama 服务运行：`ollama serve`
2. 确认模型已拉取：`ollama list`
3. 在模型配置管理 v2 页面启用 Ollama 模型
4. Ollama 本地模型不需要配置 API Key

### GLM-4.7-Flash 测试

1. 确保模型已启用并配置 API Key
2. 测试时会自动禁用 thinking 模式
3. 测试使用 `max_tokens=300` 确保有足够输出空间

### 任务取消

1. 点击取消按钮后，任务会立即停止
2. 已生成的内容会保留
3. 未生成的章节不再继续

---

## 七、注意事项

1. **Ollama 模型质量**: GLM-4.7-Flash-Q4_K_M 是 4bit 量化版本，可能出现内容重复、逻辑混乱等问题，建议：
   - 使用在线 API（阿里云百炼）获得更好质量
   - 或尝试其他本地模型（Qwen2.5-7B-Instruct 等）

2. **GLM-4.7-Flash thinking**: 已自动禁用，如需启用请修改代码

3. **任务取消**: 在 AI 调用间隙检查，如果 AI 调用时间较长，可能需要等待当前调用完成

---

## 八、测试验证

### Ollama 测试
```bash
cd web_system
python test_ollama.py
```

### GLM-4.7 测试
访问：`http://localhost:5000/api/v2/models/GLM-4.7/test`

预期结果：
```json
{
  "success": true,
  "message": "测试成功",
  "response": "我是一个由 Z.ai 训练的大语言模型..."
}
```
