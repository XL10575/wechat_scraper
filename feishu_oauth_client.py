#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞书OAuth2客户端 - 获取和管理用户身份令牌
支持获取refresh_token并自动刷新access_token
"""

import os
import json
import time
import webbrowser
import requests
from urllib.parse import urlencode, parse_qs, urlparse
from loguru import logger
import http.server
import socketserver
import threading
from typing import Optional, Dict


class FeishuOAuth2Client:
    """飞书OAuth2客户端"""
    
    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self.base_url = "https://open.feishu.cn/open-apis"
        self.redirect_uri = "http://localhost:8080/callback"
        self.token_file = "feishu_oauth_tokens.json"
        
        # 需要的权限范围
        self.scope = "drive:drive drive:file drive:file:upload wiki:wiki wiki:space wiki:space:readonly docs:document docs:document:readonly"
        
        # 存储授权结果
        self.auth_code = None
        self.auth_result = {}
        
    def start_oauth_flow(self) -> bool:
        """开始OAuth2授权流程"""
        try:
            logger.info("🚀 开始OAuth2授权流程...")
            
            # 1. 启动本地回调服务器
            logger.info("📡 启动本地回调服务器...")
            server_thread = threading.Thread(target=self._start_callback_server, daemon=True)
            server_thread.start()
            
            # 等待服务器启动
            time.sleep(1)
            
            # 2. 构造授权URL
            auth_url = self._build_auth_url()
            logger.info(f"🔗 授权URL: {auth_url}")
            
            # 3. 打开浏览器进行授权
            logger.info("🌐 正在打开浏览器进行授权...")
            webbrowser.open(auth_url)
            
            # 4. 等待用户授权回调
            logger.info("⏳ 等待用户授权（请在浏览器中完成授权）...")
            max_wait_time = 300  # 5分钟超时
            start_time = time.time()
            
            while not self.auth_code and (time.time() - start_time) < max_wait_time:
                time.sleep(1)
            
            if not self.auth_code:
                logger.error("❌ 授权超时，请重试")
                return False
            
            logger.success("✅ 获取到授权码!")
            
            # 5. 用授权码换取token
            if self._exchange_code_for_tokens():
                logger.success("🎉 OAuth2授权流程完成!")
                return True
            else:
                logger.error("❌ 获取令牌失败")
                return False
                
        except Exception as e:
            logger.error(f"OAuth2授权流程异常: {e}")
            return False
    
    def _build_auth_url(self) -> str:
        """构造授权URL"""
        params = {
            'app_id': self.app_id,
            'redirect_uri': self.redirect_uri,
            'scope': self.scope,
            'state': 'feishu_pdf_uploader'  # 防CSRF攻击的状态参数
        }
        
        auth_url = f"https://open.feishu.cn/open-apis/authen/v1/index?{urlencode(params)}"
        return auth_url
    
    def _start_callback_server(self):
        """启动本地回调服务器"""
        class CallbackHandler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, oauth_client=None, **kwargs):
                self.oauth_client = oauth_client
                super().__init__(*args, **kwargs)
            
            def do_GET(self):
                if self.path.startswith('/callback'):
                    # 解析回调参数
                    parsed_url = urlparse(self.path)
                    params = parse_qs(parsed_url.query)
                    
                    if 'code' in params:
                        self.oauth_client.auth_code = params['code'][0]
                        
                        # 返回成功页面
                        self.send_response(200)
                        self.send_header('Content-type', 'text/html; charset=utf-8')
                        self.end_headers()
                        
                        success_html = """
                        <!DOCTYPE html>
                        <html>
                        <head>
                            <title>授权成功</title>
                            <meta charset="utf-8">
                        </head>
                        <body>
                            <h1>✅ 授权成功！</h1>
                            <p>您已成功授权飞书应用，现在可以关闭此页面。</p>
                            <script>
                                setTimeout(function() {
                                    window.close();
                                }, 3000);
                            </script>
                        </body>
                        </html>
                        """
                        self.wfile.write(success_html.encode('utf-8'))
                        
                        logger.success("📨 收到授权回调")
                    else:
                        # 授权失败
                        logger.error("❌ 授权回调中没有找到code参数")
                        self.send_response(400)
                        self.end_headers()
                else:
                    self.send_response(404)
                    self.end_headers()
            
            def log_message(self, format, *args):
                # 禁用默认日志输出
                pass
        
        # 创建带有oauth_client参数的handler
        def handler_factory(*args, **kwargs):
            return CallbackHandler(*args, oauth_client=self, **kwargs)
        
        try:
            with socketserver.TCPServer(("", 8080), handler_factory) as httpd:
                logger.debug("📡 回调服务器已启动在 http://localhost:8080")
                httpd.serve_forever()
        except Exception as e:
            logger.error(f"回调服务器启动失败: {e}")
    
    def _exchange_code_for_tokens(self) -> bool:
        """用授权码换取access_token和refresh_token"""
        try:
            url = f"{self.base_url}/authen/v1/access_token"
            
            data = {
                'grant_type': 'authorization_code',
                'app_id': self.app_id,
                'app_secret': self.app_secret,
                'code': self.auth_code,
                'redirect_uri': self.redirect_uri
            }
            
            # 使用application/json格式发送请求
            headers = {
                'Content-Type': 'application/json'
            }
            
            logger.info("🔄 正在用授权码换取令牌...")
            response = requests.post(url, json=data, headers=headers)
            
            logger.debug(f"响应状态码: {response.status_code}")
            logger.debug(f"响应内容: {response.text}")
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('code') == 0:
                    token_data = result.get('data', {})
                    
                    # 保存令牌信息
                    self.auth_result = {
                        'access_token': token_data.get('access_token'),
                        'refresh_token': token_data.get('refresh_token'),
                        'expires_in': token_data.get('expires_in'),
                        'token_type': token_data.get('token_type'),
                        'scope': token_data.get('scope'),
                        'created_at': int(time.time()),
                        'app_id': self.app_id
                    }
                    
                    # 保存到文件
                    self._save_tokens()
                    
                    logger.success("✅ 成功获取访问令牌和刷新令牌")
                    logger.info(f"📝 访问令牌: {self.auth_result['access_token'][:20]}...")
                    logger.info(f"🔄 刷新令牌: {self.auth_result['refresh_token'][:20]}...")
                    logger.info(f"⏰ 有效期: {self.auth_result['expires_in']} 秒")
                    
                    return True
                else:
                    logger.error(f"API错误: {result.get('msg')} (code: {result.get('code')})")
                    return False
            else:
                logger.error(f"HTTP错误: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"换取令牌异常: {e}")
            return False
    
    def _save_tokens(self):
        """保存令牌到文件"""
        try:
            with open(self.token_file, 'w', encoding='utf-8') as f:
                json.dump(self.auth_result, f, indent=2, ensure_ascii=False)
            logger.info(f"💾 令牌已保存到 {self.token_file}")
        except Exception as e:
            logger.error(f"保存令牌失败: {e}")
    
    def load_tokens(self) -> bool:
        """从文件加载令牌"""
        try:
            if not os.path.exists(self.token_file):
                return False
            
            with open(self.token_file, 'r', encoding='utf-8') as f:
                self.auth_result = json.load(f)
            
            logger.info("📂 从文件加载令牌成功")
            return True
        except Exception as e:
            logger.error(f"加载令牌失败: {e}")
            return False
    
    def get_valid_access_token(self) -> Optional[str]:
        """获取有效的访问令牌（自动刷新）"""
        # 首先尝试加载现有令牌
        if not self.auth_result:
            if not self.load_tokens():
                logger.warning("没有找到保存的令牌，需要重新授权")
                return None
        
        # 检查令牌是否过期
        if self._is_token_expired():
            logger.info("🔄 访问令牌已过期，正在刷新...")
            if not self._refresh_access_token():
                logger.error("刷新令牌失败，需要重新授权")
                return None
        
        return self.auth_result.get('access_token')
    
    def _is_token_expired(self) -> bool:
        """检查令牌是否过期"""
        if not self.auth_result:
            return True
        
        created_at = self.auth_result.get('created_at', 0)
        expires_in = self.auth_result.get('expires_in', 0)
        
        # 提前5分钟认为过期
        expiry_time = created_at + expires_in - 300
        current_time = int(time.time())
        
        return current_time >= expiry_time
    
    def _refresh_access_token(self) -> bool:
        """使用refresh_token刷新access_token"""
        try:
            if not self.auth_result.get('refresh_token'):
                logger.error("没有refresh_token，无法刷新")
                return False
            
            url = f"{self.base_url}/authen/v1/refresh_access_token"
            
            data = {
                'grant_type': 'refresh_token',
                'refresh_token': self.auth_result['refresh_token'],
                'app_id': self.app_id,
                'app_secret': self.app_secret
            }
            
            headers = {
                'Content-Type': 'application/json'
            }
            
            logger.info("🔄 正在刷新访问令牌...")
            response = requests.post(url, json=data, headers=headers)
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('code') == 0:
                    token_data = result.get('data', {})
                    
                    # 更新令牌信息
                    self.auth_result.update({
                        'access_token': token_data.get('access_token'),
                        'expires_in': token_data.get('expires_in'),
                        'created_at': int(time.time())
                    })
                    
                    # 如果返回了新的refresh_token，也要更新
                    if token_data.get('refresh_token'):
                        self.auth_result['refresh_token'] = token_data.get('refresh_token')
                    
                    # 保存更新后的令牌
                    self._save_tokens()
                    
                    logger.success("✅ 访问令牌刷新成功")
                    return True
                else:
                    logger.error(f"刷新失败: {result.get('msg')} (code: {result.get('code')})")
                    return False
            else:
                logger.error(f"刷新请求失败: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"刷新令牌异常: {e}")
            return False
    
    def revoke_tokens(self):
        """撤销令牌并删除本地文件"""
        try:
            if os.path.exists(self.token_file):
                os.remove(self.token_file)
                logger.info("🗑️ 已删除本地令牌文件")
            
            self.auth_result = {}
            logger.info("✅ 令牌已撤销")
        except Exception as e:
            logger.error(f"撤销令牌失败: {e}")


def test_oauth_flow():
    """测试OAuth2流程"""
    app_id = "cli_a8c822312a75901c"
    app_secret = "NDbCyKEwEIA8CZo2KHyqueIOlcafErko"
    
    oauth_client = FeishuOAuth2Client(app_id, app_secret)
    
    logger.info("="*50)
    logger.info("测试OAuth2授权流程")
    logger.info("="*50)
    
    # 首先尝试获取有效令牌
    access_token = oauth_client.get_valid_access_token()
    
    if access_token:
        logger.success(f"✅ 已有有效访问令牌: {access_token[:20]}...")
    else:
        logger.info("需要重新授权...")
        
        # 开始新的授权流程
        if oauth_client.start_oauth_flow():
            access_token = oauth_client.get_valid_access_token()
            if access_token:
                logger.success(f"🎉 获取到新的访问令牌: {access_token[:20]}...")
            else:
                logger.error("❌ 授权流程完成但无法获取令牌")
        else:
            logger.error("❌ 授权流程失败")
    
    # 测试刷新功能
    if access_token:
        logger.info("🧪 测试令牌刷新功能...")
        if oauth_client._refresh_access_token():
            new_token = oauth_client.get_valid_access_token()
            logger.success(f"✅ 令牌刷新成功: {new_token[:20]}...")
        else:
            logger.warning("⚠️ 令牌刷新失败（可能不需要刷新）")


if __name__ == "__main__":
    test_oauth_flow() 