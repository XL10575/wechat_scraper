#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信会话管理器
处理微信登录状态的保存、恢复和验证
"""

import os
import json
import pickle
import base64
import time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from loguru import logger

class WeChatSessionManager:
    """微信会话管理器"""
    
    def __init__(self):
        self.session_file = "wechat_session.json"
        self.cookies_file = "wechat_cookies.pkl"
        
    def has_saved_session(self):
        """检查是否有保存的会话"""
        return os.path.exists(self.cookies_file) and os.path.exists(self.session_file)
    
    def is_session_valid(self):
        """检查保存的会话是否仍然有效"""
        if not self.has_saved_session():
            return False
            
        try:
            # 检查会话文件时间戳
            with open(self.session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
            
            # 如果会话超过24小时，认为可能已失效
            current_time = time.time()
            session_time = session_data.get('timestamp', 0)
            
            if current_time - session_time > 24 * 3600:  # 24小时
                logger.warning("会话超过24小时，可能已失效")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"检查会话有效性失败: {e}")
            return False
    
    def apply_session_to_driver(self, driver):
        """将保存的会话应用到浏览器驱动"""
        if not self.has_saved_session():
            logger.warning("没有找到保存的会话")
            return False
            
        try:
            logger.info("🔐 恢复微信登录状态...")
            
            # 首先访问微信公众号平台以设置正确的域
            driver.get("https://mp.weixin.qq.com/")
            time.sleep(2)
            
            # 加载并应用cookies
            with open(self.cookies_file, 'rb') as f:
                cookies = pickle.load(f)
            
            successful_cookies = 0
            for cookie in cookies:
                try:
                    driver.add_cookie(cookie)
                    successful_cookies += 1
                except Exception as e:
                    logger.debug(f"添加cookie失败: {e}")
            
            logger.info(f"✅ 成功恢复 {successful_cookies}/{len(cookies)} 个cookies")
            
            # 设置用户代理（如果有保存的话）
            try:
                with open(self.session_file, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)
                    
                user_agent = session_data.get('user_agent')
                if user_agent:
                    driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                        "userAgent": user_agent
                    })
                    logger.debug(f"设置用户代理: {user_agent[:50]}...")
                    
            except Exception as e:
                logger.debug(f"设置用户代理失败: {e}")
            
            # 刷新页面以应用会话
            driver.refresh()
            time.sleep(3)
            
            return True
            
        except Exception as e:
            logger.error(f"恢复会话失败: {e}")
            return False
    
    def verify_login_status(self, driver):
        """验证登录状态"""
        try:
            current_url = driver.current_url
            title = driver.title
            
            # 检查URL和标题来判断是否已登录
            if "home" in current_url or "cgi-bin" in current_url:
                logger.success("✅ 微信登录状态有效")
                return True
            elif "微信公众平台" in title and "登录" not in title:
                logger.success("✅ 微信登录状态有效")
                return True
            else:
                logger.warning("❌ 微信登录状态无效，需要重新登录")
                return False
                
        except Exception as e:
            logger.error(f"验证登录状态失败: {e}")
            return False
    
    def save_session_from_driver(self, driver):
        """从浏览器驱动保存会话"""
        try:
            logger.info("💾 保存微信登录状态...")
            
            # 保存cookies
            cookies = driver.get_cookies()
            with open(self.cookies_file, 'wb') as f:
                pickle.dump(cookies, f)
            
            # 保存会话信息
            session_data = {
                'current_url': driver.current_url,
                'title': driver.title,
                'user_agent': driver.execute_script("return navigator.userAgent;"),
                'timestamp': time.time(),
                'login_success': True
            }
            
            with open(self.session_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2)
            
            logger.success(f"✅ 会话已保存: {len(cookies)} cookies")
            return True
            
        except Exception as e:
            logger.error(f"保存会话失败: {e}")
            return False
    
    def get_session_info(self):
        """获取会话信息"""
        if not self.has_saved_session():
            return None
            
        try:
            with open(self.session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
            
            # 计算会话年龄
            current_time = time.time()
            session_time = session_data.get('timestamp', 0)
            age_hours = (current_time - session_time) / 3600
            
            return {
                'timestamp': session_data.get('timestamp'),
                'age_hours': age_hours,
                'user_agent': session_data.get('user_agent', '')[:50] + '...',
                'login_success': session_data.get('login_success', False)
            }
            
        except Exception as e:
            logger.error(f"读取会话信息失败: {e}")
            return None
    
    def clear_session(self):
        """清除保存的会话"""
        try:
            files_removed = 0
            if os.path.exists(self.cookies_file):
                os.remove(self.cookies_file)
                files_removed += 1
                
            if os.path.exists(self.session_file):
                os.remove(self.session_file)
                files_removed += 1
            
            logger.info(f"🗑️ 已清除 {files_removed} 个会话文件")
            return True
            
        except Exception as e:
            logger.error(f"清除会话失败: {e}")
            return False
    
    def restore_from_base64(self, cookies_b64, user_agent=None):
        """从Base64编码的cookies恢复会话（用于GitHub Actions）"""
        try:
            logger.info("🔄 从Base64数据恢复微信会话...")
            
            # 解码cookies
            cookies_data = base64.b64decode(cookies_b64)
            cookies = pickle.loads(cookies_data)
            
            # 保存cookies到文件
            with open(self.cookies_file, 'wb') as f:
                pickle.dump(cookies, f)
            
            # 创建会话信息
            session_data = {
                'user_agent': user_agent or 'Mozilla/5.0 (Linux x86_64) GitHub Actions',
                'timestamp': time.time(),
                'login_success': True,
                'restored_from_github': True
            }
            
            with open(self.session_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2)
            
            logger.success(f"✅ 从GitHub恢复了 {len(cookies)} 个cookies")
            return True
            
        except Exception as e:
            logger.error(f"从Base64恢复会话失败: {e}")
            return False

def setup_chrome_with_session(headless=True, session_manager=None):
    """设置Chrome浏览器并应用会话"""
    chrome_options = Options()
    
    if headless:
        chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # 设置默认用户代理
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    if session_manager and session_manager.has_saved_session():
        try:
            with open(session_manager.session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
                saved_ua = session_data.get('user_agent')
                if saved_ua:
                    user_agent = saved_ua
        except:
            pass
    
    chrome_options.add_argument(f"--user-agent={user_agent}")
    
    try:
        # 使用修复后的Chrome配置
        chrome_options.binary_location = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        
        # 查找正确的ChromeDriver路径
        import glob
        import os
        driver_path = None
        
        # 尝试使用webdriver-manager获取基础路径
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            base_path = ChromeDriverManager().install()
            base_dir = os.path.dirname(base_path)
            
            # 查找实际的chromedriver.exe文件
            possible_paths = [
                os.path.join(base_dir, "chromedriver.exe"),
                os.path.join(base_dir, "chromedriver-win32", "chromedriver.exe"),
                base_path if base_path.endswith(".exe") else None
            ]
            
            for path in possible_paths:
                if path and os.path.exists(path) and path.endswith(".exe"):
                    driver_path = path
                    break
            
            # 如果还没找到，使用通配符搜索
            if not driver_path:
                search_patterns = [
                    os.path.join(os.path.dirname(base_dir), "**", "chromedriver.exe"),
                    os.path.join(base_dir, "**", "chromedriver.exe")
                ]
                
                for pattern in search_patterns:
                    matches = glob.glob(pattern, recursive=True)
                    if matches:
                        driver_path = matches[0]
                        break
        except:
            pass
        
        # 如果仍然没找到，使用默认路径
        if not driver_path:
            driver_path = ChromeDriverManager().install()
        
        service = webdriver.chrome.service.Service(driver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # 如果有会话管理器，尝试恢复会话
        if session_manager and session_manager.has_saved_session():
            session_manager.apply_session_to_driver(driver)
        
        return driver
        
    except Exception as e:
        logger.error(f"设置Chrome浏览器失败: {e}")
        return None 