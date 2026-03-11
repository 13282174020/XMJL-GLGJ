"""
浏览器自动化测试工具
基于 Playwright 提供浏览器自动化能力
"""

from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext
from typing import Optional, Literal
import os


class BrowserTool:
    """浏览器自动化工具类"""
    
    def __init__(self, headless: bool = True):
        """
        初始化工具
        
        Args:
            headless: 是否无头模式运行，默认 True
        """
        self.headless = headless
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
    
    def start(self, browser_type: Literal["chromium", "firefox", "webkit"] = "chromium"):
        """
        启动浏览器
        
        Args:
            browser_type: 浏览器类型，chromium/firefox/webkit
        """
        self.playwright = sync_playwright().start()
        self.browser = self.playwright[browser_type].launch(headless=self.headless)
        self.context = self.browser.new_context(
            viewport={"width": 1280, "height": 720}
        )
        self.page = self.context.new_page()
        return self
    
    def goto(self, url: str, wait_until: str = "networkidle"):
        """
        导航到指定页面
        
        Args:
            url: 目标 URL
            wait_until: 等待策略，domcontentloaded/networkidle/load
        """
        if not self.page:
            raise RuntimeError("浏览器未启动，请先调用 start()")
        self.page.goto(url, wait_until=wait_until)
        return self
    
    def click(self, selector: str):
        """点击元素"""
        self.page.click(selector)
        return self
    
    def fill(self, selector: str, value: str):
        """填写表单"""
        self.page.fill(selector, value)
        return self
    
    def type_text(self, selector: str, text: str):
        """模拟键盘输入"""
        self.page.type(selector, text)
        return self
    
    def get_text(self, selector: str) -> str:
        """获取元素文本"""
        return self.page.text_content(selector)
    
    def get_inner_html(self, selector: str) -> str:
        """获取元素内部 HTML"""
        return self.page.inner_html(selector)
    
    def screenshot(self, path: str, full_page: bool = False):
        """
        截图
        
        Args:
            path: 保存路径
            full_page: 是否截取完整页面
        """
        self.page.screenshot(path=path, full_page=full_page)
        return self
    
    def wait_for_selector(self, selector: str, timeout: int = 30000):
        """等待元素出现"""
        self.page.wait_for_selector(selector, timeout=timeout)
        return self
    
    def evaluate(self, script: str):
        """执行 JavaScript 代码"""
        return self.page.evaluate(script)
    
    def close(self):
        """关闭浏览器"""
        if self.page:
            self.page.close()
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# 便捷函数
def open_browser(url: str = None, headless: bool = True):
    """快速打开浏览器"""
    tool = BrowserTool(headless=headless)
    tool.start()
    if url:
        tool.goto(url)
    return tool


def run_test(test_func):
    """
    装饰器：自动管理浏览器生命周期的测试装饰器
    
    Usage:
        @run_test
        def my_test(page):
            page.goto("https://example.com")
            ...
    """
    def wrapper(*args, **kwargs):
        with BrowserTool() as browser:
            browser.start()
            return test_func(browser.page, *args, **kwargs)
    return wrapper
