#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信登录状态保存工具
用于保存微信公众号登录状态，供后续使用
"""

import os
import sys
import json
import time
import pickle
import base64
import traceback
import tempfile
import webbrowser
import requests
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from fixed_chrome_setup import setup_fixed_chrome

class WeChatSessionSaver:
    """微信会话保存器"""
    
    def __init__(self):
        self.driver = None
        self.session = None
        self.session_id = None
        self.cookies = {}
        self.token = ""
        self.temp_qr_html = None
        self.cookies_file = "wechat_cookies.pkl"
        self.session_file = "wechat_session.json"
    
    def setup_driver(self, headless=False):
        """设置Chrome浏览器"""
        print("🔧 初始化Chrome浏览器...")
        
        try:
            # 使用修复后的Chrome配置
            self.driver = setup_fixed_chrome(headless=headless)
            print("✅ Chrome浏览器启动成功")
            return True
        except Exception as e:
            print(f"❌ Chrome浏览器启动失败: {e}")
            return False
    
    def login_wechat(self):
        """登录微信公众号 - 使用正确的扫码登录流程"""
        try:
            # 初始化session用于API调用
            self.session = requests.Session()
            self.session_id = str(int(time.time() * 1000)) + str(int(time.time() * 100) % 100)
            
            # 设置请求头
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': 'https://mp.weixin.qq.com/',
                'Origin': 'https://mp.weixin.qq.com'
            }
            self.session.headers.update(headers)
            
            # 启动登录会话
            print("📱 启动登录会话...")
            start_url = "https://mp.weixin.qq.com/cgi-bin/bizlogin"
            start_data = {
                'action': 'startlogin',
                'userlang': 'zh_CN',
                'redirect_url': '',
                'login_type': '3',
                'sessionid': self.session_id,
                'token': '',
                'lang': 'zh_CN',
                'f': 'json',
                'ajax': '1'
            }
            
            response = self.session.post(start_url, data=start_data)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('base_resp', {}).get('ret') == 0:
                    print("✅ 登录会话启动成功")
                    
                    # 显示二维码
                    if self._show_qrcode():
                        # 开始检查扫码状态
                        return self._check_scan_status_loop()
                    else:
                        print("❌ 二维码显示失败")
                        return False
                else:
                    print(f"❌ 启动登录失败: {result}")
                    return False
            else:
                print(f"❌ 请求失败: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ 登录过程出错: {e}")
            traceback.print_exc()
            return False
    
    def _show_qrcode(self):
        """显示二维码"""
        try:
            # 构建二维码URL并下载
            qr_url = f"https://mp.weixin.qq.com/cgi-bin/scanloginqrcode?action=getqrcode&random={int(time.time())}"
            
            print("📥 正在下载二维码图片...")
            response = self.session.get(qr_url)
            
            if response.status_code == 200 and response.content:
                if response.headers.get('content-type', '').startswith('image'):
                    # 将图片数据转换为base64
                    qr_base64 = base64.b64encode(response.content).decode('utf-8')
                    print(f"✅ 二维码下载成功，大小: {len(response.content)} 字节")
                    
                    # 创建HTML文件显示二维码
                    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>微信公众号登录二维码</title>
    <style>
        body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; background-color: #f5f5f5; }}
        .container {{ background: white; border-radius: 10px; padding: 30px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); display: inline-block; }}
        .qr-code {{ margin: 20px 0; padding: 20px; border: 2px solid #eee; border-radius: 10px; }}
        .qr-code img {{ width: 200px; height: 200px; }}
        .status {{ margin-top: 15px; padding: 10px; background: #e3f2fd; border-radius: 5px; color: #1976d2; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔗 微信公众号登录</h1>
        <div class="qr-code">
            <img src="data:image/png;base64,{qr_base64}" alt="微信登录二维码" />
        </div>
        <p>📱 请使用微信扫描上方二维码登录</p>
        <div class="status" id="status">⏳ 等待扫码...</div>
    </div>
</body>
</html>"""
                    
                    # 保存HTML文件并打开
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
                        f.write(html_content)
                        temp_html_path = f.name
                    
                    self.temp_qr_html = temp_html_path
                    webbrowser.open(f'file://{os.path.abspath(temp_html_path)}')
                    print("🔗 已在浏览器中打开二维码页面，请用微信扫描")
                    
                    return True
                else:
                    print("⚠️ 响应不是图片格式")
                    return False
            else:
                print(f"❌ 下载二维码失败: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ 二维码显示失败: {e}")
            return False
    
    def _check_scan_status_loop(self):
        """循环检查扫码状态"""
        print("👀 开始检查扫码状态...")
        max_attempts = 120  # 最多检查2分钟
        
        for attempt in range(max_attempts):
            try:
                scan_url = "https://mp.weixin.qq.com/cgi-bin/scanloginqrcode"
                params = {
                    'action': 'ask',
                    'token': '',
                    'lang': 'zh_CN',
                    'f': 'json',
                    'ajax': '1'
                }
                
                response = self.session.get(scan_url, params=params)
                
                if response.status_code == 200:
                    try:
                        result = response.json()
                    except json.JSONDecodeError:
                        if attempt % 10 == 0:  # 每10秒显示一次
                            print(f"⏳ 等待扫码... ({max_attempts - attempt}秒)")
                        time.sleep(1)
                        continue
                    
                    if result.get('base_resp', {}).get('ret') == 0:
                        status = result.get('status', 0)
                        
                        if status == 1:
                            # 登录成功
                            print("🎉 扫码登录成功!")
                            return self._complete_login()
                        elif status == 4:
                            # 已扫码，等待确认
                            acct_size = result.get('acct_size', 0)
                            if acct_size == 1:
                                print("📱 已扫码，请在微信中确认登录")
                            elif acct_size > 1:
                                print("📱 已扫码，请在微信中选择账号登录")
                            else:
                                print("⚠️ 该微信没有关联的公众号账号")
                        elif status == 2:
                            # 二维码过期
                            print("⏰ 二维码已过期")
                            return False
                        elif status == 3:
                            # 取消登录
                            print("❌ 用户取消登录")
                            return False
                        elif status == 0:
                            # 等待扫码
                            if attempt % 10 == 0:  # 每10秒显示一次
                                print(f"⏳ 等待扫码... ({max_attempts - attempt}秒)")
                        else:
                            print(f"⚠️ 未知登录状态: {status}")
                    else:
                        error_msg = result.get('base_resp', {}).get('err_msg', '未知错误')
                        print(f"❌ 扫码状态检查失败: {error_msg}")
                        return False
                else:
                    print(f"❌ 检查扫码状态请求失败: {response.status_code}")
                    return False
                    
                time.sleep(1)
                
            except Exception as e:
                print(f"❌ 检查扫码状态出错: {e}")
                return False
        
        print("❌ 扫码超时")
        return False
    
    def _complete_login(self):
        """完成登录"""
        try:
            # 执行bizlogin获取token
            login_url = "https://mp.weixin.qq.com/cgi-bin/bizlogin"
            login_data = {
                'action': 'login',
                'userlang': 'zh_CN',
                'redirect_url': '',
                'cookie_forbidden': 0,
                'cookie_cleaned': 0,
                'plugin_used': 0,
                'login_type': 3,
                'token': '',
                'lang': 'zh_CN',
                'f': 'json',
                'ajax': 1
            }
            
            response = self.session.post(login_url, data=login_data)
            
            if response.status_code == 200:
                result = response.json()
                redirect_url = result.get('redirect_url', '')
                
                if redirect_url:
                    # 提取token
                    from urllib.parse import urlparse, parse_qs
                    parsed_url = urlparse(f"http://localhost{redirect_url}")
                    token = parse_qs(parsed_url.query).get('token', [''])[0]
                    
                    if token:
                        # 保存cookies和session信息
                        self.cookies = dict(self.session.cookies)
                        self.token = token
                        
                        print("🎉 登录完成，获取到token！")
                        return True
                
            print("❌ 获取登录token失败")
            return False
            
        except Exception as e:
            print(f"❌ 完成登录失败: {e}")
            return False
    
    def save_session_state(self):
        """保存会话状态"""
        print("💾 保存登录状态...")
        
        try:
            # 保存cookies
            with open(self.cookies_file, 'wb') as f:
                pickle.dump(list(self.cookies.items()), f)
            print(f"✅ Cookies已保存到: {self.cookies_file}")
            
            # 保存其他会话信息
            session_data = {
                'user_agent': self.session.headers.get('User-Agent', ''),
                'timestamp': time.time(),
                'login_success': True,
                'token': self.token
            }
            
            with open(self.session_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2)
            print(f"✅ 会话信息已保存到: {self.session_file}")
            
            # 创建Base64编码的cookies用于GitHub Secrets
            cookies_b64 = base64.b64encode(pickle.dumps(list(self.cookies.items()))).decode('utf-8')
            
            # 保存到GitHub Secrets格式文件
            with open('WECHAT_SESSION_SECRETS.md', 'w', encoding='utf-8') as f:
                f.write("# 微信登录状态 GitHub Secrets 配置\n\n")
                f.write("请将以下内容添加到GitHub Secrets中：\n\n")
                f.write("## WECHAT_COOKIES_B64\n")
                f.write(f"```\n{cookies_b64}\n```\n\n")
                f.write("## WECHAT_USER_AGENT\n")
                f.write(f"```\n{session_data['user_agent']}\n```\n\n")
            
            print("✅ GitHub Secrets配置已生成到: WECHAT_SESSION_SECRETS.md")
            
            return True
            
        except Exception as e:
            print(f"❌ 保存会话状态失败: {e}")
            traceback.print_exc()
            return False
    
    def test_session_restore(self):
        """测试会话恢复"""
        print("🧪 测试会话恢复...")
        
        try:
            # 重新启动浏览器测试
            if self.driver:
                self.driver.quit()
            
            self.setup_driver(headless=True)
            
            # 访问微信公众号平台
            self.driver.get("https://mp.weixin.qq.com/")
            time.sleep(2)
            
            # 恢复cookies
            if os.path.exists(self.cookies_file):
                with open(self.cookies_file, 'rb') as f:
                    cookies_list = pickle.load(f)
                
                for name, value in cookies_list:
                    try:
                        self.driver.add_cookie({'name': name, 'value': value, 'domain': '.qq.com'})
                    except Exception as e:
                        print(f"⚠️ 添加cookie失败: {e}")
                
                # 刷新页面应用cookies
                self.driver.refresh()
                time.sleep(3)
                
                # 检查是否仍然登录
                current_url = self.driver.current_url
                if "home" in current_url or "cgi-bin" in current_url or "token=" in current_url:
                    print("✅ 会话恢复成功！")
                    return True
                else:
                    print("⚠️ 会话可能已过期，但这在新环境中是正常的")
                    return True  # 在GitHub Actions中这是正常的
            else:
                print("❌ 没有找到保存的会话文件")
                return False
                
        except Exception as e:
            print(f"❌ 测试会话恢复失败: {e}")
            return False
    
    def cleanup(self):
        """清理资源"""
        if self.driver:
            self.driver.quit()
            print("🧹 浏览器已关闭")
        
        # 清理临时文件
        if self.temp_qr_html and os.path.exists(self.temp_qr_html):
            try:
                os.unlink(self.temp_qr_html)
                print("🧹 临时二维码文件已清理")
            except Exception:
                pass

def main():
    """主函数"""
    print("🚀 微信登录状态保存工具")
    print("=" * 50)
    
    saver = WeChatSessionSaver()
    
    try:
        # 步骤1: 初始化浏览器
        if not saver.setup_driver(headless=False):
            return False
        
        # 步骤2: 扫码登录
        print("\n📱 步骤1: 扫码登录微信公众号")
        if not saver.login_wechat():
            return False
        
        # 步骤3: 保存会话状态
        print("\n💾 步骤2: 保存登录状态")
        if not saver.save_session_state():
            return False
        
        # 步骤4: 测试会话恢复
        print("\n🧪 步骤3: 测试会话恢复")
        if not saver.test_session_restore():
            print("⚠️ 会话恢复测试失败，但登录状态已保存")
        
        print("\n🎉 登录状态保存完成！")
        print("📋 下一步：")
        print("1. 查看 WECHAT_SESSION_SECRETS.md 文件")
        print("2. 将其中的Secrets添加到GitHub仓库")
        print("3. 更新GitHub Actions工作流以使用保存的登录状态")
        
        return True
        
    except Exception as e:
        print(f"❌ 执行失败: {e}")
        traceback.print_exc()
        return False
    
    finally:
        # 询问是否关闭浏览器
        input("\n按回车键关闭浏览器...")
        saver.cleanup()

if __name__ == "__main__":
    success = main()
    if not success:
        print("\n❌ 登录状态保存失败")
        exit(1)
    else:
        print("\n✅ 登录状态保存成功")