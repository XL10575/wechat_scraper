#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信文章下载工具GUI界面
简洁版本：支持单篇下载和多URL批量下载
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import threading
import queue
import os
import webbrowser
import re
from datetime import datetime
from loguru import logger
import sys
import json

# 导入我们的工具类
from simple_url_scraper import SimpleUrlScraper

# 🆕 导入链接收集器
from wechat_article_link_collector import WeChatLinkCollector

# 🆕 创建简化的链接收集器类（无GUI版本）
class SimplifiedLinkCollector:
    """简化版链接收集器，专门用于集成到主GUI中"""
    
    def __init__(self):
        """初始化"""
        import requests
        self.session = requests.Session()
        self.token = ""
        self.cookies = {}
        self.user_info = {}
        self.session_id = ""
        
        # 频率控制
        self.request_interval = 2.0
        self.last_request_time = 0
        
        # 数据存储
        self.collected_articles = []
        self.current_account = None
        
        # 设置请求头
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://mp.weixin.qq.com/',
            'Origin': 'https://mp.weixin.qq.com'
        }
        self.session.headers.update(headers)
    
    def _wait_for_rate_limit(self):
        """等待以避免触发频率限制"""
        import time
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.request_interval:
            wait_time = self.request_interval - time_since_last
            time.sleep(wait_time)
        
        self.last_request_time = time.time()
    
    def start_login_flow(self):
        """启动登录流程并显示二维码"""
        try:
            import time
            import base64
            import tempfile
            import webbrowser
            
            # 启动登录会话
            self.session_id = str(int(time.time() * 1000)) + str(int(time.time() * 100) % 100)
            
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
                    # 获取并显示二维码
                    return self._show_qrcode_and_wait()
            
            return False
            
        except Exception as e:
            logger.error(f"启动登录失败: {e}")
            return False
    
    def _show_qrcode_and_wait(self):
        """显示二维码并等待扫码"""
        try:
            import time
            import base64
            import tempfile
            import webbrowser
            
            # 获取二维码
            qr_url = f"https://mp.weixin.qq.com/cgi-bin/scanloginqrcode?action=getqrcode&random={int(time.time())}"
            response = self.session.get(qr_url)
            
            if response.status_code == 200 and response.content:
                # 生成二维码HTML页面
                qr_base64 = base64.b64encode(response.content).decode('utf-8')
                html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>RO自动更新 - 微信公众号登录</title>
    <style>
        body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; background-color: #f5f5f5; }}
        .container {{ background: white; border-radius: 10px; padding: 30px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); display: inline-block; }}
        h1 {{ color: #333; margin-bottom: 20px; }}
        .qr-code {{ margin: 20px 0; padding: 20px; border: 2px solid #eee; border-radius: 10px; }}
        .qr-code img {{ width: 200px; height: 200px; }}
        .instructions {{ color: #666; font-size: 16px; margin-top: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 RO自动更新 - 微信登录</h1>
        <div class="qr-code">
            <img src="data:image/png;base64,{qr_base64}" alt="微信登录二维码" />
        </div>
        <div class="instructions">
            📱 请使用微信扫描上方二维码登录<br>
            需要有公众号管理权限的微信账号<br><br>
            🤖 登录成功后将自动开始RO文章更新流程
        </div>
    </div>
</body>
</html>
"""
                
                # 保存并打开HTML文件
                with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
                    f.write(html_content)
                    temp_html_path = f.name
                
                webbrowser.open(f'file://{os.path.abspath(temp_html_path)}')
                
                # 开始检查登录状态
                return self._wait_for_login()
            
            return False
            
        except Exception as e:
            logger.error(f"显示二维码失败: {e}")
            return False
    
    def _wait_for_login(self):
        """等待登录完成"""
        try:
            import time
            
            for i in range(120):  # 等待最多2分钟
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
                        result = response.json()
                        
                        if result.get('base_resp', {}).get('ret') == 0:
                            status = result.get('status', 0)
                            
                            if status == 1:
                                # 登录成功
                                return self._complete_login()
                            elif status == 2:
                                # 二维码过期
                                return False
                            elif status == 3:
                                # 取消登录
                                return False
                    
                    time.sleep(1)
                    
                except Exception as e:
                    logger.warning(f"检查登录状态失败: {e}")
                    time.sleep(1)
            
            return False  # 超时
            
        except Exception as e:
            logger.error(f"等待登录失败: {e}")
            return False
    
    def _complete_login(self):
        """完成登录"""
        try:
            from urllib.parse import urlparse, parse_qs
            
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
                    parsed_url = urlparse(f"http://localhost{redirect_url}")
                    self.token = parse_qs(parsed_url.query).get('token', [''])[0]
                    
                    if self.token:
                        self.cookies = dict(self.session.cookies)
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"完成登录失败: {e}")
            return False
    
    def search_account(self, keyword):
        """搜索公众号"""
        try:
            if not self.token:
                return []
            
            self._wait_for_rate_limit()
            
            search_url = "https://mp.weixin.qq.com/cgi-bin/searchbiz"
            params = {
                'action': 'search_biz',
                'begin': 0,
                'count': 10,
                'query': keyword,
                'token': self.token,
                'lang': 'zh_CN',
                'f': 'json',
                'ajax': 1
            }
            
            response = self.session.get(search_url, params=params)
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('base_resp', {}).get('ret') == 0:
                    accounts = result.get('list', [])
                    
                    # 自动选择第一个结果
                    if accounts:
                        self.current_account = accounts[0]
                    
                    return accounts
            
            return []
            
        except Exception as e:
            logger.error(f"搜索账号失败: {e}")
            return []
    
    def collect_articles(self, limit, start_date, end_date):
        """收集文章"""
        try:
            if not self.current_account:
                return []
            
            import json
            from datetime import datetime, timedelta
            
            fakeid = self.current_account.get('fakeid', '')
            if not fakeid:
                return []
            
            collected_count = 0
            begin = 0
            page_size = 20
            
            # 计算时间范围
            start_timestamp = int(start_date.timestamp())
            end_timestamp = int((end_date + timedelta(days=1) - timedelta(seconds=1)).timestamp())
            
            # 收集符合时间范围的文章
            filtered_articles = []
            
            while collected_count < limit:
                self._wait_for_rate_limit()
                
                articles_url = "https://mp.weixin.qq.com/cgi-bin/appmsgpublish"
                params = {
                    'sub': 'list',
                    'search_field': 'null',
                    'begin': begin,
                    'count': page_size,
                    'query': '',
                    'fakeid': fakeid,
                    'type': '101_1',
                    'free_publish_type': 1,
                    'sub_action': 'list_ex',
                    'token': self.token,
                    'lang': 'zh_CN',
                    'f': 'json',
                    'ajax': 1
                }
                
                response = self.session.get(articles_url, params=params)
                
                if response.status_code == 200:
                    result = response.json()
                    
                    if result.get('base_resp', {}).get('ret') == 0:
                        # 解析文章列表
                        articles = self._parse_articles_from_response(result)
                        
                        if not articles:
                            break
                        
                        # 检查是否所有文章都早于起始时间
                        first_article_time = articles[0].get('update_time', 0) if articles else 0
                        if first_article_time < start_timestamp:
                            break
                        
                        # 过滤时间范围内的文章
                        for article in articles:
                            article_time = article.get('update_time', 0)
                            
                            if article_time < start_timestamp:
                                continue
                            
                            if article_time > end_timestamp:
                                continue
                            
                            # 构建文章信息
                            article_info = {
                                'title': article.get('title', ''),
                                'link': article.get('link', '').replace('\\/', '/'),
                                'author': article.get('author_name', ''),
                                'publish_time': datetime.fromtimestamp(article.get('update_time', 0)).strftime('%Y-%m-%d %H:%M:%S'),
                                'account_name': self.current_account.get('nickname', ''),
                                'account_alias': self.current_account.get('alias', ''),
                                'digest': article.get('digest', '')
                            }
                            filtered_articles.append(article_info)
                            collected_count += 1
                            
                            if collected_count >= limit:
                                break
                        
                        begin += page_size
                    else:
                        break
                else:
                    break
            
            # 按时间倒序排序
            filtered_articles.sort(key=lambda x: x.get('publish_time', ''), reverse=True)
            
            self.collected_articles = filtered_articles
            return filtered_articles
            
        except Exception as e:
            logger.error(f"收集文章失败: {e}")
            return []
    
    def _parse_articles_from_response(self, result):
        """从API响应中解析文章列表"""
        articles = []
        
        try:
            import json
            
            publish_page_str = result.get('publish_page', '')
            if not publish_page_str:
                return articles
            
            publish_page = json.loads(publish_page_str)
            publish_list = publish_page.get('publish_list', [])
            
            for publish_item in publish_list:
                publish_info_str = publish_item.get('publish_info', '')
                if not publish_info_str:
                    continue
                
                publish_info = json.loads(publish_info_str)
                appmsgex_list = publish_info.get('appmsgex', [])
                
                for appmsg in appmsgex_list:
                    article = {
                        'title': appmsg.get('title', ''),
                        'link': appmsg.get('link', ''),
                        'author_name': appmsg.get('author_name', ''),
                        'digest': appmsg.get('digest', ''),
                        'update_time': appmsg.get('update_time', 0),
                        'create_time': appmsg.get('create_time', 0)
                    }
                    articles.append(article)
            
        except Exception as e:
            logger.warning(f"解析文章列表出错: {e}")
        
        return articles


class WechatDownloaderGUI:
    """微信文章下载工具GUI"""
    
    def __init__(self, root):
        """初始化GUI"""
        self.root = root
        self.root.title("微信文章下载工具 v4.0 - 全自动化版")
        self.root.geometry("800x700")
        self.root.resizable(True, True)
        
        # 🆕 优先初始化消息队列，避免日志调用出错
        self.msg_queue = queue.Queue()
        
        # 设置图标和样式
        self.setup_styles()
        
        # 初始化工具类（懒加载）
        self.url_scraper = None
        self.scraper_initializing = False  # 防止重复初始化
        
        # 飞书API配置
        self.feishu_app_id = "cli_a8c822312a75901c"
        self.feishu_app_secret = "NDbCyKEwEIA8CZo2KHyqueIOlcafErko"
        self.feishu_space_id = "7511922459407450115"  # 数字格式的space_id
        self.feishu_client = None
        self.enable_feishu_upload = True  # 是否启用自动上传到飞书
        
        # 知识库分类配置
        self.wiki_locations = []  # 存储关键词-链接映射
        self.default_wiki_location = ""  # 默认转移位置
        
        # 🆕 链接收集器相关
        self.link_collector = None
        
        # 🆕 RO自动更新相关
        self.auto_update_enabled = False
        self.last_update_date = "2025-06-10"  # 知识库已有文章的最后日期
        self.ro_account_info = None  # RO公众号信息
        self.auto_update_status = ""
        
        # 定时器相关
        self.timer_enabled = False
        self.timer_interval = 60  # 默认60分钟
        self.timer_job_id = None  # 定时器任务ID
        self.next_update_time = None
        
        # GUI状态
        self.is_downloading = False
        self.output_dir = "output"
        
        # 自动收集和下载相关状态
        self.is_auto_collecting = False
        self.last_clipboard_content = ""
        self.collected_urls = set()  # 用于去重
        
        # 自动下载队列
        self.download_queue = queue.Queue()  # 下载队列
        self.is_queue_processing = False     # 队列处理状态
        self.current_downloading_url = None  # 当前下载的URL
        self.queue_stats = {"completed": 0, "failed": 0, "total": 0}
        
        # 自动下载格式设置
        self.auto_download_format = "pdf"  # 默认PDF格式
        
        # 🆕 现在可以安全地初始化知识库配置（会用到日志）
        self.init_default_wiki_config()
        
        # 创建GUI界面
        self.create_widgets()
        
        # 加载自动更新设置
        self.load_auto_update_settings()
        
        # 启动消息处理
        self.process_queue()
        
        logger.info("微信文章下载工具GUI初始化完成")
    
    def setup_styles(self):
        """设置GUI样式"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # 配置样式
        style.configure('Title.TLabel', font=('Arial', 16, 'bold'))
        style.configure('Header.TLabel', font=('Arial', 12, 'bold'))
        style.configure('Success.TLabel', foreground='green')
        style.configure('Error.TLabel', foreground='red')
    
    def create_widgets(self):
        """创建GUI组件"""
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # 标题
        title_label = ttk.Label(main_frame, text="🚀 微信文章下载工具", style='Title.TLabel')
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # 创建选项卡
        notebook = ttk.Notebook(main_frame)
        notebook.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        main_frame.rowconfigure(1, weight=1)
        
        # 单篇下载选项卡
        self.create_single_download_tab(notebook)
        
        # 批量下载选项卡
        self.create_batch_download_tab(notebook)
        
        # 🆕 链接收集器选项卡
        self.create_link_collector_tab(notebook)
        
        # 🆕 RO文章自动更新选项卡
        self.create_auto_update_tab(notebook)
        
        # 设置选项卡
        self.create_settings_tab(notebook)
        
        # 日志输出区域
        self.create_log_area(main_frame)
        
        # 底部状态栏
        self.create_status_bar(main_frame)
    
    def create_link_collector_tab(self, parent):
        """创建链接收集器选项卡"""
        frame = ttk.Frame(parent, padding="10")
        parent.add(frame, text="🔗 链接收集器")
        
        # 说明文字
        info_text = """
🔗 微信公众号链接收集器：
• 扫码登录微信公众号后台
• 搜索并选择目标公众号
• 设置时间范围，批量获取文章链接
• 支持导出CSV、JSON、TXT格式
• 可直接与下载功能配合使用
        """
        ttk.Label(frame, text=info_text.strip(), justify=tk.LEFT).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 15))
        
        # 登录区域
        login_frame = ttk.LabelFrame(frame, text="🔐 微信公众号登录", padding="10")
        login_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        login_frame.columnconfigure(1, weight=1)
        
        # 登录状态
        self.collector_login_status_var = tk.StringVar(value="未登录")
        ttk.Label(login_frame, text="登录状态:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.collector_login_status_label = ttk.Label(login_frame, textvariable=self.collector_login_status_var, 
                                                     foreground="red")
        self.collector_login_status_label.grid(row=0, column=1, sticky=tk.W)
        
        # 登录按钮
        collector_login_buttons = ttk.Frame(login_frame)
        collector_login_buttons.grid(row=0, column=2)
        
        self.collector_login_btn = ttk.Button(collector_login_buttons, text="🚀 开始登录", 
                                            command=self.start_collector_login)
        self.collector_login_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(collector_login_buttons, text="🔄 重新登录", 
                  command=self.retry_collector_login).pack(side=tk.LEFT)
        
        # 搜索区域
        search_frame = ttk.LabelFrame(frame, text="🔍 搜索公众号", padding="10")
        search_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        search_frame.columnconfigure(1, weight=1)
        
        ttk.Label(search_frame, text="搜索关键词:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.collector_search_var = tk.StringVar()
        self.collector_search_entry = ttk.Entry(search_frame, textvariable=self.collector_search_var, width=30)
        self.collector_search_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        
        self.collector_search_btn = ttk.Button(search_frame, text="🔍 搜索", 
                                             command=self.search_collector_accounts)
        self.collector_search_btn.grid(row=0, column=2)
        
        # 搜索结果显示
        result_frame = ttk.Frame(search_frame)
        result_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(0, weight=1)
        search_frame.rowconfigure(1, weight=1)
        
        # 简化的搜索结果显示
        self.collector_results_text = scrolledtext.ScrolledText(result_frame, height=5, width=80)
        self.collector_results_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 收集设置区域
        collect_frame = ttk.LabelFrame(frame, text="📥 文章收集设置", padding="10")
        collect_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        collect_frame.columnconfigure(1, weight=1)
        
        # 选中的公众号
        ttk.Label(collect_frame, text="选中公众号:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.collector_selected_var = tk.StringVar(value="未选择")
        ttk.Label(collect_frame, textvariable=self.collector_selected_var, 
                 foreground="blue").grid(row=0, column=1, sticky=tk.W)
        
        # 收集参数
        params_frame = ttk.Frame(collect_frame)
        params_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
        
        # 数量限制
        ttk.Label(params_frame, text="获取数量:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.collector_limit_var = tk.StringVar(value="50")
        ttk.Entry(params_frame, textvariable=self.collector_limit_var, width=10).grid(row=0, column=1, padx=(0, 20))
        
        # 日期范围
        ttk.Label(params_frame, text="起始日期:").grid(row=0, column=2, sticky=tk.W, padx=(0, 10))
        self.collector_start_date_var = tk.StringVar(value="2025-06-01")
        ttk.Entry(params_frame, textvariable=self.collector_start_date_var, width=12).grid(row=0, column=3, padx=(0, 20))
        
        ttk.Label(params_frame, text="结束日期:").grid(row=0, column=4, sticky=tk.W, padx=(0, 10))
        self.collector_end_date_var = tk.StringVar(value="2025-06-11")
        ttk.Entry(params_frame, textvariable=self.collector_end_date_var, width=12).grid(row=0, column=5, padx=(0, 20))
        
        # 操作按钮
        collect_buttons = ttk.Frame(collect_frame)
        collect_buttons.grid(row=2, column=0, columnspan=3, pady=(10, 0))
        
        self.collector_collect_btn = ttk.Button(collect_buttons, text="📥 收集链接", 
                                              command=self.start_collect_links)
        self.collector_collect_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(collect_buttons, text="📋 导出到批量下载", 
                  command=self.export_to_batch_download).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(collect_buttons, text="📄 导出CSV", 
                  command=self.export_collector_csv).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(collect_buttons, text="🗑️ 清空", 
                  command=self.clear_collector_data).pack(side=tk.LEFT)
        
        # 收集进度和状态
        self.collector_progress_var = tk.StringVar(value="")
        ttk.Label(collect_frame, textvariable=self.collector_progress_var).grid(row=3, column=0, columnspan=3, 
                                                                               sticky=tk.W, pady=(10, 0))
        
        self.collector_stats_var = tk.StringVar(value="已收集: 0 篇文章")
        ttk.Label(collect_frame, textvariable=self.collector_stats_var, 
                 font=("Arial", 12, "bold")).grid(row=4, column=0, columnspan=3, sticky=tk.W, pady=(5, 0))
        
        # 存储收集的数据
        self.collected_articles = []
    
    def create_auto_update_tab(self, parent):
        """创建RO文章自动更新选项卡"""
        frame = ttk.Frame(parent, padding="10")
        parent.add(frame, text="🤖 RO自动更新")
        
        # 说明文字
        info_text = """
🤖 仙境传说RO新启航 - 自动文章更新：
• 自动登录微信公众号后台
• 自动搜索"仙境传说RO新启航"公众号
• 根据日期增量更新最新文章到知识库
• 防漏检查：检查前3个节点确保无遗漏
• 自动记录更新进度，下次继续
        """
        ttk.Label(frame, text=info_text.strip(), justify=tk.LEFT).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 15))
        
        # 自动更新开关
        auto_switch_frame = ttk.LabelFrame(frame, text="🔧 自动更新设置", padding="10")
        auto_switch_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        auto_switch_frame.columnconfigure(1, weight=1)
        
        self.auto_update_enabled_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(auto_switch_frame, text="启用RO文章自动更新", 
                       variable=self.auto_update_enabled_var, 
                       command=self.toggle_auto_update).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))
        
        # 定时更新设置
        timer_frame = ttk.Frame(auto_switch_frame)
        timer_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E))
        timer_frame.columnconfigure(2, weight=1)
        
        self.timer_enabled_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(timer_frame, text="启用定时自动更新", 
                       variable=self.timer_enabled_var, 
                       command=self.toggle_timer_update).grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        
        ttk.Label(timer_frame, text="间隔:").grid(row=0, column=1, sticky=tk.W, padx=(10, 5))
        
        self.timer_interval_var = tk.StringVar(value="60")
        interval_entry = ttk.Entry(timer_frame, textvariable=self.timer_interval_var, width=8)
        interval_entry.grid(row=0, column=2, sticky=tk.W, padx=(0, 5))
        interval_entry.bind('<KeyRelease>', self.on_timer_interval_changed)
        
        ttk.Label(timer_frame, text="分钟").grid(row=0, column=3, sticky=tk.W, padx=(0, 10))
        
        # 下次更新时间显示
        self.next_update_time_var = tk.StringVar(value="定时器未启动")
        ttk.Label(timer_frame, text="下次更新:").grid(row=0, column=4, sticky=tk.W, padx=(10, 5))
        ttk.Label(timer_frame, textvariable=self.next_update_time_var, 
                 foreground="blue").grid(row=0, column=5, sticky=tk.W)
        
        # 更新状态显示
        status_frame = ttk.LabelFrame(frame, text="📊 更新状态", padding="10")
        status_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        status_frame.columnconfigure(1, weight=1)
        
        # 上次更新日期
        ttk.Label(status_frame, text="上次更新至:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.last_update_date_var = tk.StringVar(value=self.last_update_date)
        ttk.Label(status_frame, textvariable=self.last_update_date_var, 
                 foreground="blue").grid(row=0, column=1, sticky=tk.W)
        
        # 当前状态
        ttk.Label(status_frame, text="当前状态:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10))
        self.auto_update_status_var = tk.StringVar(value="等待启动")
        ttk.Label(status_frame, textvariable=self.auto_update_status_var, 
                 foreground="green").grid(row=1, column=1, sticky=tk.W)
        
        # RO公众号信息
        ttk.Label(status_frame, text="目标公众号:").grid(row=2, column=0, sticky=tk.W, padx=(0, 10))
        self.ro_account_status_var = tk.StringVar(value="仙境传说RO新启航 (未搜索)")
        ttk.Label(status_frame, textvariable=self.ro_account_status_var, 
                 foreground="orange").grid(row=2, column=1, sticky=tk.W)
        
        # 手动控制区域
        control_frame = ttk.LabelFrame(frame, text="🎮 手动控制", padding="10")
        control_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        control_buttons = ttk.Frame(control_frame)
        control_buttons.grid(row=0, column=0)
        
        self.manual_update_btn = ttk.Button(control_buttons, text="🚀 立即执行更新", 
                                          command=self.start_manual_update)
        self.manual_update_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(control_buttons, text="🔍 测试RO公众号搜索", 
                  command=self.test_ro_account_search).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(control_buttons, text="📅 重置更新日期", 
                  command=self.reset_update_date).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(control_buttons, text="📋 查看更新日志", 
                  command=self.view_update_log).pack(side=tk.LEFT)
        
        # 更新进度
        progress_frame = ttk.LabelFrame(frame, text="📈 更新进度", padding="10")
        progress_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        progress_frame.columnconfigure(0, weight=1)
        progress_frame.rowconfigure(0, weight=1)
        frame.rowconfigure(4, weight=1)
        
        self.auto_update_log = scrolledtext.ScrolledText(progress_frame, height=8, wrap=tk.WORD)
        self.auto_update_log.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 在启动时检查是否需要自动更新
        self.root.after(1000, self.check_auto_update_on_startup)
    
    def create_single_download_tab(self, parent):
        """创建单篇下载选项卡"""
        frame = ttk.Frame(parent, padding="10")
        parent.add(frame, text="📄 单篇下载")
        
        # URL输入
        ttk.Label(frame, text="微信文章URL:", style='Header.TLabel').grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.single_url_var = tk.StringVar()
        url_entry = ttk.Entry(frame, textvariable=self.single_url_var, width=60)
        url_entry.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        frame.columnconfigure(0, weight=1)
        
        # 格式选择
        ttk.Label(frame, text="输出格式:", style='Header.TLabel').grid(row=2, column=0, sticky=tk.W, pady=(5, 5))
        
        format_frame = ttk.Frame(frame)
        format_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.single_format_var = tk.StringVar(value="pdf")
        formats = [
            ("📑 PDF (推荐，保持完整格式)", "pdf"),
            ("📝 Word文档 (支持飞书直接上传)", "docx"),
            ("🌐 完整HTML (包含图片)", "complete_html"),
            ("📄 Markdown (飞书适用)", "individual"),
            ("📊 JSON数据", "json")
        ]
        
        for i, (text, value) in enumerate(formats):
            ttk.Radiobutton(format_frame, text=text, variable=self.single_format_var, 
                           value=value).grid(row=i//2, column=i%2, sticky=tk.W, padx=(0, 20))
        
        # 下载按钮
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=4, column=0, columnspan=2, pady=20)
        
        self.single_download_btn = ttk.Button(button_frame, text="🚀 开始下载", 
                                            command=self.start_single_download)
        self.single_download_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(button_frame, text="📁 打开下载目录", 
                  command=self.open_pdf_download_dir).pack(side=tk.LEFT)
        
        # 下载进度
        self.single_progress_var = tk.StringVar(value="就绪")
        ttk.Label(frame, textvariable=self.single_progress_var, style='Success.TLabel').grid(row=5, column=0, columnspan=2, pady=10)
    
    def create_batch_download_tab(self, parent):
        """创建批量下载选项卡"""
        frame = ttk.Frame(parent, padding="10")
        parent.add(frame, text="📚 批量下载")
        
        # 说明文字
        info_text = """
🚀 自动下载模式：
• 点击"开启自动下载模式"，然后复制微信文章链接即可自动下载PDF
• 多个链接会自动排队，依次下载，无需手动点击下载按钮
• 自动去重，跳过重复链接
• 文件保存在 output/auto_download/ 目录下
• 🔥 NEW: 支持自动上传到飞书知识库，在设置页面可开启/关闭
• 也可以手动粘贴多个链接到下方文本框，使用传统批量下载
        """
        ttk.Label(frame, text=info_text.strip(), justify=tk.LEFT).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 15))
        
        # URL输入区域
        ttk.Label(frame, text="微信文章URL列表 (每行一个):", style='Header.TLabel').grid(row=1, column=0, sticky=tk.W, pady=(0, 5))
        
        # URL文本框
        url_frame = ttk.Frame(frame)
        url_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(2, weight=1)
        url_frame.columnconfigure(0, weight=1)
        url_frame.rowconfigure(0, weight=1)
        
        self.batch_urls_text = scrolledtext.ScrolledText(url_frame, height=10, width=80)
        self.batch_urls_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 示例URL
        example_urls = """https://mp.weixin.qq.com/s?__biz=xxx&mid=xxx&idx=1&sn=xxx
https://mp.weixin.qq.com/s/abc123def456
https://mp.weixin.qq.com/s?a=b&c=d"""
        self.batch_urls_text.insert(tk.END, example_urls)
        
        # 自动下载格式选择
        format_frame = ttk.LabelFrame(frame, text="🎯 自动下载格式设置", padding="10")
        format_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        
        self.auto_format_var = tk.StringVar(value="pdf")
        self.auto_download_format = "pdf"  # 确保初始化
        
        format_options = [
            ("📑 PDF格式 (完整样式，推荐)", "pdf"),
            ("📝 Word文档 (支持飞书知识库)", "docx")
        ]
        
        for i, (text, value) in enumerate(format_options):
            ttk.Radiobutton(format_frame, text=text, variable=self.auto_format_var, 
                           value=value, command=self.update_auto_format).grid(row=0, column=i, sticky=tk.W, padx=(0, 30))
        
        # 操作按钮（第一行）
        batch_button_frame1 = ttk.Frame(frame)
        batch_button_frame1.grid(row=4, column=0, columnspan=2, pady=(15, 5))
        
        ttk.Button(batch_button_frame1, text="🧹 清空", 
                  command=self.clear_batch_urls).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(batch_button_frame1, text="📋 从剪贴板粘贴", 
                  command=self.paste_from_clipboard).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(batch_button_frame1, text="📁 从文件加载", 
                  command=self.load_urls_from_file).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(batch_button_frame1, text="🔄 去重", 
                  command=self.clean_duplicate_urls).pack(side=tk.LEFT, padx=(0, 10))
        
        # 自动下载按钮
        self.auto_download_btn = ttk.Button(batch_button_frame1, text="🚀 开启自动下载模式", 
                                          command=self.toggle_auto_download)
        self.auto_download_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 批量下载选项
        batch_options_frame = ttk.Frame(frame)
        batch_options_frame.grid(row=5, column=0, columnspan=2, pady=(5, 10))
        
        # 自动上传到飞书知识库勾选框
        self.batch_feishu_upload_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(batch_options_frame, text="📚 批量下载后自动上传到飞书知识库", 
                       variable=self.batch_feishu_upload_var).pack(side=tk.LEFT)
        
        # 操作按钮（第二行）
        batch_button_frame2 = ttk.Frame(frame)
        batch_button_frame2.grid(row=6, column=0, columnspan=2, pady=(5, 15))
        
        self.batch_download_btn = ttk.Button(batch_button_frame2, text="🚀 开始批量下载", 
                                           command=self.start_batch_download)
        self.batch_download_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(batch_button_frame2, text="📁 打开下载目录", 
                  command=self.open_pdf_download_dir).pack(side=tk.LEFT, padx=(0, 10))
        
        # 自动下载状态显示
        self.auto_download_status = tk.StringVar(value="")
        ttk.Label(batch_button_frame2, textvariable=self.auto_download_status, 
                 style='Success.TLabel').pack(side=tk.LEFT, padx=(20, 0))
        
        # 批量下载进度
        self.batch_progress_var = tk.StringVar(value="准备就绪")
        ttk.Label(frame, textvariable=self.batch_progress_var, style='Success.TLabel').grid(row=7, column=0, columnspan=2, pady=10)
        
        # 下载统计
        self.batch_stats_var = tk.StringVar(value="")
        ttk.Label(frame, textvariable=self.batch_stats_var, style='Header.TLabel').grid(row=8, column=0, columnspan=2, pady=5)
    
    def create_settings_tab(self, parent):
        """创建设置选项卡"""
        frame = ttk.Frame(parent, padding="10")
        parent.add(frame, text="⚙️ 设置")
        
        # 创建滚动框架以容纳更多内容
        canvas = tk.Canvas(frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        # 配置滚动区域
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 布局Canvas和滚动条 - 确保Canvas占满宽度
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 绑定Canvas宽度到scrollable_frame，确保内容充满宽度
        def configure_scrollable_frame(event):
            canvas.itemconfig(canvas.find_all()[0], width=event.width)
        canvas.bind('<Configure>', configure_scrollable_frame)
        
        # 输出目录设置
        ttk.Label(scrollable_frame, text="输出目录:", style='Header.TLabel').grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        dir_frame = ttk.Frame(scrollable_frame)
        dir_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        scrollable_frame.columnconfigure(0, weight=1)
        dir_frame.columnconfigure(0, weight=1)
        
        self.output_dir_var = tk.StringVar(value=self.output_dir)
        ttk.Entry(dir_frame, textvariable=self.output_dir_var, state='readonly').grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))
        ttk.Button(dir_frame, text="浏览", command=self.browse_output_dir).grid(row=0, column=1)
        
        # 浏览器设置
        ttk.Label(scrollable_frame, text="浏览器模式:", style='Header.TLabel').grid(row=2, column=0, sticky=tk.W, pady=(15, 5))
        
        self.headless_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(scrollable_frame, text="无头模式 (后台运行，但可能无法处理验证码)", 
                       variable=self.headless_var).grid(row=3, column=0, sticky=tk.W, pady=(0, 15))
        
        # 飞书集成设置
        ttk.Label(scrollable_frame, text="飞书知识库集成:", style='Header.TLabel').grid(row=4, column=0, sticky=tk.W, pady=(15, 5))
        
        self.feishu_upload_var = tk.BooleanVar(value=self.enable_feishu_upload)
        ttk.Checkbutton(scrollable_frame, text="自动上传PDF到飞书知识库", 
                       variable=self.feishu_upload_var, 
                       command=self.toggle_feishu_upload).grid(row=5, column=0, sticky=tk.W, pady=(0, 5))
        
        # 飞书状态显示
        self.feishu_status_var = tk.StringVar(value="⚠️ 飞书集成已启用（仅检测模式）")
        ttk.Label(scrollable_frame, textvariable=self.feishu_status_var, 
                 style='Warning.TLabel').grid(row=6, column=0, sticky=tk.W, pady=(0, 5))
        
        # 🆕 OAuth认证状态和重新认证功能
        oauth_frame = ttk.LabelFrame(scrollable_frame, text="🔐 OAuth认证管理", padding="5")
        oauth_frame.grid(row=7, column=0, sticky=(tk.W, tk.E), pady=(5, 15))
        oauth_frame.columnconfigure(0, weight=1)
        
        # 认证状态显示
        self.oauth_status_var = tk.StringVar()
        self.oauth_status_label = ttk.Label(oauth_frame, textvariable=self.oauth_status_var, 
                                           foreground='blue')
        self.oauth_status_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        # 认证操作按钮
        oauth_buttons_frame = ttk.Frame(oauth_frame)
        oauth_buttons_frame.grid(row=1, column=0, sticky=tk.W)
        
        self.oauth_reauth_btn = ttk.Button(oauth_buttons_frame, text="🔄 重新认证", 
                                          command=self.start_oauth_reauth)
        self.oauth_reauth_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(oauth_buttons_frame, text="🔍 检查状态", 
                  command=self.check_oauth_status).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(oauth_buttons_frame, text="❌ 撤销认证", 
                  command=self.revoke_oauth_tokens).pack(side=tk.LEFT)
        
        # 初始化OAuth状态检查
        self.check_oauth_status()
        
        # 🆕 知识库智能分类设置
        self.create_wiki_location_settings(scrollable_frame, 8)
        
        # 批量下载设置
        ttk.Label(scrollable_frame, text="批量下载设置:", style='Header.TLabel').grid(row=20, column=0, sticky=tk.W, pady=(15, 5))
        
        # 延迟设置
        delay_frame = ttk.Frame(scrollable_frame)
        delay_frame.grid(row=21, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(delay_frame, text="下载延迟(秒):").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.delay_var = tk.StringVar(value="3")
        delay_spin = ttk.Spinbox(delay_frame, from_=1, to=10, width=10, textvariable=self.delay_var)
        delay_spin.grid(row=0, column=1, sticky=tk.W)
        ttk.Label(delay_frame, text="(防止被限制)").grid(row=0, column=2, sticky=tk.W, padx=(10, 0))
        
        # 重试设置
        retry_frame = ttk.Frame(scrollable_frame)
        retry_frame.grid(row=22, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        
        ttk.Label(retry_frame, text="失败重试次数:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.retry_var = tk.StringVar(value="2")
        retry_spin = ttk.Spinbox(retry_frame, from_=0, to=5, width=10, textvariable=self.retry_var)
        retry_spin.grid(row=0, column=1, sticky=tk.W)
        
        # 关于信息
        about_frame = ttk.LabelFrame(scrollable_frame, text="📖 关于", padding="10")
        about_frame.grid(row=23, column=0, sticky=(tk.W, tk.E), pady=15)
        
        about_text = """
微信文章下载工具 v3.0 - 简洁版

✨ 主要功能:
• 单篇文章下载 (PDF/HTML/Markdown/JSON)
• 多URL批量下载 (简单直接)
• 完美保持原文格式和图片
• 智能重试和错误处理
• 🆕 智能分类转移到飞书知识库
• 🆕 OAuth认证管理

🔧 技术特点:
• 人类式阅读行为模拟
• 智能图片加载检测
• 高效PDF生成
• 自动文件命名
• 🆕 关键词匹配自动分类

📧 支持: 遇到问题请查看日志输出
        """
        ttk.Label(about_frame, text=about_text.strip(), justify=tk.LEFT).pack(anchor=tk.W)
        
        # 绑定鼠标滚轮事件到Canvas
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        # 绑定滚轮事件到Canvas和scrollable_frame
        canvas.bind("<MouseWheel>", _on_mousewheel)
        scrollable_frame.bind("<MouseWheel>", _on_mousewheel)
        
        # 确保焦点事件也能滚动
        def bind_mousewheel_to_widget(widget):
            widget.bind("<MouseWheel>", _on_mousewheel)
            for child in widget.winfo_children():
                bind_mousewheel_to_widget(child)
        
        bind_mousewheel_to_widget(scrollable_frame)
    
    def create_wiki_location_settings(self, parent, start_row):
        """创建知识库位置配置界面"""
        # 主标题
        wiki_frame = ttk.LabelFrame(parent, text="🎯 知识库智能分类设置", padding="10")
        wiki_frame.grid(row=start_row, column=0, sticky=(tk.W, tk.E), pady=(15, 0))
        parent.columnconfigure(0, weight=1)
        wiki_frame.columnconfigure(0, weight=1)
        
        # 说明文字
        info_text = """
💡 智能分类功能：根据文章标题中的关键词自动转移到对应的知识库位置
• 支持多个关键词匹配同一个位置
• 可以设置转移到页面或子页面
• 未匹配到关键词时转移到默认位置
        """
        ttk.Label(wiki_frame, text=info_text.strip(), justify=tk.LEFT, 
                 foreground='gray').grid(row=0, column=0, sticky=tk.W, pady=(0, 10))
        
        # 默认位置设置
        default_frame = ttk.LabelFrame(wiki_frame, text="🏠 默认转移位置", padding="5")
        default_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        default_frame.columnconfigure(1, weight=1)
        
        # 默认位置URL输入行
        ttk.Label(default_frame, text="默认位置:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.default_wiki_var = tk.StringVar(value=self.default_wiki_location)
        ttk.Entry(default_frame, textvariable=self.default_wiki_var, width=50).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        ttk.Button(default_frame, text="测试", command=lambda: self.test_wiki_url(self.default_wiki_var.get())).grid(row=0, column=2)
        
        # 默认位置子页面选项行
        default_options_frame = ttk.Frame(default_frame)
        default_options_frame.grid(row=1, column=0, columnspan=3, sticky=tk.W, pady=(5, 0))
        
        self.default_as_subpage_var = tk.BooleanVar(value=True)  # 默认勾选
        ttk.Checkbutton(default_options_frame, text="转移到该位置的子页面", 
                       variable=self.default_as_subpage_var).pack(side=tk.LEFT)
        
        # 关键词-位置映射设置
        mapping_frame = ttk.LabelFrame(wiki_frame, text="🔍 关键词位置映射", padding="5")
        mapping_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        mapping_frame.columnconfigure(0, weight=1)
        
        # 创建滚动区域用于位置映射
        self.create_wiki_mappings_area(mapping_frame)
        
        # 操作按钮
        button_frame = ttk.Frame(mapping_frame)
        button_frame.grid(row=1, column=0, pady=(10, 0))
        
        ttk.Button(button_frame, text="➕ 添加位置", command=self.add_wiki_location).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="💾 保存配置", command=self.save_wiki_config).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="🔄 重置配置", command=self.reset_wiki_config).pack(side=tk.LEFT)
        
        # 🆕 智能分类测试区域
        test_frame = ttk.LabelFrame(wiki_frame, text="🧪 智能分类测试", padding="5")
        test_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        test_frame.columnconfigure(1, weight=1)
        
        ttk.Label(test_frame, text="测试标题:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.test_title_var = tk.StringVar(value="Python编程技术入门教程")
        ttk.Entry(test_frame, textvariable=self.test_title_var, width=40).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        ttk.Button(test_frame, text="🧪 测试分类", command=self.run_classification_test).grid(row=0, column=2)
        
        # 测试结果显示
        self.test_result_var = tk.StringVar(value="点击'测试分类'查看结果")
        ttk.Label(test_frame, textvariable=self.test_result_var, foreground='blue').grid(row=1, column=0, columnspan=3, sticky=tk.W, pady=(5, 0))

    def create_wiki_mappings_area(self, parent):
        """创建知识库映射配置区域"""
        # 创建滚动区域
        mappings_canvas = tk.Canvas(parent, height=200)
        mappings_scrollbar = ttk.Scrollbar(parent, orient="vertical", command=mappings_canvas.yview)
        self.mappings_frame = ttk.Frame(mappings_canvas)
        
        self.mappings_frame.bind(
            "<Configure>",
            lambda e: mappings_canvas.configure(scrollregion=mappings_canvas.bbox("all"))
        )
        
        mappings_canvas.create_window((0, 0), window=self.mappings_frame, anchor="nw")
        mappings_canvas.configure(yscrollcommand=mappings_scrollbar.set)
        
        mappings_canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        mappings_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        parent.rowconfigure(0, weight=1)
        parent.columnconfigure(0, weight=1)
        
        # 绑定鼠标滚轮
        def _on_mappings_mousewheel(event):
            mappings_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        mappings_canvas.bind("<MouseWheel>", _on_mappings_mousewheel)
        
        # 创建现有的映射项
        self.refresh_wiki_mappings()

    def refresh_wiki_mappings(self):
        """刷新知识库映射显示"""
        # 清空现有内容
        for widget in self.mappings_frame.winfo_children():
            widget.destroy()
        
        # 添加表头
        header_frame = ttk.Frame(self.mappings_frame)
        header_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(header_frame, text="关键词 (用逗号分隔)", font=('Arial', 9, 'bold')).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Label(header_frame, text="知识库链接", font=('Arial', 9, 'bold')).pack(side=tk.LEFT, padx=(120, 10))
        ttk.Label(header_frame, text="子页面", font=('Arial', 9, 'bold')).pack(side=tk.LEFT, padx=(200, 10))
        ttk.Label(header_frame, text="操作", font=('Arial', 9, 'bold')).pack(side=tk.LEFT, padx=(30, 0))
        
        # 添加现有的映射项
        for i, location in enumerate(self.wiki_locations):
            self.create_wiki_mapping_row(i, location)
        
        # 如果没有映射项，添加一个默认的
        if not self.wiki_locations:
            self.add_wiki_location()

    def create_wiki_mapping_row(self, index, location_data):
        """创建单个知识库映射行"""
        row_frame = ttk.Frame(self.mappings_frame)
        row_frame.pack(fill=tk.X, pady=2)
        
        # 关键词输入框
        keywords_str = ", ".join(location_data.get("keywords", []))
        keywords_var = tk.StringVar(value=keywords_str)
        keywords_entry = ttk.Entry(row_frame, textvariable=keywords_var, width=20)
        keywords_entry.pack(side=tk.LEFT, padx=(0, 10))
        
        # 链接输入框
        url_var = tk.StringVar(value=location_data.get("wiki_url", ""))
        url_entry = ttk.Entry(row_frame, textvariable=url_var, width=40)
        url_entry.pack(side=tk.LEFT, padx=(0, 10))
        
        # 子页面勾选框
        subpage_var = tk.BooleanVar(value=location_data.get("as_subpage", True))
        subpage_check = ttk.Checkbutton(row_frame, variable=subpage_var)
        subpage_check.pack(side=tk.LEFT, padx=(0, 10))
        
        # 测试按钮
        ttk.Button(row_frame, text="测试", width=6,
                  command=lambda: self.test_wiki_url(url_var.get())).pack(side=tk.LEFT, padx=(0, 5))
        
        # 删除按钮
        ttk.Button(row_frame, text="删除", width=6,
                  command=lambda i=index: self.remove_wiki_location(i)).pack(side=tk.LEFT)
        
        # 保存变量引用以便后续获取值
        setattr(row_frame, 'keywords_var', keywords_var)
        setattr(row_frame, 'url_var', url_var)
        setattr(row_frame, 'subpage_var', subpage_var)
        setattr(row_frame, 'index', index)

    def add_wiki_location(self):
        """添加新的知识库位置"""
        new_location = {
            "keywords": [],
            "wiki_url": "",
            "as_subpage": True
        }
        self.wiki_locations.append(new_location)
        self.refresh_wiki_mappings()
        self.log_message("已添加新的知识库位置配置", "INFO")

    def remove_wiki_location(self, index):
        """删除知识库位置"""
        if 0 <= index < len(self.wiki_locations):
            self.wiki_locations.pop(index)
            self.refresh_wiki_mappings()
            self.log_message(f"已删除知识库位置配置 #{index + 1}", "INFO")

    def save_wiki_config(self):
        """保存知识库配置"""
        try:
            # 更新默认位置
            self.default_wiki_location = self.default_wiki_var.get()
            
            # 更新映射配置
            self.wiki_locations.clear()
            
            for widget in self.mappings_frame.winfo_children():
                if hasattr(widget, 'keywords_var'):
                    keywords_str = widget.keywords_var.get().strip()
                    wiki_url = widget.url_var.get().strip()
                    as_subpage = widget.subpage_var.get()
                    
                    if keywords_str and wiki_url:
                        # 解析关键词
                        keywords = [kw.strip() for kw in keywords_str.split(',') if kw.strip()]
                        
                        location_config = {
                            "keywords": keywords,
                            "wiki_url": wiki_url,
                            "as_subpage": as_subpage
                        }
                        self.wiki_locations.append(location_config)
            
            # 保存到配置文件（可选）
            self.save_config_to_file()
            
            self.log_message(f"✅ 知识库配置已保存 ({len(self.wiki_locations)} 个位置)", "SUCCESS")
            
        except Exception as e:
            self.log_message(f"❌ 保存知识库配置失败: {e}", "ERROR")

    def reset_wiki_config(self):
        """重置知识库配置"""
        if messagebox.askyesno("确认重置", "确定要重置知识库配置吗？这将恢复到默认设置。"):
            self.init_default_wiki_config()
            self.default_wiki_var.set(self.default_wiki_location)
            self.refresh_wiki_mappings()
            self.log_message("已重置知识库配置到默认设置", "INFO")

    def test_wiki_url(self, url):
        """测试知识库URL是否有效"""
        if not url:
            messagebox.showwarning("警告", "请输入URL")
            return
        
        # 这里可以添加URL验证逻辑
        # 暂时只做简单的格式检查
        if "feishu.cn" in url:
            messagebox.showinfo("测试结果", "URL格式正确！\n注意：实际有效性需要在使用时验证。")
            self.log_message(f"测试知识库URL: {url}", "INFO")
        else:
            messagebox.showwarning("测试结果", "URL格式可能不正确，请检查是否为飞书链接。")

    def save_config_to_file(self):
        """保存配置到文件"""
        try:
            import json
            config_data = {
                "default_wiki_location": self.default_wiki_location,
                "default_as_subpage": self.default_as_subpage_var.get() if hasattr(self, 'default_as_subpage_var') else True,
                "wiki_locations": self.wiki_locations
            }
            
            with open("wiki_location_config.json", "w", encoding="utf-8") as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
                
            self.log_message("配置已保存到 wiki_location_config.json", "INFO")
            
        except Exception as e:
            self.log_message(f"保存配置文件失败: {e}", "WARNING")

    def load_config_from_file(self):
        """从文件加载配置"""
        try:
            import json
            if os.path.exists("wiki_location_config.json"):
                with open("wiki_location_config.json", "r", encoding="utf-8") as f:
                    config_data = json.load(f)
                
                self.default_wiki_location = config_data.get("default_wiki_location", self.default_wiki_location)
                self.wiki_locations = config_data.get("wiki_locations", self.wiki_locations)
                
                # 加载默认位置的子页面设置
                default_as_subpage = config_data.get("default_as_subpage", True)
                if hasattr(self, 'default_as_subpage_var'):
                    self.default_as_subpage_var.set(default_as_subpage)
                
                self.log_message("从配置文件加载设置成功", "INFO")
                
        except Exception as e:
            self.log_message(f"加载配置文件失败: {e}", "WARNING")

    def find_target_wiki_location(self, title):
        """根据文章标题找到目标知识库分类子节点位置"""
        self.log_message(f"🔍 智能分类分析开始", "INFO")
        self.log_message(f"   📝 分析标题: {title}", "INFO")
        self.log_message(f"   🗂️ 配置的分类位置: {len(self.wiki_locations)} 个", "INFO")
        self.log_message(f"   💡 匹配策略: 关键词匹配 → 分类定位 → 智能上传", "INFO")
        
        title_lower = title.lower()
        
        # 遍历所有配置的位置
        for i, location in enumerate(self.wiki_locations):
            keywords = location.get("keywords", [])
            wiki_url = location.get("wiki_url", "")
            as_subpage = location.get("as_subpage", True)
            
            location_name = wiki_url.split('/')[-1] if '/' in wiki_url else wiki_url
            self.log_message(f"   📂 位置{i+1}: {location_name} (关键词: {keywords})", "INFO")
            
            for keyword in keywords:
                if keyword.lower() in title_lower:
                    self.log_message(f"   🎯 ✅ 匹配成功! 关键词 '{keyword}' 命中", "SUCCESS")
                    self.log_message(f"      📍 目标位置: {location_name}", "SUCCESS")
                    self.log_message(f"      📄 上传方式: {'子页面' if as_subpage else '独立页面'}", "SUCCESS")
                    return location
        
        # 没有匹配到关键词，使用默认位置
        default_as_subpage = self.default_as_subpage_var.get() if hasattr(self, 'default_as_subpage_var') else True
        default_location_name = self.default_wiki_location.split('/')[-1] if '/' in self.default_wiki_location else self.default_wiki_location
        self.log_message(f"   🏠 无关键词匹配，使用默认位置", "INFO")
        self.log_message(f"      📍 默认位置: {default_location_name}", "INFO")
        self.log_message(f"      📄 上传方式: {'子页面' if default_as_subpage else '独立页面'}", "INFO")
        
        # 🔥 确保返回完整的位置信息，包含keywords字段（空列表）
        return {
            "keywords": [],  # 默认位置没有关键词
            "wiki_url": self.default_wiki_location,
            "as_subpage": default_as_subpage
        }

    def init_default_wiki_config(self):
        """初始化默认的知识库配置"""
        # 设置默认转移位置（RO知识库的默认位置）
        self.default_wiki_location = "https://thedream.feishu.cn/wiki/MLOZwjYtBiCepHkpHFPcA2dgnvf"
        
        # 添加完整的RO关键词-链接配置（与wiki_location_config.json保持一致）
        self.wiki_locations = [
            {
                "keywords": ["冒险者指南"],
                "wiki_url": "https://thedream.feishu.cn/wiki/XS8kwk7oJieSv6keDWGc8bGln5g",
                "as_subpage": True
            },
            {
                "keywords": ["热点问题汇总"],
                "wiki_url": "https://thedream.feishu.cn/wiki/CBnawegHoi8rsrkqmINc2jIHnMb",
                "as_subpage": True
            },
            {
                "keywords": ["冒险者投稿"],
                "wiki_url": "https://thedream.feishu.cn/wiki/FlXIwYAkbioxf1kURgXcIZhInl7",
                "as_subpage": True
            },
            {
                "keywords": ["征集"],
                "wiki_url": "https://thedream.feishu.cn/wiki/YIK6wvyxuiER1MkWDUjcv1WfnQb",
                "as_subpage": True
            },
            {
                "keywords": ["南门茶话会"],
                "wiki_url": "https://thedream.feishu.cn/wiki/B3sUwGL9oiD6oNkTzzkcMm4fnKd",
                "as_subpage": True
            },
            {
                "keywords": ["波利观光团"],
                "wiki_url": "https://thedream.feishu.cn/wiki/AFsRw5o52i3NLdkGl0FcFBa3nIU",
                "as_subpage": True
            },
            {
                "keywords": ["更新公告"],
                "wiki_url": "https://thedream.feishu.cn/wiki/K1iVwfcrois7UHkY32Icurxtnuf",
                "as_subpage": True
            },
            {
                "keywords": ["壁纸派送"],
                "wiki_url": "https://thedream.feishu.cn/wiki/XIgpwJVGOiuCtFkHq2zcfipjn4q",
                "as_subpage": True
            },
            {
                "keywords": ["福利"],
                "wiki_url": "https://thedream.feishu.cn/wiki/NwtlwO1SHiUyzgkMU5Rc57i6nYc",
                "as_subpage": True
            },
            {
                "keywords": ["彩虹路透社"],
                "wiki_url": "https://thedream.feishu.cn/wiki/B3sUwGL9oiD6oNkTzzkcMm4fnKd",
                "as_subpage": True
            },
            {
                "keywords": ["卡普拉独家"],
                "wiki_url": "https://thedream.feishu.cn/wiki/WVPnwjiZiiGhpYkUCSWc01NFnOd",
                "as_subpage": True
            },
            {
                "keywords": ["有礼"],
                "wiki_url": "https://thedream.feishu.cn/wiki/W2Qsw8R8aiZrMQkQlSZcr8gmnhe",
                "as_subpage": True
            },
            {
                "keywords": ["冒险日历"],
                "wiki_url": "https://thedream.feishu.cn/wiki/QvkMwNvZHiKX7xkWkD4cDxMdntc",
                "as_subpage": True
            }
        ]
        
        # 尝试从配置文件加载（会覆盖上面的默认设置）
        self.load_config_from_file()
        
        self.log_message(f"📂 智能分类配置初始化完成", "INFO")
        self.log_message(f"🏠 默认位置: {self.default_wiki_location}", "INFO")
        self.log_message(f"🗂️ 关键词位置数量: {len(self.wiki_locations)}", "INFO")
        
        # 显示所有配置的关键词（调试用）
        for i, location in enumerate(self.wiki_locations, 1):
            keywords = location.get("keywords", [])
            wiki_url = location.get("wiki_url", "")
            self.log_message(f"   📋 [{i}] 关键词: {keywords} → {wiki_url.split('/')[-1]}", "INFO")
    
    def log_message(self, message, level="INFO"):
        """添加日志消息到队列"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {level}: {message}\n"
        self.msg_queue.put(('log', formatted_message))
    
    def process_queue(self):
        """处理消息队列"""
        try:
            while True:
                msg_type, data = self.msg_queue.get_nowait()
                if msg_type == 'log':
                    self.log_text.config(state='normal')
                    self.log_text.insert(tk.END, data)
                    self.log_text.see(tk.END)
                    self.log_text.config(state='disabled')
                elif msg_type == 'status':
                    self.status_var.set(data)
                elif msg_type == 'progress_single':
                    self.single_progress_var.set(data)
                elif msg_type == 'progress_batch':
                    self.batch_progress_var.set(data)
                elif msg_type == 'stats_batch':
                    self.batch_stats_var.set(data)
                elif msg_type == 'enable_buttons':
                    self.enable_buttons()
                elif msg_type == 'disable_buttons':
                    self.disable_buttons()
                elif msg_type == 'oauth_success':
                    self.handle_oauth_result(True)
                elif msg_type == 'oauth_failed':
                    self.handle_oauth_result(False)
        except queue.Empty:
            pass
        
        # 每100ms检查一次队列
        self.root.after(100, self.process_queue)
    
    def enable_buttons(self):
        """启用按钮"""
        self.single_download_btn.config(state='normal')
        self.batch_download_btn.config(state='normal')
        self.is_downloading = False
    
    def disable_buttons(self):
        """禁用按钮"""
        self.single_download_btn.config(state='disabled')
        self.batch_download_btn.config(state='disabled')
        self.is_downloading = True
    
    def clear_log(self):
        """清空日志"""
        self.log_text.config(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state='disabled')
    
    def browse_output_dir(self):
        """浏览输出目录"""
        directory = filedialog.askdirectory(initialdir=self.output_dir)
        if directory:
            self.output_dir = directory
            self.output_dir_var.set(directory)
    
    def open_output_dir(self):
        """打开输出目录"""
        if os.path.exists(self.output_dir):
            if sys.platform == "win32":
                os.startfile(self.output_dir)
            elif sys.platform == "darwin":
                os.system(f"open '{self.output_dir}'")
            else:
                os.system(f"xdg-open '{self.output_dir}'")
        else:
            messagebox.showwarning("警告", f"输出目录不存在: {self.output_dir}")
    
    def open_pdf_download_dir(self):
        """打开PDF下载目录"""
        pdf_dir = os.path.join(self.output_dir, "pdf")
        
        # 确保目录存在
        os.makedirs(pdf_dir, exist_ok=True)
        
        if sys.platform == "win32":
            os.startfile(pdf_dir)
        elif sys.platform == "darwin":
            os.system(f"open '{pdf_dir}'")
        else:
            os.system(f"xdg-open '{pdf_dir}'")
        
        self.log_message(f"已打开PDF下载目录: {pdf_dir}")
    
    def update_auto_format(self):
        """更新自动下载格式"""
        self.auto_download_format = self.auto_format_var.get()
        format_name = "PDF" if self.auto_download_format == "pdf" else "Word文档"
        self.log_message(f"🎯 自动下载格式已切换为: {format_name}", "INFO")
    
    def clear_batch_urls(self):
        """清空批量URL文本框"""
        self.batch_urls_text.delete(1.0, tk.END)
    
    def paste_from_clipboard(self):
        """从剪贴板粘贴URL"""
        try:
            clipboard_content = self.root.clipboard_get()
            self.batch_urls_text.insert(tk.END, "\n" + clipboard_content)
            self.log_message("已从剪贴板粘贴内容")
        except tk.TclError:
            messagebox.showwarning("警告", "剪贴板为空或无法访问")
    
    def load_urls_from_file(self):
        """从文件加载URL"""
        file_path = filedialog.askopenfilename(
            title="选择URL文件",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.batch_urls_text.insert(tk.END, "\n" + content)
                self.log_message(f"已从文件加载URL: {file_path}")
            except Exception as e:
                messagebox.showerror("错误", f"读取文件失败: {e}")
    
    def start_single_download(self):
        """开始单篇下载"""
        url = self.single_url_var.get().strip()
        if not url:
            messagebox.showerror("错误", "请输入微信文章URL")
            return
        
        if self.is_downloading:
            messagebox.showwarning("警告", "正在下载中，请等待完成")
            return
        
        # 在新线程中执行下载
        thread = threading.Thread(target=self._single_download_worker, args=(url,))
        thread.daemon = True
        thread.start()
    
    def start_batch_download(self):
        """开始批量下载"""
        urls_text = self.batch_urls_text.get(1.0, tk.END).strip()
        if not urls_text:
            messagebox.showerror("错误", "请输入微信文章URL列表")
            return
        
        if self.is_downloading:
            messagebox.showwarning("警告", "正在下载中，请等待完成")
            return
        
        # 解析URL列表
        urls = [url.strip() for url in urls_text.split('\n') if url.strip()]
        if not urls:
            messagebox.showerror("错误", "没有找到有效的URL")
            return
        
        # 确认下载
        result = messagebox.askyesno("确认批量下载", 
                                   f"将要下载 {len(urls)} 篇文章\n\n"
                                   f"预计耗时: {len(urls) * int(self.delay_var.get())} 秒\n\n"
                                   f"确定要开始批量下载吗？")
        if not result:
            return
        
        # 在新线程中执行批量下载
        thread = threading.Thread(target=self._batch_download_worker, args=(urls,))
        thread.daemon = True
        thread.start()
    
    def _single_download_worker(self, url):
        """单篇下载工作线程"""
        try:
            self.msg_queue.put(('disable_buttons', None))
            self.msg_queue.put(('status', '正在下载...'))
            self.msg_queue.put(('progress_single', '初始化中...'))
            
            # 🆕 优化：异步初始化scraper，只在首次使用时初始化
            if not self.url_scraper and not self.scraper_initializing:
                self.scraper_initializing = True
                self.msg_queue.put(('progress_single', '首次使用，正在初始化浏览器...'))
                self.log_message("🔧 首次使用，正在初始化浏览器...", "INFO")
                self.url_scraper = SimpleUrlScraper(headless=self.headless_var.get())
                self.scraper_initializing = False
                self.log_message("✅ 浏览器初始化完成", "SUCCESS")
            
            format_type = self.single_format_var.get()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            self.log_message(f"开始下载文章: {url}")
            self.log_message(f"输出格式: {format_type}")
            
            # 首先获取文章信息提取标题
            self.msg_queue.put(('progress_single', '获取文章信息...'))
            article_info = self.url_scraper.extract_article_info(url)
            
            # 生成文件名
            if article_info and 'error' not in article_info and article_info.get('title'):
                title = article_info['title']
                safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)[:80]
                if not safe_title.strip():
                    safe_title = f"article_{timestamp}"
                self.log_message(f"文章标题: {title}")
            else:
                safe_title = f"article_{timestamp}"
                self.log_message("未能获取文章标题，使用默认文件名")
            
            # 根据格式下载
            success = False
            output_path = ""
            
            if format_type == "pdf":
                self.msg_queue.put(('progress_single', '生成PDF中...'))
                pdf_filename = f"{safe_title}.pdf"
                output_path = os.path.join(self.output_dir, "pdf", pdf_filename)
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                success = self.url_scraper.save_as_pdf(url, output_path)
                
            elif format_type == "docx":
                self.msg_queue.put(('progress_single', '生成Word文档中...'))
                docx_filename = f"{safe_title}.docx"
                output_path = os.path.join(self.output_dir, "docx", docx_filename)
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                success = self.url_scraper.save_as_docx(url, output_path)

            elif format_type == "complete_html":
                self.msg_queue.put(('progress_single', '生成完整HTML中...'))
                html_filename = f"{safe_title}.html"
                output_path = os.path.join(self.output_dir, "complete_html", html_filename)
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                success = self.url_scraper.save_complete_html(url, output_path)
                
            else:
                # 其他格式暂时标记为成功
                self.msg_queue.put(('progress_single', f'生成{format_type}格式中...'))
                success = True
                output_path = f"{self.output_dir}/{format_type}/{safe_title}"
            
            if success:
                self.log_message("✅ 下载成功!", "SUCCESS")
                self.msg_queue.put(('progress_single', f'✅ 下载成功: {os.path.basename(output_path)}'))
                self.msg_queue.put(('status', '下载完成'))
                
                # 自动上传到飞书知识库
                if self.enable_feishu_upload and format_type in ["pdf", "docx"]:
                    self.upload_to_feishu(output_path)
            else:
                self.log_message("❌ 下载失败", "ERROR")
                self.msg_queue.put(('progress_single', '❌ 下载失败'))
                self.msg_queue.put(('status', '下载失败'))
                
        except Exception as e:
            self.log_message(f"下载过程中出现错误: {e}", "ERROR")
            self.msg_queue.put(('progress_single', '❌ 下载出错'))
            self.msg_queue.put(('status', '下载出错'))
        finally:
            self.msg_queue.put(('enable_buttons', None))
    
    def _batch_download_worker(self, urls):
        """批量下载工作线程"""
        try:
            self.msg_queue.put(('disable_buttons', None))
            self.msg_queue.put(('status', '批量下载中...'))
            self.msg_queue.put(('progress_batch', '准备批量下载...'))
            
            # 🆕 优化：异步初始化scraper，只在首次使用时初始化
            if not self.url_scraper and not self.scraper_initializing:
                self.scraper_initializing = True
                self.msg_queue.put(('progress_batch', '首次使用，正在初始化浏览器...'))
                self.log_message("🔧 首次使用，正在初始化浏览器...", "INFO")
                self.url_scraper = SimpleUrlScraper(headless=self.headless_var.get())
                self.scraper_initializing = False
                self.log_message("✅ 浏览器初始化完成", "SUCCESS")
            
            # 统计变量
            total_urls = len(urls)
            success_count = 0
            failed_count = 0
            delay_seconds = int(self.delay_var.get())
            max_retries = int(self.retry_var.get())
            
            # 🆕 获取批量下载格式设置（使用自动下载格式设置）
            format_type = self.auto_format_var.get()
            
            self.log_message(f"开始批量下载 {total_urls} 篇文章")
            self.log_message(f"下载格式: {format_type.upper()}")
            self.log_message(f"下载延迟: {delay_seconds} 秒，重试次数: {max_retries}")
            
            # 检查飞书上传设置
            if self.batch_feishu_upload_var.get():
                self.log_message("📚 已启用批量下载后自动上传到飞书知识库", "INFO")
            else:
                self.log_message("📁 仅下载文件，不上传到飞书知识库", "INFO")
            
            # 过滤和验证URL
            valid_urls = []
            for i, url in enumerate(urls):
                if self._is_valid_wechat_url(url):
                    valid_urls.append(url)
                else:
                    self.log_message(f"跳过无效URL: {url}", "WARNING")
                    failed_count += 1
            
            self.log_message(f"有效URL: {len(valid_urls)} 个，无效URL: {failed_count} 个")
            
            # 开始下载有效URL
            for i, url in enumerate(valid_urls):
                try:
                    current_progress = f"下载进度: {i+1}/{len(valid_urls)}"
                    self.msg_queue.put(('progress_batch', current_progress))
                    
                    stats = f"成功: {success_count} | 失败: {failed_count} | 剩余: {len(valid_urls) - i - 1}"
                    self.msg_queue.put(('stats_batch', stats))
                    
                    self.log_message(f"[{i+1}/{len(valid_urls)}] 开始下载: {url}")
                    
                    # 尝试下载
                    download_success = False
                    for attempt in range(max_retries + 1):
                        try:
                            if attempt > 0:
                                self.log_message(f"重试第 {attempt} 次...")
                            
                            # 获取文章信息
                            article_info = self.url_scraper.extract_article_info(url)
                            if not article_info or 'error' in article_info:
                                raise Exception("无法获取文章信息")
                            
                            # 生成文件名
                            title = article_info.get('title', f'article_{i+1}')
                            safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)[:80]
                            if not safe_title.strip():
                                safe_title = f"article_{i+1}_{datetime.now().strftime('%H%M%S')}"
                            
                            # 🆕 根据格式类型下载文件
                            if format_type == "pdf":
                                file_extension = ".pdf"
                                filename = f"{safe_title}{file_extension}"
                                output_path = os.path.join(self.output_dir, "batch_download", filename)
                                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                                
                                # 处理文件名冲突
                                counter = 1
                                while os.path.exists(output_path):
                                    filename = f"{safe_title}_{counter}{file_extension}"
                                    output_path = os.path.join(self.output_dir, "batch_download", filename)
                                    counter += 1
                                
                                download_success = self.url_scraper.save_as_pdf(url, output_path)
                                
                            elif format_type == "docx":
                                file_extension = ".docx"
                                filename = f"{safe_title}{file_extension}"
                                output_path = os.path.join(self.output_dir, "batch_download", filename)
                                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                                
                                # 处理文件名冲突
                                counter = 1
                                while os.path.exists(output_path):
                                    filename = f"{safe_title}_{counter}{file_extension}"
                                    output_path = os.path.join(self.output_dir, "batch_download", filename)
                                    counter += 1
                                
                                download_success = self.url_scraper.save_as_docx(url, output_path)
                                
                            else:
                                raise Exception(f"不支持的格式: {format_type}")
                            
                            if download_success:
                                self.log_message(f"✅ 下载成功: {title}", "SUCCESS")
                                
                                # 检查是否需要自动上传到飞书知识库
                                if self.batch_feishu_upload_var.get():
                                    self.log_message(f"📚 开始批量上传到飞书知识库: {os.path.basename(output_path)}", "INFO")
                                    upload_success = self._upload_to_feishu_batch(output_path)
                                    if upload_success:
                                        self.log_message(f"✅ 批量飞书上传成功: {title}", "SUCCESS")
                                    else:
                                        self.log_message(f"❌ 批量飞书上传失败: {title}", "WARNING")
                                
                                break
                            else:
                                raise Exception(f"{format_type.upper()}生成失败")
                                
                        except Exception as e:
                            self.log_message(f"下载失败 (尝试 {attempt + 1}): {e}", "WARNING")
                            if attempt < max_retries:
                                import time
                                time.sleep(2)  # 重试前等待2秒
                    
                    if download_success:
                        success_count += 1
                    else:
                        failed_count += 1
                        self.log_message(f"❌ 彻底失败: {url}", "ERROR")
                    
                    # 延迟处理（除了最后一个）
                    if i < len(valid_urls) - 1:
                        self.log_message(f"等待 {delay_seconds} 秒后下载下一篇...")
                        import time
                        time.sleep(delay_seconds)
                        
                except Exception as e:
                    failed_count += 1
                    self.log_message(f"处理URL时出错: {e}", "ERROR")
                    continue
            
            # 完成统计
            final_stats = f"批量下载完成！成功: {success_count} | 失败: {failed_count} | 总计: {total_urls}"
            self.msg_queue.put(('stats_batch', final_stats))
            
            if self.batch_feishu_upload_var.get():
                self.msg_queue.put(('progress_batch', '✅ 批量下载和上传完成'))
                self.msg_queue.put(('status', '批量下载和上传完成'))
                self.log_message("🎉 批量下载和飞书上传任务完成！", "SUCCESS")
            else:
                self.msg_queue.put(('progress_batch', '✅ 批量下载完成'))
                self.msg_queue.put(('status', '批量下载完成'))
                self.log_message("🎉 批量下载任务完成！", "SUCCESS")
            
            self.log_message(final_stats, "INFO")
                
        except Exception as e:
            self.log_message(f"批量下载过程中出现严重错误: {e}", "ERROR")
            self.msg_queue.put(('progress_batch', '❌ 批量下载出错'))
            self.msg_queue.put(('status', '批量下载出错'))
        finally:
            self.msg_queue.put(('enable_buttons', None))
    
    def _is_valid_wechat_url(self, url):
        """检查是否是有效的微信文章URL"""
        if not url or not url.startswith('http'):
            return False
        
        # 检查是否包含微信公众号域名
        return 'mp.weixin.qq.com/s' in url
    
    def toggle_auto_download(self):
        """切换自动下载模式状态"""
        if self.is_auto_collecting:
            self.stop_auto_download()
        else:
            self.start_auto_download()
    
    def start_auto_download(self):
        """开始自动下载模式"""
        self.log_message("🚀 正在启动自动下载模式...", "INFO")
        
        self.is_auto_collecting = True
        self.auto_download_btn.config(text="⏹️ 停止自动下载")
        self.auto_download_status.set("🚀 监控中...")
        self.log_message("🚀 自动下载模式已启动！复制微信文章链接即可自动下载PDF", "SUCCESS")
        
        # 清空统计和状态
        self.collected_urls.clear()
        self.queue_stats = {"completed": 0, "failed": 0, "total": 0}
        self.log_message("🧹 已清空统计数据", "INFO")
        
        # 🆕 启动时不初始化浏览器，大大加快启动速度
        # 浏览器将在首次下载时才初始化，避免启动卡顿
        self.log_message("⚡ 快速启动模式：浏览器将在首次使用时初始化", "INFO")
        self.log_message("🔧 注意：整合版上传器有独立的下载器，不会影响浏览器启动速度", "INFO")
        
        # 初始化飞书集成
        if self.enable_feishu_upload:
            self.log_message("🔧 正在初始化飞书集成...", "INFO")
            self.log_message("✅ 飞书集成已启用 (使用整合版上传器)", "SUCCESS")
        
        # 获取当前文本框中的URL用于初始化去重集合
        current_content = self.batch_urls_text.get("1.0", tk.END).strip()
        if current_content and not "https://mp.weixin.qq.com/s?__biz=xxx" in current_content:
            self.log_message("📄 处理现有文本框中的URL...", "INFO")
            count = 0
            for line in current_content.split('\n'):
                line = line.strip()
                if line and self._is_valid_wechat_url(line):
                    self.collected_urls.add(line)
                    count += 1
            self.log_message(f"📝 从文本框加载了 {count} 个已有URL", "INFO")
        
        # 开始队列处理
        if not self.is_queue_processing:
            self.log_message("📥 启动下载队列处理器...", "INFO")
            self.start_queue_processor()
        
        # 获取初始剪贴板内容
        try:
            self.last_clipboard_content = self.root.clipboard_get()
            self.log_message(f"📋 获取初始剪贴板内容: {self.last_clipboard_content[:30]}...", "INFO")
        except:
            self.last_clipboard_content = ""
            self.log_message("📋 初始剪贴板为空", "INFO")
        
        # 开始监控剪贴板
        self.log_message("👀 开始监控剪贴板变化 (每500ms检查一次)", "INFO")
        self.check_clipboard()
    
    def stop_auto_download(self):
        """停止自动下载模式"""
        self.is_auto_collecting = False
        self.is_queue_processing = False
        self.auto_download_btn.config(text="🚀 开启自动下载模式")
        self.auto_download_status.set("")
        self.log_message("自动下载模式已停止", "INFO")
    
    def check_clipboard(self):
        """检查剪贴板内容（修复版）"""
        if not self.is_auto_collecting:
            return
        
        try:
            # 获取剪贴板内容
            clipboard_content = self.root.clipboard_get()
            
            # 检查内容是否变化且不为空
            if (clipboard_content != self.last_clipboard_content and 
                clipboard_content.strip() and 
                len(clipboard_content.strip()) > 10):  # 避免处理很短的内容
                
                self.last_clipboard_content = clipboard_content
                
                # 去除前后空白字符
                cleaned_url = clipboard_content.strip()
                
                # 记录检测到的变化
                self.log_message(f"📋 检测到剪贴板变化: {cleaned_url[:50]}...", "INFO")
                
                # 检查是否是微信文章链接
                if self._is_valid_wechat_url(cleaned_url):
                    self.log_message(f"✅ 检测到微信文章链接!", "SUCCESS")
                    # 使用整合版处理
                    self._process_url_with_integrated_uploader(cleaned_url)
                else:
                    self.log_message(f"❌ 不是微信文章链接: {cleaned_url[:30]}...", "WARNING")
                    
        except tk.TclError:
            # 剪贴板为空或无法访问，这是正常的
            pass
        except Exception as e:
            self.log_message(f"检查剪贴板时出错: {e}", "ERROR")
        
        # 继续监控（每500毫秒检查一次）
        if self.is_auto_collecting:
            self.root.after(500, self.check_clipboard)
    
    def add_url_and_download(self, url):
        """将URL添加到下载队列并开始下载"""
        url = url.strip()
        
        self.log_message(f"🔄 处理URL: {url[:50]}...", "INFO")
        
        # 检查是否重复
        if url in self.collected_urls:
            self.log_message(f"链接重复，跳过: {url[:50]}...", "WARNING")
            return
        
        # 添加到去重集合
        self.collected_urls.add(url)
        self.log_message(f"📝 已添加到去重集合 (当前 {len(self.collected_urls)} 个)", "INFO")
        
        # 添加到下载队列
        self.download_queue.put(url)
        self.queue_stats["total"] += 1
        self.log_message(f"📥 已添加到下载队列 (队列大小: {self.download_queue.qsize()})", "INFO")
        
        # 添加到文本框显示
        current_content = self.batch_urls_text.get("1.0", tk.END).strip()
        
        # 如果文本框为空或只有示例内容，则清空后添加
        if not current_content or "https://mp.weixin.qq.com/s?__biz=xxx" in current_content:
            self.log_message("📄 清空文本框并添加新URL", "INFO")
            self.batch_urls_text.delete("1.0", tk.END)
            self.batch_urls_text.insert(tk.END, url)
        else:
            # 在末尾添加新行和URL
            self.log_message("📄 在文本框末尾添加新URL", "INFO")
            self.batch_urls_text.insert(tk.END, f"\n{url}")
        
        # 滚动到底部
        self.batch_urls_text.see(tk.END)
        
        # 记录日志
        self.log_message(f"🎯 已添加到下载队列: {url[:50]}...", "SUCCESS")
        
        # 更新状态
        queue_size = self.download_queue.qsize()
        status_msg = f"队列中: {queue_size} 个"
        self.update_download_status(status_msg)
        self.log_message(f"📊 更新状态: {status_msg}", "INFO")
    
    def clean_duplicate_urls(self):
        """清理文本框中的重复URL"""
        current_content = self.batch_urls_text.get("1.0", tk.END).strip()
        if not current_content:
            return
        
        # 分割成行并去重
        lines = current_content.split('\n')
        unique_urls = []
        seen_urls = set()
        
        for line in lines:
            line = line.strip()
            if line and self._is_valid_wechat_url(line):
                if line not in seen_urls:
                    unique_urls.append(line)
                    seen_urls.add(line)
        
        # 更新文本框
        self.batch_urls_text.delete("1.0", tk.END)
        self.batch_urls_text.insert(tk.END, '\n'.join(unique_urls))
        
        # 更新去重集合
        self.collected_urls = seen_urls.copy()
        
        removed_count = len(lines) - len(unique_urls)
        if removed_count > 0:
            self.log_message(f"清理完成，删除了 {removed_count} 个重复链接", "INFO")
    
    def start_queue_processor(self):
        """启动队列处理器"""
        self.is_queue_processing = True
        threading.Thread(target=self._queue_processor_worker, daemon=True).start()
        self.log_message("📥 下载队列处理器已启动", "INFO")
    
    def _queue_processor_worker(self):
        """队列处理工作线程"""
        while self.is_queue_processing:
            try:
                # 从队列获取URL（超时1秒）
                url = self.download_queue.get(timeout=1)
                
                if not self.is_queue_processing:
                    break
                
                # 开始下载
                self.current_downloading_url = url
                self._download_single_url(url)
                
                # 标记任务完成
                self.download_queue.task_done()
                self.current_downloading_url = None
                
            except queue.Empty:
                continue
            except Exception as e:
                self.log_message(f"队列处理出错: {e}", "ERROR")
        
        self.log_message("📥 下载队列处理器已停止", "INFO")
    
    def _download_single_url(self, url):
        """下载单个URL - 支持PDF和Word格式"""
        try:
            format_name = "PDF" if self.auto_download_format == "pdf" else "Word文档"
            self.log_message(f"🚀 开始下载{format_name}: {url[:50]}...", "INFO")
            self.update_download_status(f"⬇️ 下载{format_name}中...")
            
            # 🆕 优化：懒加载初始化scraper，只在真正需要时初始化
            if not self.url_scraper and not self.scraper_initializing:
                self.scraper_initializing = True
                self.log_message("🔧 正在初始化URL scraper（首次使用）...", "INFO")
                self.url_scraper = SimpleUrlScraper(headless=self.headless_var.get())
                self.scraper_initializing = False
                self.log_message("✅ URL scraper初始化完成", "SUCCESS")
            
            # 获取文章信息
            article_info = self.url_scraper.extract_article_info(url)
            if not article_info or 'error' in article_info:
                raise Exception("无法获取文章信息")
            
            # 生成文件名（基于文章标题）
            title = article_info.get('title', 'unknown_article')
            safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)[:80]
            if not safe_title.strip():
                safe_title = f"article_{datetime.now().strftime('%H%M%S')}"
            
            # 根据格式生成文件扩展名
            file_ext = ".pdf" if self.auto_download_format == "pdf" else ".docx"
            filename = f"{safe_title}{file_ext}"
            output_path = os.path.join(self.output_dir, "auto_download", filename)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # 处理文件名冲突
            counter = 1
            original_path = output_path
            while os.path.exists(output_path):
                name_without_ext = safe_title
                filename = f"{name_without_ext}_{counter}{file_ext}"
                output_path = os.path.join(self.output_dir, "auto_download", filename)
                counter += 1
            
            # 根据格式下载文件
            success = False
            if self.auto_download_format == "pdf":
                success = self.url_scraper.save_as_pdf(url, output_path)
            elif self.auto_download_format == "docx":
                success = self.url_scraper.save_as_docx(url, output_path)
            
            if success:
                self.queue_stats["completed"] += 1
                self.log_message(f"✅ {format_name}下载成功: {title}", "SUCCESS")
                self.log_message(f"📁 文件保存: {filename}", "INFO")
                
                # 自动上传到飞书知识库
                if self.enable_feishu_upload:
                    self.upload_to_feishu(output_path)
            else:
                raise Exception(f"{format_name}生成失败")
                
        except Exception as e:
            self.queue_stats["failed"] += 1
            self.log_message(f"❌ {format_name}下载失败: {e}", "ERROR")
        
        finally:
            # 更新状态
            self._update_queue_stats()
    
    def _update_queue_stats(self):
        """更新队列统计信息"""
        completed = self.queue_stats["completed"]
        failed = self.queue_stats["failed"]
        total = self.queue_stats["total"]
        queue_size = self.download_queue.qsize()
        
        if queue_size > 0:
            status = f"⬇️ 队列: {queue_size} | 完成: {completed} | 失败: {failed}"
        elif total > 0:
            status = f"✅ 全部完成 | 成功: {completed} | 失败: {failed} | 总计: {total}"
        else:
            status = "🚀 就绪"
        
        self.update_download_status(status)
    
    def update_download_status(self, status):
        """更新下载状态显示"""
        if hasattr(self, 'auto_download_status'):
            self.auto_download_status.set(status)
    
    def toggle_feishu_upload(self):
        """切换飞书上传功能"""
        self.enable_feishu_upload = self.feishu_upload_var.get()
        
        if self.enable_feishu_upload:
            # 使用整合版配置
            self.feishu_status_var.set("✅ 整合版上传器已启用")
            self.log_message("✅ 飞书完整功能已启用（整合版上传器）", "SUCCESS")
        else:
            self.feishu_status_var.set("❌ 飞书集成已禁用")
            self.log_message("飞书知识库集成已禁用", "INFO")

    def check_oauth_status(self):
        """检查OAuth认证状态"""
        try:
            from feishu_oauth_client import FeishuOAuth2Client
            
            oauth_client = FeishuOAuth2Client(self.feishu_app_id, self.feishu_app_secret)
            
            # 检查是否有有效的token
            if oauth_client.load_tokens():
                access_token = oauth_client.get_valid_access_token()
                if access_token:
                    self.oauth_status_var.set("✅ OAuth认证正常，token有效")
                    self.oauth_status_label.config(foreground='green')
                    self.log_message("OAuth认证状态：正常", "SUCCESS")
                else:
                    self.oauth_status_var.set("⚠️  OAuth token已过期，需要重新认证")
                    self.oauth_status_label.config(foreground='orange')
                    self.log_message("OAuth认证状态：token已过期", "WARNING")
            else:
                self.oauth_status_var.set("❌ 未找到OAuth认证信息，需要进行首次认证")
                self.oauth_status_label.config(foreground='red')
                self.log_message("OAuth认证状态：未认证", "WARNING")
                
        except Exception as e:
            self.oauth_status_var.set(f"❌ OAuth状态检查失败: {e}")
            self.oauth_status_label.config(foreground='red')
            self.log_message(f"OAuth状态检查失败: {e}", "ERROR")

    def start_oauth_reauth(self):
        """启动OAuth重新认证流程"""
        try:
            self.log_message("🔄 开始OAuth重新认证流程...", "INFO")
            self.oauth_reauth_btn.config(state='disabled', text="认证中...")
            
            # 在新线程中执行认证，避免阻塞UI
            def oauth_thread():
                try:
                    from feishu_oauth_client import FeishuOAuth2Client
                    
                    oauth_client = FeishuOAuth2Client(self.feishu_app_id, self.feishu_app_secret)
                    
                    # 启动OAuth流程
                    success = oauth_client.start_oauth_flow()
                    
                    if success:
                        self.msg_queue.put(('log', "[SUCCESS] 🎉 OAuth重新认证成功！\n"))
                        self.msg_queue.put(('oauth_success', None))
                    else:
                        self.msg_queue.put(('log', "[ERROR] ❌ OAuth重新认证失败\n"))
                        self.msg_queue.put(('oauth_failed', None))
                        
                except Exception as e:
                    self.msg_queue.put(('log', f"[ERROR] OAuth认证异常: {e}\n"))
                    self.msg_queue.put(('oauth_failed', None))
            
            import threading
            thread = threading.Thread(target=oauth_thread, daemon=True)
            thread.start()
            
            # 提示用户
            messagebox.showinfo("OAuth认证", 
                              "将打开浏览器进行OAuth认证\n\n"
                              "请在浏览器中完成授权流程\n"
                              "认证完成后会自动返回程序")
            
        except Exception as e:
            self.log_message(f"启动OAuth认证失败: {e}", "ERROR")
            self.oauth_reauth_btn.config(state='normal', text="🔄 重新认证")

    def revoke_oauth_tokens(self):
        """撤销OAuth认证"""
        try:
            if messagebox.askyesno("确认撤销", "确定要撤销OAuth认证吗？\n这将删除所有认证信息。"):
                from feishu_oauth_client import FeishuOAuth2Client
                
                oauth_client = FeishuOAuth2Client(self.feishu_app_id, self.feishu_app_secret)
                oauth_client.revoke_tokens()
                
                self.log_message("🗑️  OAuth认证已撤销", "INFO")
                self.check_oauth_status()  # 更新状态显示
                
        except Exception as e:
            self.log_message(f"撤销OAuth认证失败: {e}", "ERROR")

    def handle_oauth_result(self, success: bool):
        """处理OAuth认证结果"""
        if success:
            self.oauth_status_var.set("✅ OAuth重新认证成功！")
            self.oauth_status_label.config(foreground='green')
        else:
            self.oauth_status_var.set("❌ OAuth重新认证失败")
            self.oauth_status_label.config(foreground='red')
        
        self.oauth_reauth_btn.config(state='normal', text="🔄 重新认证")
        
        # 重新检查状态
        self.root.after(2000, self.check_oauth_status)
    
    
    
    def _process_url_with_integrated_uploader(self, url: str):
        """使用整合版上传器处理URL - 支持智能分类和智能重复检测"""
        try:
            from pathlib import Path
            from integrated_auto_download_uploader import IntegratedAutoUploader
            
            self.log_message(f"🚀 使用整合版处理器处理URL: {url[:50]}...", "INFO")
            
            # 检查是否重复
            if url in self.collected_urls:
                self.log_message(f"📋 链接重复，跳过: {url[:50]}...", "WARNING")
                return
            
            # 添加到去重集合和界面
            self.collected_urls.add(url)
            self.add_url_and_download(url)
            
            # 在后台线程中处理，避免阻塞UI
            def background_process():
                try:
                    # 🔥 使用GUI的智能分类处理流程
                    self.log_message(f"🚀 开始智能分类处理流程", "INFO")
                    
                    # 步骤1: 使用整合版下载文件
                    uploader = IntegratedAutoUploader(self.feishu_app_id, self.feishu_app_secret)
                    temp_file_path = uploader.download_article(url, self.auto_download_format)
                    
                    if not temp_file_path:
                        self.log_message(f"❌ 文件下载失败: {url[:50]}...", "ERROR")
                        self.queue_stats["failed"] += 1
                        return
                    
                    filename = temp_file_path.name
                    title = temp_file_path.stem
                    
                    self.log_message(f"✅ 文件下载成功: {filename}", "SUCCESS")
                    self.log_message(f"📝 提取的文件标题: {title}", "INFO")
                    
                    # 步骤2: 使用GUI的智能分类功能
                    self.log_message(f"🧠 执行智能分类分析...", "INFO")
                    target_location = self.find_target_wiki_location(title)
                    target_url = target_location.get("wiki_url", self.default_wiki_location)
                    as_subpage = target_location.get("as_subpage", True)
                    
                    self.log_message(f"🎯 智能分类结果: {target_url[:50]}...", "INFO")
                    self.log_message(f"📄 作为子页面: {'是' if as_subpage else '否'}", "INFO")
                    
                    # 步骤3: 智能重复检测 - 在目标位置检查重复
                    self.log_message(f"🔍 在目标分类位置检查重复...", "INFO")
                    
                    # 提取目标位置的wiki_token
                    target_wiki_token = None
                    if "wiki/" in target_url:
                        if "?" in target_url:
                            clean_url = target_url.split("?")[0]
                        else:
                            clean_url = target_url
                        
                        if "/wiki/space/" in clean_url:
                            target_wiki_token = clean_url.split("/wiki/space/")[-1]
                        elif "/wiki/" in clean_url:
                            target_wiki_token = clean_url.split("/wiki/")[-1]
                    
                    self.log_message(f"📋 目标wiki_token: {target_wiki_token}", "INFO")
                    
                    # 在目标分类子节点下检查重复文章
                    if target_wiki_token:
                        self.log_message(f"📂 在分类子节点下检查重复: {target_wiki_token}", "INFO")
                        wiki_exists = uploader.feishu_client.check_file_exists_in_wiki(
                            uploader.space_id, 
                            title, 
                            target_wiki_token  # 在分类子节点下检查是否有同名文章
                        )
                    else:
                        # 如果无法解析目标token，使用默认位置检查
                        self.log_message(f"⚠️ 无法解析目标token，使用默认位置检查...", "WARNING")
                        default_wiki_token = self.default_wiki_location.split("/wiki/")[-1] if "/wiki/" in self.default_wiki_location else None
                        if default_wiki_token:
                            self.log_message(f"📂 使用默认位置: {default_wiki_token}", "INFO")
                            wiki_exists = uploader.feishu_client.check_file_exists_in_wiki(
                                uploader.space_id, 
                                title, 
                                default_wiki_token
                            )
                        else:
                            # 最后回退到父节点检查
                            self.log_message(f"⚠️ 默认位置也无法解析，回退到父节点检查...", "WARNING")
                            wiki_exists = uploader.feishu_client.check_file_exists_in_wiki(
                                uploader.space_id, 
                                title, 
                                uploader.parent_wiki_token
                            )
                    
                    if wiki_exists:
                        self.log_message(f"📋 目标分类子节点下已存在同名文档，跳过: {title}", "WARNING")
                        self.queue_stats["completed"] += 1
                        return
                    
                    # 步骤4: 上传到云文档
                    self.log_message(f"☁️ 上传到云文档...", "INFO")
                    file_token = uploader.upload_to_drive(temp_file_path)
                    
                    if file_token == "DUPLICATE":
                        self.log_message(f"📋 云文档重复跳过: {filename}", "WARNING")
                        self.queue_stats["completed"] += 1
                        return
                    
                    if not file_token:
                        self.log_message(f"❌ 云文档上传失败: {filename}", "ERROR")
                        self.queue_stats["failed"] += 1
                        return
                    
                    # 步骤5: 智能转移到目标知识库位置
                    self.log_message(f"📚 智能转移到目标位置...", "INFO")
                    wiki_result = self._smart_move_to_wiki(uploader, file_token, filename, target_location)
                    
                    if wiki_result:
                        if wiki_result.startswith("75"):  # task_id格式
                            self.log_message(f"⏳ 智能转移任务已提交: {wiki_result}", "SUCCESS")
                        else:  # wiki_token格式
                            wiki_url = f"https://thedream.feishu.cn/wiki/{wiki_result}"
                            self.log_message(f"✅ 智能分类处理成功: {filename}", "SUCCESS")
                            self.log_message(f"📖 文档链接: {wiki_url}", "INFO")
                        
                        self.log_message(f"🎯 已转移到: {target_url[:50]}...", "SUCCESS")
                        self.queue_stats["completed"] += 1
                    else:
                        self.log_message(f"❌ 智能转移失败: {filename}", "ERROR")
                        self.queue_stats["failed"] += 1
                        
                except Exception as e:
                    self.log_message(f"❌ 智能分类处理异常: {e}", "ERROR")
                    self.queue_stats["failed"] += 1
                
                finally:
                    if 'uploader' in locals():
                        uploader.cleanup()
                    self._update_queue_stats()
            
            # 在线程中运行
            import threading
            thread = threading.Thread(target=background_process, daemon=True)
            thread.start()
            
        except Exception as e:
            self.log_message(f"❌ 智能分类处理器初始化失败: {e}", "ERROR")

    def _process_with_smart_classification(self, uploader, url: str, format_type: str, target_location: dict) -> bool:
        """使用智能分类处理单个URL的完整流程"""
        try:
            from pathlib import Path
            
            format_name = "PDF" if format_type == "pdf" else "Word文档"
            self.log_message(f"🚀 开始智能分类{format_name}处理: {url[:50]}...", "INFO")
            
            # 步骤1: 下载文件（使用正确的方法名）
            temp_file_path = uploader.download_article(url, format_type)
            if not temp_file_path:
                self.log_message(f"❌ {format_name}下载失败", "ERROR")
                return False
            
            filename = temp_file_path.name  # Path对象使用.name属性
            title = temp_file_path.stem  # Path对象使用.stem属性获取不含扩展名的文件名
            
            self.log_message(f"✅ {format_name}下载成功: {filename}", "SUCCESS")
            self.log_message(f"📝 提取的文件标题: {title}", "INFO")
            
            # 🆕 重新执行智能分类分析（基于实际文件标题）
            self.log_message(f"🔄 基于文件标题重新执行智能分类分析", "INFO")
            updated_target_location = self.find_target_wiki_location(title)
            
            # 比较原始分类和基于文件名的分类
            original_url = target_location.get("wiki_url", "")
            updated_url = updated_target_location.get("wiki_url", "")
            
            if original_url != updated_url:
                self.log_message(f"📊 智能分类结果更新:", "INFO")
                self.log_message(f"   原始分类: {original_url[:50]}...", "INFO")
                self.log_message(f"   更新分类: {updated_url[:50]}...", "INFO")
                target_location = updated_target_location
            else:
                self.log_message(f"📊 智能分类结果一致，使用原分类", "INFO")
            
            # 步骤2: 检查重复
            if uploader.check_file_duplicate_by_title(title):
                self.log_message(f"📋 飞书中已存在同名文件，跳过上传: {filename}", "WARNING")
                return True
            
            # 步骤3: 上传到云文档
            self.log_message(f"☁️ 上传{format_name}到云文档...", "INFO")
            file_token = uploader.upload_to_drive(temp_file_path)  # temp_file_path已经是Path对象
            
            if not file_token:
                self.log_message(f"❌ 云文档上传失败: {filename}", "ERROR")
                return False
            
            # 步骤4: 智能转移到知识库
            target_url = target_location.get("wiki_url", self.default_wiki_location)
            self.log_message(f"📚 智能转移{format_name}到知识库: {target_url[:50]}...", "INFO")
            
            wiki_result = self._smart_move_to_wiki(uploader, file_token, filename, target_location)
            
            if wiki_result:
                if wiki_result.startswith("75"):  # task_id格式
                    self.log_message(f"⏳ {format_name}智能转移任务已提交: {wiki_result}", "SUCCESS")
                else:  # wiki_token格式
                    wiki_url = f"https://thedream.feishu.cn/wiki/{wiki_result}"
                    self.log_message(f"✅ {format_name}智能上传成功: {filename}", "SUCCESS")
                    self.log_message(f"📖 文档链接: {wiki_url}", "INFO")
                
                self.log_message(f"🎯 已智能转移到: {target_url[:50]}...", "SUCCESS")
                return True
            else:
                self.log_message(f"❌ {format_name}智能转移失败: {filename}", "ERROR")
                return False
                
        except Exception as e:
            self.log_message(f"智能分类处理异常: {e}", "ERROR")
            return False

    def test_smart_classification(self, test_title: str = None):
        """测试智能分类功能"""
        if not test_title:
            test_title = "Python编程技术入门教程"
        
        self.log_message(f"🧪 测试智能分类功能", "INFO")
        self.log_message(f"📝 测试标题: {test_title}", "INFO")
        
        target_location = self.find_target_wiki_location(test_title)
        target_url = target_location.get("wiki_url", "未知")
        as_subpage = target_location.get("as_subpage", True)
        
        self.log_message(f"🎯 分类结果 - 目标位置: {target_url}", "SUCCESS")
        self.log_message(f"📋 作为子页面: {'是' if as_subpage else '否'}", "SUCCESS")
        
        return target_location

    def run_classification_test(self):
        """运行智能分类测试"""
        try:
            test_title = self.test_title_var.get().strip()
            if not test_title:
                messagebox.showwarning("警告", "请输入测试标题")
                return
            
            # 先保存当前配置
            self.save_wiki_config()
            
            # 执行测试
            target_location = self.test_smart_classification(test_title)
            
            # 显示结果
            target_url = target_location.get("wiki_url", "未匹配")
            as_subpage = target_location.get("as_subpage", True)
            matched_keywords = []
            
            # 查找匹配的关键词
            title_lower = test_title.lower()
            for location in self.wiki_locations:
                keywords = location.get("keywords", [])
                for keyword in keywords:
                    if keyword.lower() in title_lower:
                        matched_keywords.append(keyword)
                        break
            
            if matched_keywords:
                result_text = f"✅ 匹配关键词: {', '.join(matched_keywords)} | 目标: {target_url[:30]}... | 子页面: {'是' if as_subpage else '否'}"
            else:
                # 使用默认位置设置
                default_as_subpage = self.default_as_subpage_var.get() if hasattr(self, 'default_as_subpage_var') else True
                result_text = f"🏠 使用默认位置: {target_url[:30]}... | 子页面: {'是' if default_as_subpage else '否'}"
            
            self.test_result_var.set(result_text)
            
        except Exception as e:
            self.test_result_var.set(f"❌ 测试失败: {e}")
            self.log_message(f"智能分类测试失败: {e}", "ERROR")

    def upload_to_feishu(self, file_path: str) -> bool:
        """上传文件到飞书知识库（支持PDF和Word文档）- 支持智能分类
        🆕 DOCX文件使用三步导入流程，转换为飞书云文档格式
        """
        if not self.enable_feishu_upload:
            return True
        
        try:
            filename = os.path.basename(file_path)
            file_ext = os.path.splitext(filename)[1].lower()
            file_type = "PDF" if file_ext == ".pdf" else "Word文档" if file_ext == ".docx" else "文件"
            
            # 从文件名提取标题（去掉扩展名）
            title = os.path.splitext(filename)[0]
            
            self.log_message(f"🚀 开始飞书{file_type}智能上传: {filename}", "INFO")
            self.log_message(f"📝 分析标题: {title}", "INFO")
            
            # 🆕 使用智能分类功能找到目标位置
            target_location = self.find_target_wiki_location(title)
            target_url = target_location.get("wiki_url", self.default_wiki_location)
            as_subpage = target_location.get("as_subpage", True)
            
            self.log_message(f"🎯 智能分类结果 - 目标位置: {target_url[:50]}...", "INFO")
            self.log_message(f"📋 作为子页面: {'是' if as_subpage else '否'}", "INFO")
            
            # 🔄 对于PDF和DOCX文件，都使用统一的上传流程
            from pathlib import Path
            from integrated_auto_download_uploader import IntegratedAutoUploader
            
            # 使用整合上传器
            uploader = IntegratedAutoUploader(self.feishu_app_id, self.feishu_app_secret)
            
            # 步骤1: 检查文件是否已存在（同时检查云文档和知识库）
            if uploader.check_file_duplicate_by_title(title, filename):
                self.log_message(f"📋 云文档或知识库中已存在同名文件，跳过上传: {filename}", "WARNING")
                self.log_message(f"💡 提示: '{title}' 已存在，无需重复上传", "INFO")
                uploader.cleanup()
                return True  # 返回True因为这不是错误，只是重复
            
            # 步骤2: 上传到云文档
            self.log_message(f"☁️ 上传{file_type}到云文档...", "INFO")
            file_token = uploader.upload_to_drive(Path(file_path))
            
            # 处理重复文件的情况
            if file_token == "DUPLICATE":
                self.log_message(f"📋 云文档上传时发现重名，跳过后续处理: {filename}", "WARNING")
                uploader.cleanup()
                return True  # 返回True因为这不是错误
            
            if not file_token:
                self.log_message(f"❌ 云文档上传失败: {filename}", "ERROR")
                uploader.cleanup()
                return False
            
            # 步骤3: 智能转移到目标知识库位置
            self.log_message(f"📚 智能转移{file_type}到知识库位置...", "INFO")
            self.log_message(f"🎯 目标位置: {target_url[:50]}...", "INFO")
            
            # 🆕 使用智能分类转移
            wiki_result = self._smart_move_to_wiki(uploader, file_token, filename, target_location)
            
            if wiki_result:
                if wiki_result.startswith("75"):  # task_id格式
                    self.log_message(f"⏳ 飞书{file_type}智能转移任务已提交: {wiki_result}", "SUCCESS")
                else:  # wiki_token格式
                    wiki_url = f"https://thedream.feishu.cn/wiki/{wiki_result}"
                    self.log_message(f"✅ 飞书{file_type}智能上传成功: {filename}", "SUCCESS")
                    self.log_message(f"📖 文档链接: {wiki_url}", "INFO")
                    self.log_message(f"🎯 已转移到: {target_url[:50]}...", "SUCCESS")
                
                uploader.cleanup()
                return True
            else:
                self.log_message(f"❌ 智能转移失败: {filename}", "ERROR")
                uploader.cleanup()
                return False
                
        except Exception as e:
            self.log_message(f"飞书智能上传异常: {e}", "ERROR")
            return False

    def _upload_to_feishu_batch(self, file_path: str) -> bool:
        """批量下载专用的飞书上传方法，使用智能分类功能"""
        if not self.batch_feishu_upload_var.get():
            return True
        
        try:
            filename = os.path.basename(file_path)
            file_ext = os.path.splitext(filename)[1].lower()
            file_type = "PDF" if file_ext == ".pdf" else "Word文档" if file_ext == ".docx" else "文件"
            
            # 从文件名提取标题（去掉扩展名）
            title = os.path.splitext(filename)[0]
            
            self.log_message(f"🚀 开始批量飞书{file_type}智能上传: {filename}", "INFO")
            self.log_message(f"📝 分析标题: {title}", "INFO")
            
            # 🆕 使用智能分类功能找到目标位置
            target_location = self.find_target_wiki_location(title)
            target_url = target_location.get("wiki_url", self.default_wiki_location)
            as_subpage = target_location.get("as_subpage", True)
            
            self.log_message(f"🎯 批量上传目标位置: {target_url}", "INFO")
            self.log_message(f"📋 作为子页面: {'是' if as_subpage else '否'}", "INFO")
            
            # 🆕 对于DOCX文件，也使用统一的上传流程（不再使用三步导入）
            from pathlib import Path
            from integrated_auto_download_uploader import IntegratedAutoUploader
            
            # 使用整合上传器
            uploader = IntegratedAutoUploader(self.feishu_app_id, self.feishu_app_secret)
            
            # 步骤1: 检查文件是否已存在（同时检查云文档和知识库）
            if uploader.check_file_duplicate_by_title(title, filename):
                self.log_message(f"📋 云文档或知识库中已存在同名文件，跳过批量上传: {filename}", "WARNING")
                self.log_message(f"💡 提示: '{title}' 已存在，无需重复上传", "INFO")
                uploader.cleanup()
                return True  # 返回True因为这不是错误，只是重复
            
            # 步骤2: 上传到云文档
            self.log_message(f"☁️ 批量上传{file_type}到云文档...", "INFO")
            file_token = uploader.upload_to_drive(Path(file_path))
            
            # 处理重复文件的情况
            if file_token == "DUPLICATE":
                self.log_message(f"📋 云文档上传时发现重名，跳过后续处理: {filename}", "WARNING")
                uploader.cleanup()
                return True  # 返回True因为这不是错误，只是重复
            
            if not file_token:
                self.log_message(f"❌ 云文档上传失败: {filename}", "ERROR")
                uploader.cleanup()
                return False
            
            # 步骤3: 智能转移到目标知识库位置
            self.log_message(f"📚 批量智能转移{file_type}到知识库位置...", "INFO")
            self.log_message(f"🎯 目标位置: {target_url}", "INFO")
            
            # 🆕 使用智能分类转移
            wiki_result = self._smart_move_to_wiki(uploader, file_token, filename, target_location)
            
            if wiki_result:
                if wiki_result.startswith("75"):  # task_id格式
                    self.log_message(f"⏳ 批量飞书{file_type}智能转移任务已提交: {wiki_result}", "SUCCESS")
                else:  # wiki_token格式
                    wiki_url = f"https://thedream.feishu.cn/wiki/{wiki_result}"
                    self.log_message(f"✅ 批量飞书{file_type}智能上传成功: {filename}", "SUCCESS")
                    self.log_message(f"📖 文档链接: {wiki_url}", "INFO")
                    self.log_message(f"🎯 已转移到: {target_url}", "SUCCESS")
                
                uploader.cleanup()
                return True
            else:
                self.log_message(f"❌ 批量智能转移失败: {filename}", "ERROR")
                uploader.cleanup()
                return False
                
        except Exception as e:
            self.log_message(f"批量飞书智能上传异常: {e}", "ERROR")
            return False

    def _smart_move_to_wiki(self, uploader, file_token: str, filename: str, target_location: dict) -> str:
        """智能转移文件到知识库指定位置"""
        try:
            target_url = target_location.get("wiki_url", self.default_wiki_location)
            as_subpage = target_location.get("as_subpage", True)
            
            self.log_message(f"📋 智能转移详情:", "INFO")
            self.log_message(f"   📁 文件: {filename}", "INFO")
            self.log_message(f"   🎯 目标URL: {target_url}", "INFO")
            self.log_message(f"   📄 作为子页面: {'是' if as_subpage else '否'}", "INFO")
            
            # 解析目标URL类型并提取wiki_token
            wiki_token = None
            
            if "drive/folder/" in target_url:
                # 云文档文件夹类型 - 需要移动到知识库
                self.log_message(f"📁 检测到云文档文件夹链接，执行标准转移流程", "INFO")
                return uploader.move_to_wiki(file_token, filename)
                
            elif "wiki/" in target_url:
                # 知识库类型 - 提取wiki_token
                # 处理包含查询参数的URL
                if "?" in target_url:
                    clean_url = target_url.split("?")[0]  # 去除查询参数
                else:
                    clean_url = target_url
                
                if "/wiki/space/" in clean_url:
                    # 知识库空间类型
                    wiki_token = clean_url.split("/wiki/space/")[-1]
                    self.log_message(f"📚 检测到知识库空间链接: {wiki_token}", "INFO")
                elif "/wiki/" in clean_url:
                    # 知识库页面类型
                    wiki_token = clean_url.split("/wiki/")[-1]
                    self.log_message(f"📄 检测到知识库页面链接: {wiki_token}", "INFO")
                
                if wiki_token:
                    self.log_message(f"🎯 提取的wiki_token: {wiki_token}", "INFO")
                    if as_subpage:
                        self.log_message(f"📋 转移为指定页面的子页面", "INFO")
                    else:
                        self.log_message(f"📑 转移为同级页面", "INFO")
                    
                    # 🔥 使用提取的wiki_token进行智能转移
                    return self._move_to_specific_wiki_location(uploader, file_token, filename, wiki_token)
                else:
                    self.log_message(f"⚠️ 无法从URL提取wiki_token: {target_url}", "WARNING")
                    self.log_message(f"🔄 回退到标准转移方法", "INFO")
                    return uploader.move_to_wiki(file_token, filename)
                    
            else:
                # 未知链接类型，使用默认转移
                self.log_message(f"⚠️ 未识别的链接类型: {target_url}", "WARNING")
                self.log_message(f"🔄 回退到标准转移方法", "INFO")
                return uploader.move_to_wiki(file_token, filename)
            
            # 🔥 修复：如果上面的条件都没有返回，确保有返回值
            self.log_message(f"⚠️ 智能转移逻辑执行完毕但无明确结果，使用标准转移", "WARNING")
            return uploader.move_to_wiki(file_token, filename)
                
        except Exception as e:
            self.log_message(f"❌ 智能转移过程出错: {e}", "ERROR")
            self.log_message(f"🔄 出错后回退到标准转移方法", "INFO")
            try:
                return uploader.move_to_wiki(file_token, filename)
            except Exception as e2:
                self.log_message(f"❌ 标准转移方法也失败: {e2}", "ERROR")
                return None

    def _move_to_specific_wiki_location(self, uploader, file_token: str, filename: str, parent_wiki_token: str) -> str:
        """转移文件到指定的知识库位置 - 支持智能分类"""
        try:
            self.log_message(f"🚀 执行智能分类转移:", "INFO")
            self.log_message(f"   📁 文件: {filename}", "INFO")
            self.log_message(f"   🎯 目标wiki_token: {parent_wiki_token}", "INFO")
            
            # 使用uploader的API，但指定特定的parent_wiki_token
            feishu_client = uploader.feishu_client if hasattr(uploader, 'feishu_client') else None
            
            if not feishu_client:
                self.log_message(f"❌ 无法获取feishu_client，回退到标准方法", "ERROR")
                return uploader.move_to_wiki(file_token, filename)
            
            # 手动构建API请求 - 支持智能分类指定位置
            api_url = f"https://open.feishu.cn/open-apis/wiki/v2/spaces/{uploader.space_id}/nodes/move_docs_to_wiki"
            
            # 🔥 构建智能分类API数据
            data = {
                "obj_token": file_token,
                "obj_type": "file",
                "parent_wiki_token": parent_wiki_token
            }
            
            self.log_message(f"🔄 智能分类API调用: {api_url}", "INFO")
            self.log_message(f"📋 智能分类请求数据: {data}", "INFO")
            
            # 调用API
            response_obj = feishu_client._make_authenticated_request('POST', api_url, json=data)
            
            if response_obj and response_obj.status_code == 200:
                response = response_obj.json()
                self.log_message(f"📡 智能分类API响应: {response}", "INFO")
                
                if response.get("code") == 0:
                    data_result = response.get("data", {})
                    task_id = data_result.get("task_id")
                    wiki_token = data_result.get("wiki_token")
                    
                    if wiki_token:
                        wiki_url = f"https://thedream.feishu.cn/wiki/{wiki_token}"
                        self.log_message(f"✅ 智能分类转移成功!", "SUCCESS")
                        self.log_message(f"📖 新文档链接: {wiki_url}", "SUCCESS")
                        self.log_message(f"🎯 分类位置: {parent_wiki_token}", "SUCCESS")
                        return wiki_token
                    elif task_id:
                        self.log_message(f"⏳ 智能分类转移任务已提交: {task_id}", "SUCCESS")
                        self.log_message(f"🎯 分类位置: {parent_wiki_token}", "SUCCESS")
                        return task_id
                    else:
                        self.log_message(f"⚠️ 智能分类响应无结果数据: {response}", "WARNING")
                        return None
                else:
                    error_msg = response.get("msg", "未知错误")
                    self.log_message(f"❌ 智能分类API调用失败: code={response.get('code')}, msg={error_msg}", "ERROR")
                    
                    # 如果是权限或其他API错误，回退到标准方法
                    self.log_message(f"🔄 回退到标准转移方法", "INFO")
                    return uploader.move_to_wiki(file_token, filename)
            else:
                status_code = response_obj.status_code if response_obj else 'None'
                self.log_message(f"❌ 智能分类HTTP请求失败: status_code={status_code}", "ERROR")
                
                # HTTP错误也回退到标准方法
                self.log_message(f"🔄 回退到标准转移方法", "INFO")
                return uploader.move_to_wiki(file_token, filename)
                
        except Exception as e:
            self.log_message(f"❌ 智能分类转移异常: {e}", "ERROR")
            self.log_message(f"🔄 异常后回退到标准转移方法", "INFO")
            try:
                return uploader.move_to_wiki(file_token, filename)
            except Exception as e2:
                self.log_message(f"❌ 标准转移方法也失败: {e2}", "ERROR")
                return None

    def on_closing(self):
        """窗口关闭事件"""
        if self.is_downloading:
            result = messagebox.askyesno("确认退出", "正在下载中，确定要退出吗？")
            if not result:
                return
        
        # 停止自动下载
        if self.is_auto_collecting:
            self.stop_auto_download()
        
        # 停止定时器
        if self.timer_job_id:
            self.stop_timer_update()
        
        # 保存设置
        self.save_auto_update_settings()
        
        # 清理资源
        try:
            if self.url_scraper:
                self.url_scraper.cleanup()
        except:
            pass
        
        self.root.destroy()

    def create_log_area(self, parent):
        """创建日志输出区域"""
        log_frame = ttk.LabelFrame(parent, text="📝 运行日志", padding="5")
        log_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        parent.rowconfigure(2, weight=1)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        # 创建文本区域
        self.log_text = scrolledtext.ScrolledText(log_frame, height=12, state='disabled')
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 清空日志按钮
        ttk.Button(log_frame, text="清空日志", command=self.clear_log).grid(row=1, column=0, pady=(5, 0))
    
    def create_status_bar(self, parent):
        """创建状态栏"""
        status_frame = ttk.Frame(parent)
        status_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
        
        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(status_frame, textvariable=self.status_var).pack(side=tk.LEFT)
        
        # 版本信息
        ttk.Label(status_frame, text="v4.0 全功能版 - 完全自动化").pack(side=tk.RIGHT)
    
    # ===== 🆕 链接收集器功能方法 =====
    
    def start_collector_login(self):
        """启动链接收集器登录"""
        try:
            self.log_message("🚀 启动链接收集器登录...", "INFO")
            
            # 创建链接收集器实例
            if not self.link_collector:
                # 使用简化版链接收集器
                self.link_collector = SimplifiedLinkCollector()
            
            # 在新线程中执行登录
            def login_worker():
                try:
                    self.collector_login_btn.config(state='disabled', text="登录中...")
                    self.collector_login_status_var.set("正在登录...")
                    self.collector_login_status_label.config(foreground="orange")
                    
                    # 调用简化版登录方法
                    login_success = self.link_collector.start_login_flow()
                    
                    # 检查登录状态
                    if login_success and self.link_collector.token:
                        self.collector_login_status_var.set("✅ 已登录")
                        self.collector_login_status_label.config(foreground="green")
                        self.collector_login_btn.config(state='normal', text="✅ 已登录")
                        self.log_message("✅ 链接收集器登录成功", "SUCCESS")
                    else:
                        self.collector_login_status_var.set("❌ 登录失败")
                        self.collector_login_status_label.config(foreground="red")
                        self.collector_login_btn.config(state='normal', text="🚀 开始登录")
                    
                except Exception as e:
                    self.log_message(f"❌ 链接收集器登录失败: {e}", "ERROR")
                    self.collector_login_status_var.set("❌ 登录失败")
                    self.collector_login_status_label.config(foreground="red")
                    self.collector_login_btn.config(state='normal', text="🚀 开始登录")
            
            threading.Thread(target=login_worker, daemon=True).start()
            
        except Exception as e:
            self.log_message(f"❌ 启动链接收集器登录失败: {e}", "ERROR")
    
    def retry_collector_login(self):
        """重新登录链接收集器"""
        self.log_message("🔄 重新登录链接收集器", "INFO")
        
        # 重置状态
        if self.link_collector:
            self.link_collector.token = ""
            self.link_collector.cookies = {}
        
        self.collector_login_status_var.set("未登录")
        self.collector_login_status_label.config(foreground="red")
        
        # 重新开始登录
        self.start_collector_login()
    
    def search_collector_accounts(self):
        """搜索公众号"""
        if not self.link_collector or not self.link_collector.token:
            messagebox.showerror("错误", "请先登录微信公众号")
            return
        
        keyword = self.collector_search_var.get().strip()
        if not keyword:
            messagebox.showerror("错误", "请输入搜索关键词")
            return
        
        self.log_message(f"🔍 搜索公众号: {keyword}", "INFO")
        self.collector_search_btn.config(state='disabled', text="搜索中...")
        
        def search_worker():
            try:
                # 调用简化版搜索方法
                accounts = self.link_collector.search_account(keyword)
                
                # 显示搜索结果
                self.collector_results_text.delete('1.0', tk.END)
                if accounts:
                    result_text = f"搜索关键词: {keyword}\n找到 {len(accounts)} 个公众号:\n\n"
                    for i, account in enumerate(accounts, 1):
                        nickname = account.get('nickname', '')
                        alias = account.get('alias', '')
                        signature = account.get('signature', '')[:50] + '...' if len(account.get('signature', '')) > 50 else account.get('signature', '')
                        
                        result_text += f"{i}. {nickname} ({alias})\n   {signature}\n\n"
                    
                    # 自动选择第一个结果
                    if self.link_collector.current_account:
                        selected_account = self.link_collector.current_account
                        self.collector_selected_var.set(f"{selected_account.get('nickname', '')} ({selected_account.get('alias', '')})")
                        result_text += f"✅ 已自动选择: {selected_account.get('nickname', '')}"
                else:
                    result_text = f"搜索关键词: {keyword}\n❌ 未找到匹配的公众号"
                
                self.collector_results_text.insert(tk.END, result_text)
                self.log_message(f"✅ 搜索完成: {keyword}，找到 {len(accounts)} 个结果", "SUCCESS")
                    
            except Exception as e:
                self.log_message(f"❌ 搜索失败: {e}", "ERROR")
                self.collector_results_text.delete('1.0', tk.END)
                self.collector_results_text.insert(tk.END, f"搜索失败: {e}")
            finally:
                self.collector_search_btn.config(state='normal', text="🔍 搜索")
        
        threading.Thread(target=search_worker, daemon=True).start()
    
    def start_collect_links(self):
        """开始收集链接"""
        if not self.link_collector or not self.link_collector.current_account:
            messagebox.showerror("错误", "请先登录并选择公众号")
            return
        
        try:
            limit = int(self.collector_limit_var.get())
            start_date_str = self.collector_start_date_var.get().strip()
            end_date_str = self.collector_end_date_var.get().strip()
            
            from datetime import datetime
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
            
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字和日期格式 (YYYY-MM-DD)")
            return
        
        self.log_message(f"📥 开始收集链接 (最多{limit}篇，{start_date_str} 至 {end_date_str})", "INFO")
        self.collector_collect_btn.config(state='disabled', text="收集中...")
        
        def collect_worker():
            try:
                # 清空之前的收集结果
                self.collected_articles.clear()
                
                # 调用简化版收集方法
                articles = self.link_collector.collect_articles(limit, start_date, end_date)
                
                # 获取收集结果
                self.collected_articles = articles.copy()
                
                # 更新统计
                self.collector_stats_var.set(f"已收集: {len(self.collected_articles)} 篇文章")
                self.log_message(f"✅ 收集完成，共获取 {len(self.collected_articles)} 篇文章链接", "SUCCESS")
                
            except Exception as e:
                self.log_message(f"❌ 收集失败: {e}", "ERROR")
            finally:
                self.collector_collect_btn.config(state='normal', text="📥 收集链接")
                self.collector_progress_var.set("")
        
        threading.Thread(target=collect_worker, daemon=True).start()
    
    def export_to_batch_download(self):
        """导出链接到批量下载页面"""
        if not self.collected_articles:
            messagebox.showwarning("警告", "没有可导出的链接")
            return
        
        # 提取链接
        links = [article['link'] for article in self.collected_articles if article.get('link')]
        
        if not links:
            messagebox.showwarning("警告", "没有有效的链接")
            return
        
        # 添加到批量下载文本框
        current_content = self.batch_urls_text.get("1.0", tk.END).strip()
        
        # 如果文本框为空或只有示例内容，则清空后添加
        if not current_content or "https://mp.weixin.qq.com/s?__biz=xxx" in current_content:
            self.batch_urls_text.delete("1.0", tk.END)
            self.batch_urls_text.insert(tk.END, '\n'.join(links))
        else:
            # 在末尾添加新链接
            self.batch_urls_text.insert(tk.END, '\n' + '\n'.join(links))
        
        # 去重
        self.clean_duplicate_urls()
        
        self.log_message(f"📋 已导出 {len(links)} 个链接到批量下载页面", "SUCCESS")
        messagebox.showinfo("成功", f"已导出 {len(links)} 个链接到批量下载页面")
    
    def export_collector_csv(self):
        """导出收集器数据为CSV"""
        if not self.collected_articles:
            messagebox.showwarning("警告", "没有可导出的数据")
            return
        
        try:
            # 确保输出目录存在
            output_dir = os.path.join(self.output_dir, "links")
            os.makedirs(output_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"collected_articles_{timestamp}.csv"
            filepath = os.path.join(output_dir, filename)
            
            import csv
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['title', 'link', 'author', 'publish_time', 'account_name', 'account_alias', 'digest']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for article in self.collected_articles:
                    writer.writerow(article)
            
            self.log_message(f"✅ CSV导出成功: {filepath}", "SUCCESS")
            messagebox.showinfo("成功", f"CSV文件已导出到:\n{filepath}")
            
        except Exception as e:
            self.log_message(f"❌ CSV导出失败: {e}", "ERROR")
            messagebox.showerror("错误", f"导出失败: {e}")
    
    def clear_collector_data(self):
        """清空收集器数据"""
        if messagebox.askyesno("确认", "确定要清空所有收集的数据吗？"):
            self.collected_articles.clear()
            self.collector_stats_var.set("已收集: 0 篇文章")
            self.collector_results_text.delete('1.0', tk.END)
            self.collector_selected_var.set("未选择")
            self.log_message("🗑️ 收集器数据已清空", "INFO")
    
    # ===== 🆕 RO自动更新功能方法 =====
    
    def toggle_auto_update(self):
        """切换自动更新开关"""
        self.auto_update_enabled = self.auto_update_enabled_var.get()
        self.save_auto_update_settings()
        
        if self.auto_update_enabled:
            self.log_message("✅ RO文章自动更新已启用", "SUCCESS")
        else:
            self.log_message("❌ RO文章自动更新已禁用", "INFO")
    
    def toggle_timer_update(self):
        """切换定时更新开关"""
        self.timer_enabled = self.timer_enabled_var.get()
        
        if self.timer_enabled:
            # 启动定时器
            self.start_timer_update()
            self.log_message("⏰ 定时自动更新已启用", "SUCCESS")
        else:
            # 停止定时器
            self.stop_timer_update()
            self.log_message("⏰ 定时自动更新已禁用", "INFO")
        
        self.save_auto_update_settings()
    
    def on_timer_interval_changed(self, event):
        """定时间隔输入变化事件"""
        try:
            interval_str = self.timer_interval_var.get()
            if interval_str.isdigit():
                new_interval = int(interval_str)
                if new_interval > 0:
                    self.timer_interval = new_interval
                    # 如果定时器正在运行，重新启动以应用新间隔
                    if self.timer_enabled and self.timer_job_id:
                        self.stop_timer_update()
                        self.start_timer_update()
                    self.save_auto_update_settings()
        except Exception as e:
            pass  # 忽略输入错误
    
    def start_timer_update(self):
        """启动定时更新"""
        try:
            if self.timer_job_id:
                # 取消现有的定时器
                self.root.after_cancel(self.timer_job_id)
            
            # 计算下次更新时间
            from datetime import datetime, timedelta
            next_time = datetime.now() + timedelta(minutes=self.timer_interval)
            self.next_update_time = next_time
            self.next_update_time_var.set(next_time.strftime("%H:%M:%S"))
            
            # 设置定时器（转换为毫秒）
            interval_ms = self.timer_interval * 60 * 1000
            self.timer_job_id = self.root.after(interval_ms, self.on_timer_update)
            
            self.log_auto_update(f"⏰ 定时器已启动，间隔: {self.timer_interval} 分钟")
            self.log_auto_update(f"   📅 下次更新时间: {next_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
        except Exception as e:
            self.log_auto_update(f"❌ 启动定时器失败: {e}")
    
    def stop_timer_update(self):
        """停止定时更新"""
        try:
            if self.timer_job_id:
                self.root.after_cancel(self.timer_job_id)
                self.timer_job_id = None
            
            self.next_update_time = None
            self.next_update_time_var.set("定时器未启动")
            
            self.log_auto_update("⏰ 定时器已停止")
            
        except Exception as e:
            self.log_auto_update(f"❌ 停止定时器失败: {e}")
    
    def on_timer_update(self):
        """定时器触发的更新事件"""
        try:
            self.log_auto_update("⏰ 定时器触发 - 开始自动更新")
            
            # 执行自动更新
            self.start_auto_update_process()
            
            # 设置下一次定时器
            if self.timer_enabled:
                self.start_timer_update()
            
        except Exception as e:
            self.log_auto_update(f"❌ 定时更新执行失败: {e}")
            # 即使失败也要重新设置定时器
            if self.timer_enabled:
                self.start_timer_update()
    
    def check_auto_update_on_startup(self):
        """启动时检查是否需要自动更新"""
        try:
            # 加载自动更新设置
            self.load_auto_update_settings()
            
            if self.auto_update_enabled:
                self.log_message("🤖 检测到RO自动更新已启用，准备自动执行...", "INFO")
                self.auto_update_status_var.set("启动检查中...")
                
                # 延迟2秒后开始自动更新流程
                self.root.after(2000, self.start_auto_update_process)
            else:
                self.auto_update_status_var.set("未启用")
                
        except Exception as e:
            self.log_message(f"❌ 启动检查失败: {e}", "ERROR")
    
    def start_manual_update(self):
        """手动启动更新"""
        self.log_message("🚀 手动启动RO文章更新...", "INFO")
        self.start_auto_update_process()
    
    def start_auto_update_process(self):
        """启动自动更新流程"""
        self.auto_update_status_var.set("正在执行自动更新...")
        self.manual_update_btn.config(state='disabled', text="更新中...")
        
        def auto_update_worker():
            try:
                self.log_auto_update("🤖 开始RO文章自动更新流程")
                
                # 步骤1: 登录微信公众号
                self.log_auto_update("📱 步骤1: 自动登录微信公众号...")
                if not self.auto_login_wechat():
                    return
                
                # 步骤2: 搜索RO公众号
                self.log_auto_update("🔍 步骤2: 搜索仙境传说RO新启航公众号...")
                if not self.auto_search_ro_account():
                    return
                
                # 步骤3: 计算需要更新的日期范围
                self.log_auto_update("📅 步骤3: 计算更新日期范围...")
                start_date, end_date = self.calculate_update_date_range()
                
                # 步骤4: 收集新文章链接
                self.log_auto_update(f"📥 步骤4: 收集新文章 ({start_date} 至 {end_date})...")
                new_articles = self.auto_collect_new_articles(start_date, end_date)
                
                # 步骤5: 下载并上传新文章（包括处理空列表的情况）
                self.log_auto_update(f"📚 步骤5: 处理文章下载上传...")
                success_count = self.auto_download_and_upload_articles(new_articles)
                
                # 🔥 修复：根据实际情况给出准确的完成状态
                if not new_articles:
                    self.log_auto_update("🎉 自动更新完成！知识库内容已是最新状态")
                    self.auto_update_status_var.set("完成 - 无新文章")
                    # 即使没有新文章，也更新日期节点，表示已检查到该日期
                    self.log_auto_update("📅 步骤6: 更新检查日期节点...")
                    self.update_last_update_date(end_date)
                else:
                    # 步骤6: 更新日期节点
                    if success_count > 0:
                        self.log_auto_update("📅 步骤6: 更新日期节点...")
                        self.update_last_update_date(end_date)
                    
                    self.log_auto_update(f"🎉 自动更新完成！成功处理 {success_count}/{len(new_articles)} 篇文章")
                    self.auto_update_status_var.set(f"完成 - 更新了{success_count}篇文章")
                
            except Exception as e:
                self.log_auto_update(f"❌ 自动更新失败: {e}")
                self.auto_update_status_var.set("执行失败")
            finally:
                self.manual_update_btn.config(state='normal', text="🚀 立即执行更新")
        
        threading.Thread(target=auto_update_worker, daemon=True).start()
    
    def test_ro_account_search(self):
        """测试RO公众号搜索"""
        self.log_message("🔍 测试RO公众号搜索...", "INFO")
        
        def test_worker():
            try:
                if not self.link_collector or not self.link_collector.token:
                    self.log_message("❌ 请先登录微信公众号", "ERROR")
                    return
                
                # 搜索RO公众号
                keyword = "仙境传说RO新启航"
                accounts = self.link_collector.search_account(keyword)
                
                if accounts and self.link_collector.current_account:
                    nickname = self.link_collector.current_account.get('nickname', '')
                    alias = self.link_collector.current_account.get('alias', '')
                    self.ro_account_status_var.set(f"{nickname} ({alias}) ✅")
                    self.log_message(f"✅ 找到RO公众号: {nickname}", "SUCCESS")
                else:
                    self.ro_account_status_var.set("仙境传说RO新启航 ❌未找到")
                    self.log_message("❌ 未找到RO公众号", "ERROR")
                    
            except Exception as e:
                self.log_message(f"❌ 测试搜索失败: {e}", "ERROR")
        
        threading.Thread(target=test_worker, daemon=True).start()
    
    def reset_update_date(self):
        """重置更新日期"""
        if messagebox.askyesno("确认重置", "确定要重置更新日期到 2025-06-10 吗？"):
            self.last_update_date = "2025-06-10"
            self.last_update_date_var.set(self.last_update_date)
            self.save_auto_update_settings()
            self.log_message("📅 更新日期已重置到 2025-06-10", "INFO")
    
    def view_update_log(self):
        """查看更新日志"""
        self.log_message("📋 显示更新日志窗口", "INFO")
        
        # 创建日志查看窗口
        log_window = tk.Toplevel(self.root)
        log_window.title("RO文章更新日志")
        log_window.geometry("800x600")
        
        log_text = scrolledtext.ScrolledText(log_window, wrap=tk.WORD)
        log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 显示当前自动更新日志内容
        current_log = self.auto_update_log.get('1.0', tk.END)
        log_text.insert('1.0', current_log)
        
        # 添加关闭按钮
        ttk.Button(log_window, text="关闭", command=log_window.destroy).pack(pady=10)
    
    # ===== 🆕 自动更新辅助方法 =====
    
    def log_auto_update(self, message):
        """记录自动更新日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        self.auto_update_log.insert(tk.END, log_entry)
        self.auto_update_log.see(tk.END)
        self.root.update()
        
        # 同时输出到主日志
        self.log_message(message, "INFO")
    
    def save_auto_update_settings(self):
        """保存自动更新设置"""
        try:
            settings = {
                "auto_update_enabled": self.auto_update_enabled,
                "last_update_date": self.last_update_date,
                "timer_enabled": self.timer_enabled,
                "timer_interval": self.timer_interval
            }
            
            with open("ro_auto_update_settings.json", "w", encoding="utf-8") as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            self.log_message(f"保存自动更新设置失败: {e}", "WARNING")
    
    def load_auto_update_settings(self):
        """加载自动更新设置"""
        try:
            if os.path.exists("ro_auto_update_settings.json"):
                with open("ro_auto_update_settings.json", "r", encoding="utf-8") as f:
                    settings = json.load(f)
                
                self.auto_update_enabled = settings.get("auto_update_enabled", False)
                self.last_update_date = settings.get("last_update_date", "2025-06-10")
                self.timer_enabled = settings.get("timer_enabled", False)
                self.timer_interval = settings.get("timer_interval", 60)
                
                # 更新GUI
                self.auto_update_enabled_var.set(self.auto_update_enabled)
                self.last_update_date_var.set(self.last_update_date)
                self.timer_enabled_var.set(self.timer_enabled)
                self.timer_interval_var.set(str(self.timer_interval))
                
                # 如果定时器是启用状态，恢复定时器
                if self.timer_enabled:
                    self.root.after(1000, self.start_timer_update)  # 延迟1秒启动
                
        except Exception as e:
            self.log_message(f"加载自动更新设置失败: {e}", "WARNING")
    
    def auto_login_wechat(self):
        """自动登录微信公众号"""
        try:
            if not self.link_collector:
                self.link_collector = SimplifiedLinkCollector()
            
            if self.link_collector.token:
                self.log_auto_update("✅ 已有有效登录token")
                return True
            
            self.log_auto_update("📱 启动微信公众号登录...")
            
            # 启动登录流程（这会显示二维码页面）
            login_success = self.link_collector.start_login_flow()
            
            if login_success:
                self.log_auto_update("✅ 微信公众号登录成功")
                return True
            else:
                self.log_auto_update("❌ 登录失败，请重试")
                return False
            
        except Exception as e:
            self.log_auto_update(f"❌ 自动登录失败: {e}")
            return False
    
    def auto_search_ro_account(self):
        """自动搜索RO公众号"""
        try:
            keyword = "仙境传说RO新启航"
            self.log_auto_update(f"🔍 搜索公众号: {keyword}")
            
            accounts = self.link_collector.search_account(keyword)
            
            if accounts and self.link_collector.current_account:
                nickname = self.link_collector.current_account.get('nickname', '')
                self.log_auto_update(f"✅ 找到并选择公众号: {nickname}")
                self.ro_account_info = self.link_collector.current_account
                return True
            else:
                self.log_auto_update("❌ 未找到RO公众号")
                return False
                
        except Exception as e:
            self.log_auto_update(f"❌ 搜索RO公众号失败: {e}")
            return False
    
    def calculate_update_date_range(self):
        """计算更新日期范围 - 包含防漏检查"""
        from datetime import datetime, timedelta
        
        # 当前日期
        today = datetime.now()
        today_str = today.strftime("%Y-%m-%d")
        
        # 上次更新日期
        last_update = datetime.strptime(self.last_update_date, "%Y-%m-%d")
        
        # 🆕 防漏检查：检查前3天的所有文章
        # 从上次更新日期前3天开始，确保不遗漏任何文章
        start_date = last_update - timedelta(days=3)
        start_date_str = start_date.strftime("%Y-%m-%d")
        
        self.log_auto_update(f"📅 计算更新范围（防漏检查）:")
        self.log_auto_update(f"   🕐 开始日期: {start_date_str} (上次更新前3天)")
        self.log_auto_update(f"   🕐 结束日期: {today_str} (今天)")
        self.log_auto_update(f"   📌 上次更新: {self.last_update_date}")
        self.log_auto_update(f"   🛡️ 防漏策略: 向前检查3天确保完整性")
        
        return start_date_str, today_str
    
    def auto_collect_new_articles(self, start_date, end_date):
        """自动收集新文章并进行智能知识库重复检测"""
        try:
            if not self.link_collector.current_account:
                self.log_auto_update("❌ 没有选择的公众号")
                return []
            
            from datetime import datetime
            from integrated_auto_download_uploader import IntegratedAutoUploader
            
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
            
            # 收集文章
            articles = self.link_collector.collect_articles(100, start_date_obj, end_date_obj)  # 最多100篇
            
            self.log_auto_update(f"📥 收集到 {len(articles)} 篇文章")
            
            # 🔥 修复：跳过时间筛选，直接进行智能知识库重复检测
            # 由于我们已经做了防漏检查（前3天），让知识库重复检测来决定哪些文章需要更新
            self.log_auto_update(f"📊 跳过时间筛选，将对所有 {len(articles)} 篇文章进行智能重复检测")
            self.log_auto_update(f"💡 原因：防漏检查已限定时间范围，智能重复检测更准确")
            
            # 显示收集到的文章详情
            if articles:
                self.log_auto_update(f"📝 收集到的文章详情:")
                for i, article in enumerate(articles, 1):
                    title = article.get('title', '无标题')
                    publish_time = article.get('publish_time', '无时间')
                    link = article.get('link', '无链接')
                    self.log_auto_update(f"   📄 [{i}] {title}")
                    self.log_auto_update(f"       📅 发布时间: {publish_time}")
                    self.log_auto_update(f"       🔗 链接: {link[:60]}...")
                self.log_auto_update("")  # 分隔线
            else:
                self.log_auto_update(f"📝 指定时间范围内没有收集到文章")
            
            time_filtered_articles = articles  # 直接使用所有收集到的文章
            
            # 🆕 创建uploader用于重复检测
            uploader = IntegratedAutoUploader(self.feishu_app_id, self.feishu_app_secret)
            
            # 🆕 进行智能知识库重复检测
            self.log_auto_update(f"🧠 开始智能知识库重复检测...")
            self.log_auto_update(f"💡 策略：根据文章标题关键词，只在对应分类子节点下检测重复文章")
            self.log_auto_update(f"📂 知识库结构：父节点 → 分类子节点(13个) → 文章")
            final_articles = []
            duplicate_count = 0
            
            for i, article in enumerate(time_filtered_articles, 1):
                title = article.get('title', '')
                publish_time = article.get('publish_time', '无时间')
                link = article.get('link', '无链接')
                
                if not title:
                    self.log_auto_update(f"   ⚠️ [{i}/{len(time_filtered_articles)}] 跳过无标题文章")
                    continue
                
                self.log_auto_update(f"🔍 [{i}/{len(time_filtered_articles)}] 智能检测文章:")
                self.log_auto_update(f"   📝 文章标题: {title}")
                self.log_auto_update(f"   📅 发布时间: {publish_time}")
                self.log_auto_update(f"   🔗 文章链接: {link[:60]}...")
                
                # 🔥 使用智能分类找到目标位置
                self.log_auto_update(f"   🧠 步骤1: 执行智能分类分析...")
                target_location = self.find_target_wiki_location(title)
                target_url = target_location.get("wiki_url", self.default_wiki_location)
                
                # 提取目标位置的wiki_token
                target_wiki_token = None
                if "wiki/" in target_url:
                    if "?" in target_url:
                        clean_url = target_url.split("?")[0]
                    else:
                        clean_url = target_url
                    
                    if "/wiki/space/" in clean_url:
                        target_wiki_token = clean_url.split("/wiki/space/")[-1]
                    elif "/wiki/" in clean_url:
                        target_wiki_token = clean_url.split("/wiki/")[-1]
                
                # 提取匹配的关键词（用于日志显示）
                matched_keywords = target_location.get("keywords", [])
                if matched_keywords:
                    # 找到实际匹配的关键词
                    matched_keyword = None
                    title_lower = title.lower()
                    for keyword in matched_keywords:
                        if keyword.lower() in title_lower:
                            matched_keyword = keyword
                            break
                    
                    if matched_keyword:
                        self.log_auto_update(f"   🎯 分类结果: 匹配关键词 '{matched_keyword}' → {target_url.split('/')[-1]}")
                    else:
                        self.log_auto_update(f"   🎯 分类结果: 配置关键词 {matched_keywords} → {target_url.split('/')[-1]}")
                else:
                    self.log_auto_update(f"   🎯 分类结果: 无匹配关键词 → 默认位置 {target_url.split('/')[-1]}")
                
                self.log_auto_update(f"   📋 目标wiki_token: {target_wiki_token}")
                
                # 🔥 在目标分类子节点下检查重复文章
                self.log_auto_update(f"   🔍 步骤2: 检查目标分类子节点下是否已存在同名文章...")
                if target_wiki_token:
                    self.log_auto_update(f"   📂 检查位置: {target_wiki_token} (分类子节点)")
                    wiki_exists = uploader.feishu_client.check_file_exists_in_wiki(
                        uploader.space_id, 
                        title, 
                        target_wiki_token  # 在分类子节点下检查是否有同名文章
                    )
                else:
                    # 如果无法解析目标token，使用默认位置检查
                    self.log_auto_update(f"   ⚠️ 无法解析目标token，使用默认位置检查...")
                    default_wiki_token = self.default_wiki_location.split("/wiki/")[-1] if "/wiki/" in self.default_wiki_location else None
                    if default_wiki_token:
                        self.log_auto_update(f"   📂 检查位置: {default_wiki_token} (默认位置)")
                        wiki_exists = uploader.feishu_client.check_file_exists_in_wiki(
                            uploader.space_id, 
                            title, 
                            default_wiki_token
                        )
                    else:
                        # 最后回退到父节点检查
                        self.log_auto_update(f"   ⚠️ 默认位置也无法解析，回退到父节点检查...")
                        self.log_auto_update(f"   📂 检查位置: {uploader.parent_wiki_token} (父节点)")
                        wiki_exists = uploader.feishu_client.check_file_exists_in_wiki(
                            uploader.space_id, 
                            title, 
                            uploader.parent_wiki_token
                        )
                
                if wiki_exists:
                    self.log_auto_update(f"   📋 检测结果: 目标位置已存在同名文档 '{title}'，跳过")
                    duplicate_count += 1
                else:
                    self.log_auto_update(f"   ✅ 检测结果: 目标位置不存在同名文档，加入下载队列")
                    final_articles.append(article)
                
                self.log_auto_update("")  # 空行分隔
            
            # 清理uploader
            uploader.cleanup()
            
            self.log_auto_update(f"📊 智能重复检测汇总:")
            self.log_auto_update(f"   📥 收集文章: {len(time_filtered_articles)} 篇")
            self.log_auto_update(f"   📋 已存在: {duplicate_count} 篇 (目标位置已有同名文档)")
            self.log_auto_update(f"   🆕 待处理: {len(final_articles)} 篇 (新文章需要下载上传)")
            self.log_auto_update("")
            
            return final_articles
            
        except Exception as e:
            self.log_auto_update(f"❌ 收集新文章失败: {e}")
            return []
    
    def auto_download_and_upload_articles(self, articles):
        """自动下载并上传文章 - 支持智能分类"""
        success_count = 0
        
        # 🔥 修复：如果没有文章需要处理，直接返回
        if not articles:
            self.log_auto_update(f"📋 没有新文章需要下载，所有文章都已存在于知识库中")
            self.log_auto_update(f"   ✅ 智能重复检测已过滤掉所有重复文章")
            self.log_auto_update(f"   💡 这是正常情况，表明知识库内容是最新的")
            return 0  # 返回0表示成功完成（没有需要处理的文章）
        
        try:
            from integrated_auto_download_uploader import IntegratedAutoUploader
            
            # 创建整合版上传器
            uploader = IntegratedAutoUploader(self.feishu_app_id, self.feishu_app_secret)
            
            self.log_auto_update(f"📥 开始处理 {len(articles)} 篇需要下载的新文章:")
            
            for i, article in enumerate(articles, 1):
                try:
                    title = article.get('title', f'article_{i}')
                    link = article.get('link', '')
                    
                    if not link:
                        self.log_auto_update(f"⚠️ [{i}/{len(articles)}] 跳过无链接文章: {title}")
                        continue
                    
                    self.log_auto_update(f"📥 [{i}/{len(articles)}] 开始处理文章: {title}")
                    self.log_auto_update(f"   🔗 文章链接: {link[:60]}...")
                    
                    # 🆕 使用智能分类处理流程
                    result = self._process_article_with_smart_classification(uploader, link, title, i, len(articles))
                    
                    if result:
                        success_count += 1
                        self.log_auto_update(f"✅ [{i}/{len(articles)}] 文章处理成功: {title}")
                        self.log_auto_update(f"   🎉 已成功下载并上传到飞书知识库")
                    else:
                        self.log_auto_update(f"❌ [{i}/{len(articles)}] 文章处理失败: {title}")
                        self.log_auto_update(f"   💔 下载或上传过程中发生错误")
                    
                    # 添加延迟避免频率限制
                    import time
                    time.sleep(3)
                    
                except Exception as e:
                    self.log_auto_update(f"❌ [{i}/{len(articles)}] 处理异常: {e}")
            
            uploader.cleanup()
            
            # 🔥 修复：更准确的处理结果汇总
            self.log_auto_update(f"📊 文章处理汇总:")
            self.log_auto_update(f"   📥 预计处理: {len(articles)} 篇 (智能重复检测后的新文章)")
            self.log_auto_update(f"   ✅ 成功处理: {success_count} 篇")
            if len(articles) - success_count > 0:
                self.log_auto_update(f"   ❌ 处理失败: {len(articles) - success_count} 篇")
            
        except Exception as e:
            self.log_auto_update(f"❌ 批量处理失败: {e}")
        
        return success_count
    
    def _process_article_with_smart_classification(self, uploader, url: str, title: str, current: int, total: int) -> bool:
        """处理单篇文章的智能分类流程（已通过前置重复检测）"""
        try:
            # 步骤1: 下载文件
            self.log_auto_update(f"   📥 步骤1: 开始下载微信文章...")
            temp_file_path = uploader.download_article(url, 'pdf')
            
            # 🔥 修复：正确处理跳过下载的情况
            if temp_file_path == "DUPLICATE_SKIPPED":
                self.log_auto_update(f"   📋 步骤1结果: 检测到云文档重复文件，跳过下载")
                self.log_auto_update(f"   ✅ 这是正常情况，说明文档已存在于云文档中")
                return True  # 跳过是成功的状态
            
            if not temp_file_path:
                self.log_auto_update(f"   ❌ 步骤1失败: 文件下载失败，无法获取文章内容")
                return False
            
            filename = temp_file_path.name
            actual_title = temp_file_path.stem  # 使用实际的文件名作为标题
            
            self.log_auto_update(f"   ✅ 步骤1成功: 文件下载完成")
            self.log_auto_update(f"      📄 文件名: {filename}")
            self.log_auto_update(f"      📝 提取标题: {actual_title}")
            
            # 步骤2: 智能分类分析（基于实际下载的文件标题）
            self.log_auto_update(f"   🧠 步骤2: 执行智能分类分析...")
            target_location = self.find_target_wiki_location(actual_title)
            target_url = target_location.get("wiki_url", self.default_wiki_location)
            as_subpage = target_location.get("as_subpage", True)
            
            # 提取匹配的关键词（用于日志显示）
            matched_keywords = target_location.get("keywords", [])
            if matched_keywords:
                # 找到实际匹配的关键词
                matched_keyword = None
                title_lower = actual_title.lower()
                for keyword in matched_keywords:
                    if keyword.lower() in title_lower:
                        matched_keyword = keyword
                        break
                
                if matched_keyword:
                    self.log_auto_update(f"   ✅ 步骤2成功: 匹配关键词 '{matched_keyword}'")
                else:
                    self.log_auto_update(f"   ✅ 步骤2成功: 配置关键词 {matched_keywords}")
            else:
                self.log_auto_update(f"   ✅ 步骤2成功: 无匹配关键词，使用默认位置")
            
            self.log_auto_update(f"      🎯 目标位置: {target_url.split('/')[-1]}")
            self.log_auto_update(f"      📄 作为子页面: {'是' if as_subpage else '否'}")
            
            # 🆕 跳过重复检测（已在前置阶段完成）
            self.log_auto_update(f"   ⏭️ 跳过重复检测（已在收集阶段完成智能重复检测）")
            
            # 步骤3: 上传到云文档
            self.log_auto_update(f"   ☁️ 步骤3: 上传文件到飞书云文档...")
            file_token = uploader.upload_to_drive(temp_file_path)
            
            if file_token == "DUPLICATE":
                self.log_auto_update(f"   📋 步骤3结果: 云文档中已存在相同文件，跳过上传")
                return True
            
            if not file_token:
                self.log_auto_update(f"   ❌ 步骤3失败: 云文档上传失败，无法获取文件token")
                return False
            
            self.log_auto_update(f"   ✅ 步骤3成功: 文件已上传到云文档")
            self.log_auto_update(f"      🏷️ 文件token: {file_token}")
            
            # 步骤4: 智能转移到目标知识库位置
            self.log_auto_update(f"   📚 步骤4: 转移文档到目标知识库位置...")
            wiki_result = self._smart_move_to_wiki(uploader, file_token, filename, target_location)
            
            if wiki_result:
                if wiki_result.startswith("75"):  # task_id格式
                    self.log_auto_update(f"   ✅ 步骤4成功: 转移任务已提交到飞书后台")
                    self.log_auto_update(f"      ⏳ 任务ID: {wiki_result}")
                    self.log_auto_update(f"      💡 飞书正在后台处理转移，请稍后在知识库中查看")
                else:  # wiki_token格式
                    wiki_url = f"https://thedream.feishu.cn/wiki/{wiki_result}"
                    self.log_auto_update(f"   ✅ 步骤4成功: 文档已转移到知识库")
                    self.log_auto_update(f"      📖 文档链接: {wiki_url}")
                
                self.log_auto_update(f"      🎯 目标位置: {target_url.split('/')[-1]}")
                return True
            else:
                self.log_auto_update(f"   ❌ 步骤4失败: 转移到知识库失败")
                return False
                
        except Exception as e:
            self.log_auto_update(f"   ❌ [{current}/{total}] 智能分类处理异常: {e}")
            return False
    
    def update_last_update_date(self, new_date):
        """更新最后更新日期"""
        self.last_update_date = new_date
        self.last_update_date_var.set(new_date)
        self.save_auto_update_settings()
        self.log_auto_update(f"📅 更新日期节点: {new_date}")


def main():
    """启动GUI应用"""
    try:
        print("🚀 启动微信文章下载工具GUI...")
        
        root = tk.Tk()
        print("✅ tkinter根窗口创建成功")
        
        app = WechatDownloaderGUI(root)
        print("✅ GUI应用初始化成功")
        
        # 设置关闭事件
        root.protocol("WM_DELETE_WINDOW", app.on_closing)
        
        print("🎯 启动GUI主循环...")
        # 启动主循环
        root.mainloop()
        
        print("👋 GUI应用已关闭")
        
    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        print("💡 请确保安装了所有依赖包:")
        print("   pip install selenium beautifulsoup4 requests loguru")
        input("按回车键退出...")
    except Exception as e:
        print(f"❌ GUI启动失败: {e}")
        import traceback
        print("📋 详细错误信息:")
        traceback.print_exc()
        input("按回车键退出...")


if __name__ == "__main__":
    main() 