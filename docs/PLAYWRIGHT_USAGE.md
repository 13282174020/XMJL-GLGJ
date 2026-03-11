# Playwright 浏览器自动化使用指南

## 概述

项目已集成 Playwright 浏览器自动化工具，位于 `backend/app/browser.py`。
我可以在后续开发中自主调用浏览器进行测试、截图、数据抓取等操作。

## 安装状态

✅ Playwright 已安装  
✅ Chromium 浏览器已下载  
✅ 测试验证通过

## 使用方法

### 1. 基础用法

```python
from app.browser import BrowserTool

# 使用上下文管理器（自动关闭浏览器）
with BrowserTool() as browser:
    browser.start()
    browser.goto("https://example.com")
    browser.screenshot("output.png")
```

### 2. 常用操作

```python
from app.browser import BrowserTool

with BrowserTool(headless=False) as browser:  # headless=False 显示浏览器界面
    browser.start()
    
    # 导航
    browser.goto("https://example.com")
    
    # 填写表单
    browser.fill("#username", "admin")
    browser.fill("#password", "123456")
    
    # 点击按钮
    browser.click("#login-btn")
    
    # 等待元素
    browser.wait_for_selector(".dashboard")
    
    # 获取文本
    title = browser.get_text("h1")
    
    # 截图
    browser.screenshot("dashboard.png", full_page=True)
    
    # 执行 JavaScript
    data = browser.evaluate("() => document.title")
```

### 3. 使用装饰器

```python
from app.browser import run_test

@run_test
def my_test(page):
    page.goto("https://example.com")
    assert page.title() == "Expected Title"
    page.screenshot("result.png")
```

## API 参考

| 方法 | 说明 |
|------|------|
| `start(browser_type)` | 启动浏览器，支持 chromium/firefox/webkit |
| `goto(url)` | 导航到指定 URL |
| `click(selector)` | 点击元素 |
| `fill(selector, value)` | 填写表单字段 |
| `type_text(selector, text)` | 模拟键盘输入 |
| `get_text(selector)` | 获取元素文本 |
| `get_inner_html(selector)` | 获取元素内部 HTML |
| `screenshot(path, full_page)` | 截图 |
| `wait_for_selector(selector, timeout)` | 等待元素出现 |
| `evaluate(script)` | 执行 JavaScript |
| `close()` | 关闭浏览器 |

## 常用选择器

```python
# CSS 选择器
browser.click("#id")           # 按 ID
browser.click(".class")        # 按类名
browser.click("button")        # 按标签名
browser.click("[name='q']")    # 按属性

# XPath (需要前缀)
browser.click("xpath=//button[text()='Submit']")

# 文本选择器
browser.click("text=登录")
browser.click("text='Submit'")
```

## 截图保存位置

截图默认保存到 `outputs/` 目录：
- `e:\Qwen\xmjl\outputs\`

## 调试技巧

1. **显示浏览器界面**：设置 `headless=False`
2. **慢速执行**：在 `start()` 后添加 `browser.context.set_default_timeout(60000)`
3. **查看网络请求**：使用 `browser.page.on('request', lambda r: print(r.url))`

## 示例测试文件

- `backend/tests/test_browser.py` - 完整示例
- `backend/app/test_browser_simple.py` - 简单测试

## 注意事项

1. 使用 `with` 语句确保浏览器正确关闭
2. 无头模式 (`headless=True`) 适合服务器环境
3. 截图路径需要确保目录存在
4. 选择器找不到元素时会抛出异常，可用 `wait_for_selector` 先等待
