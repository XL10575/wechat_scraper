#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chrome启动修复工具
专门解决ChromeDriver路径问题
"""

import os
import glob
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from loguru import logger

class ChromeFixTool:
    """Chrome修复工具"""
    
    def __init__(self):
        self.chrome_path = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
        self.driver_path = None
    
    def find_correct_chromedriver_path(self):
        """找到正确的ChromeDriver路径"""
        logger.info("🔍 寻找正确的ChromeDriver路径...")
        
        # 让webdriver-manager下载驱动
        try:
            base_path = ChromeDriverManager().install()
            logger.info(f"webdriver-manager返回路径: {base_path}")
            
            # 获取基础目录
            base_dir = os.path.dirname(base_path)
            logger.info(f"基础目录: {base_dir}")
            
            # 查找实际的chromedriver.exe文件
            possible_paths = [
                os.path.join(base_dir, "chromedriver.exe"),
                os.path.join(base_dir, "chromedriver-win32", "chromedriver.exe"),
                base_path if base_path.endswith(".exe") else None
            ]
            
            for path in possible_paths:
                if path and os.path.exists(path) and path.endswith(".exe"):
                    logger.success(f"✅ 找到ChromeDriver: {path}")
                    self.driver_path = path
                    return True
            
            # 如果上面都没找到，使用通配符搜索
            search_patterns = [
                os.path.join(os.path.dirname(base_dir), "**", "chromedriver.exe"),
                os.path.join(base_dir, "**", "chromedriver.exe")
            ]
            
            for pattern in search_patterns:
                matches = glob.glob(pattern, recursive=True)
                if matches:
                    self.driver_path = matches[0]
                    logger.success(f"✅ 通过搜索找到ChromeDriver: {self.driver_path}")
                    return True
            
            logger.error("❌ 未找到有效的ChromeDriver")
            return False
            
        except Exception as e:
            logger.error(f"❌ 查找ChromeDriver失败: {e}")
            return False
    
    def test_chrome_startup(self, headless=True):
        """测试Chrome启动"""
        logger.info(f"🚀 测试Chrome启动 (headless={headless})...")
        
        try:
            chrome_options = Options()
            
            if headless:
                chrome_options.add_argument("--headless")
            
            # 基本优化选项
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            
            # 设置Chrome路径
            chrome_options.binary_location = self.chrome_path
            
            # 创建服务
            service = Service(self.driver_path)
            
            # 启动Chrome
            driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # 测试访问页面
            driver.get("https://www.baidu.com")
            title = driver.title
            
            driver.quit()
            
            logger.success(f"✅ Chrome启动成功！页面标题: {title}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Chrome启动失败: {e}")
            return False
    
    def create_fixed_chrome_function(self):
        """创建修复后的Chrome启动函数"""
        logger.info("📝 创建修复后的Chrome启动函数...")
        
        code = f'''
def setup_fixed_chrome(headless=True):
    """修复后的Chrome启动函数"""
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    
    chrome_options = Options()
    
    if headless:
        chrome_options.add_argument("--headless")
    
    # 基本优化选项
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # 设置Chrome和ChromeDriver路径
    chrome_options.binary_location = r"{self.chrome_path}"
    service = Service(r"{self.driver_path}")
    
    # 启动Chrome
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver
'''
        
        # 保存到文件
        with open("fixed_chrome_setup.py", "w", encoding="utf-8") as f:
            f.write(code)
        
        logger.success("✅ 修复函数已保存到 fixed_chrome_setup.py")
        logger.info("您可以在其他脚本中使用:")
        logger.info("from fixed_chrome_setup import setup_fixed_chrome")
        logger.info("driver = setup_fixed_chrome(headless=True)")
    
    def run_full_fix(self):
        """运行完整修复流程"""
        logger.info("🔧 开始Chrome启动修复...")
        
        # 查找正确的ChromeDriver路径
        if not self.find_correct_chromedriver_path():
            logger.error("❌ 无法找到ChromeDriver，修复失败")
            return False
        
        # 测试启动
        if not self.test_chrome_startup(headless=True):
            logger.error("❌ Chrome启动测试失败")
            return False
        
        # 创建修复函数
        self.create_fixed_chrome_function()
        
        logger.success("🎉 Chrome启动修复完成！")
        return True

def main():
    """主函数"""
    fixer = ChromeFixTool()
    fixer.run_full_fix()

if __name__ == "__main__":
    main() 