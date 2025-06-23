#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信公众号文章链接批量获取工具
基于微信公众平台后台编辑功能的搜索API实现
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import requests
import json
import csv
import time
import threading
import tempfile
import base64
import subprocess
from datetime import datetime, timedelta
from urllib.parse import urlencode, parse_qs, urlparse
import re
import os
from loguru import logger
from pathlib import Path
import queue
import webbrowser


class WeChatLinkCollector:
    """微信公众号文章链接收集器"""
    
    def __init__(self):
        """初始化"""
        self.session = requests.Session()
        self.token = ""
        self.cookies = {}
        self.user_info = {}
        self.session_id = ""
        
        # 频率控制
        self.request_interval = 2.0  # 请求间隔（秒）
        self.last_request_time = 0
        
        # 数据存储
        self.collected_articles = []
        self.current_account = None
        
        # GUI相关
        self.root = None
        self.setup_gui()
        
        logger.info("🚀 微信公众号文章链接收集器初始化完成")
    
    def setup_gui(self):
        """设置GUI界面"""
        self.root = tk.Tk()
        self.root.title("微信公众号文章链接收集器 v1.0")
        self.root.geometry("1000x700")
        self.root.resizable(True, True)
        
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # 标题
        title_label = ttk.Label(main_frame, text="🔗 微信公众号文章链接收集器", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        self.create_login_section(main_frame)
        self.create_search_section(main_frame)
        self.create_results_section(main_frame)
        self.create_export_section(main_frame)
        self.create_log_section(main_frame)
        
        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, 
                              relief=tk.SUNKEN, anchor=tk.W)
        status_bar.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
        
        logger.info("✅ GUI界面创建完成")
    
    def create_login_section(self, parent):
        """创建登录区域"""
        # 登录框架
        login_frame = ttk.LabelFrame(parent, text="1. 微信公众号登录", padding="10")
        login_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        login_frame.columnconfigure(1, weight=1)
        
        # 登录状态
        self.login_status_var = tk.StringVar(value="未登录")
        ttk.Label(login_frame, text="登录状态:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.login_status_label = ttk.Label(login_frame, textvariable=self.login_status_var, 
                                           foreground="red")
        self.login_status_label.grid(row=0, column=1, sticky=tk.W)
        
        # 登录按钮
        self.login_btn = ttk.Button(login_frame, text="🚀 开始登录", command=self.start_login)
        self.login_btn.grid(row=0, column=2, padx=(10, 0))
        
        # 重新登录按钮
        self.retry_btn = ttk.Button(login_frame, text="🔄 重新登录", command=self.retry_login)
        self.retry_btn.grid(row=0, column=3, padx=(5, 0))
        
        # 二维码显示区域
        self.qr_frame = ttk.Frame(login_frame)
        self.qr_frame.grid(row=1, column=0, columnspan=3, pady=(10, 0))
        
        self.qr_label = ttk.Label(self.qr_frame, text="点击'开始登录'获取二维码")
        self.qr_label.pack()
    
    def create_search_section(self, parent):
        """创建搜索区域"""
        search_frame = ttk.LabelFrame(parent, text="2. 搜索公众号", padding="10")
        search_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        search_frame.columnconfigure(1, weight=1)
        search_frame.rowconfigure(1, weight=1)
        
        # 搜索输入
        ttk.Label(search_frame, text="搜索关键词:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=30)
        self.search_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        self.search_entry.bind('<Return>', lambda e: self.search_accounts())
        
        self.search_btn = ttk.Button(search_frame, text="🔍 搜索", command=self.search_accounts)
        self.search_btn.grid(row=0, column=2)
        
        # 搜索结果列表
        result_frame = ttk.Frame(search_frame)
        result_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(0, weight=1)
        
        # 创建Treeview显示搜索结果
        columns = ('nickname', 'alias', 'signature')
        self.accounts_tree = ttk.Treeview(result_frame, columns=columns, show='tree headings', height=8)
        
        self.accounts_tree.heading('#0', text='序号')
        self.accounts_tree.heading('nickname', text='公众号名称')
        self.accounts_tree.heading('alias', text='微信号')
        self.accounts_tree.heading('signature', text='签名')
        
        self.accounts_tree.column('#0', width=50)
        self.accounts_tree.column('nickname', width=200)
        self.accounts_tree.column('alias', width=150)
        self.accounts_tree.column('signature', width=300)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.accounts_tree.yview)
        self.accounts_tree.configure(yscrollcommand=scrollbar.set)
        
        self.accounts_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # 绑定选择事件
        self.accounts_tree.bind('<<TreeviewSelect>>', self.on_account_select)
    
    def create_results_section(self, parent):
        """创建结果区域"""
        results_frame = ttk.LabelFrame(parent, text="3. 文章获取设置", padding="10")
        results_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        results_frame.columnconfigure(1, weight=1)
        
        # 当前选中的公众号
        ttk.Label(results_frame, text="选中公众号:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.selected_account_var = tk.StringVar(value="未选择")
        ttk.Label(results_frame, textvariable=self.selected_account_var, 
                 foreground="blue").grid(row=0, column=1, sticky=tk.W)
        
        # 获取设置
        settings_frame = ttk.Frame(results_frame)
        settings_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
        
        # 数量限制
        ttk.Label(settings_frame, text="获取数量:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.limit_var = tk.StringVar(value="100")
        limit_entry = ttk.Entry(settings_frame, textvariable=self.limit_var, width=10)
        limit_entry.grid(row=0, column=1, padx=(0, 20))
        
        # 获取按钮
        self.collect_btn = ttk.Button(settings_frame, text="📥 获取文章链接", 
                                     command=self.collect_articles)
        self.collect_btn.grid(row=0, column=2)
        
        # 日期范围设置 - 第二行
        date_frame = ttk.Frame(settings_frame)
        date_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
        
        # 起始日期
        ttk.Label(date_frame, text="起始日期:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.start_date_var = tk.StringVar(value=(datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"))
        start_date_entry = ttk.Entry(date_frame, textvariable=self.start_date_var, width=12)
        start_date_entry.grid(row=0, column=1, padx=(0, 20))
        
        # 结束日期
        ttk.Label(date_frame, text="结束日期:").grid(row=0, column=2, sticky=tk.W, padx=(0, 10))
        self.end_date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        end_date_entry = ttk.Entry(date_frame, textvariable=self.end_date_var, width=12)
        end_date_entry.grid(row=0, column=3, padx=(0, 20))
        
        # 日期格式说明
        ttk.Label(date_frame, text="(格式: YYYY-MM-DD)", 
                 foreground="gray").grid(row=0, column=4, sticky=tk.W)
        
        # 快捷日期设置按钮 - 第三行
        quick_date_frame = ttk.Frame(settings_frame)
        quick_date_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(5, 0))
        
        ttk.Label(quick_date_frame, text="快捷设置:", 
                 foreground="gray").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        
        ttk.Button(quick_date_frame, text="最近7天", 
                  command=lambda: self._set_date_range(7)).grid(row=0, column=1, padx=(0, 5))
        ttk.Button(quick_date_frame, text="最近30天", 
                  command=lambda: self._set_date_range(30)).grid(row=0, column=2, padx=(0, 5))
        ttk.Button(quick_date_frame, text="最近90天", 
                  command=lambda: self._set_date_range(90)).grid(row=0, column=3, padx=(0, 5))
        ttk.Button(quick_date_frame, text="今天", 
                  command=lambda: self._set_date_range(0)).grid(row=0, column=4, padx=(0, 5))
        
        # 进度显示
        self.progress_var = tk.StringVar(value="")
        ttk.Label(results_frame, textvariable=self.progress_var).grid(row=2, column=0, columnspan=3, 
                                                                     sticky=tk.W, pady=(10, 0))
    
    def create_export_section(self, parent):
        """创建导出区域"""
        export_frame = ttk.LabelFrame(parent, text="4. 导出设置", padding="10")
        export_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 统计信息
        self.stats_var = tk.StringVar(value="已收集: 0 篇文章")
        ttk.Label(export_frame, textvariable=self.stats_var, 
                 font=("Arial", 12, "bold")).grid(row=0, column=0, sticky=tk.W, padx=(0, 20))
        
        # 导出按钮
        export_buttons_frame = ttk.Frame(export_frame)
        export_buttons_frame.grid(row=0, column=1, sticky=tk.E)
        
        ttk.Button(export_buttons_frame, text="📄 导出CSV", 
                  command=lambda: self.export_data('csv')).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(export_buttons_frame, text="📋 导出JSON", 
                  command=lambda: self.export_data('json')).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(export_buttons_frame, text="📝 导出TXT", 
                  command=lambda: self.export_data('txt')).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(export_buttons_frame, text="📁 打开文件夹", 
                  command=self.open_output_folder).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(export_buttons_frame, text="🗑️ 清空数据", 
                  command=self.clear_data).pack(side=tk.LEFT)
    
    def create_log_section(self, parent):
        """创建日志区域"""
        log_frame = ttk.LabelFrame(parent, text="5. 运行日志", padding="10")
        log_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        # 日志文本框
        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, wrap=tk.WORD)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        parent.rowconfigure(5, weight=1)
    
    def log_message(self, message, level="INFO"):
        """添加日志消息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END)
        self.root.update()
        
        # 同时输出到控制台
        if level == "ERROR":
            logger.error(message)
        elif level == "WARNING":
            logger.warning(message)
        else:
            logger.info(message)
    
    def update_status(self, status):
        """更新状态栏"""
        self.status_var.set(status)
        self.root.update()
    
    def _wait_for_rate_limit(self):
        """等待以避免触发频率限制"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.request_interval:
            wait_time = self.request_interval - time_since_last
            self.log_message(f"⏱️ 等待 {wait_time:.1f} 秒以避免频率限制")
            time.sleep(wait_time)
        
        self.last_request_time = time.time()
    
    def start_login(self):
        """开始登录流程"""
        self.log_message("🚀 开始微信公众号登录流程")
        self.login_btn.config(state='disabled', text="登录中...")
        self.retry_btn.config(state='disabled')
        
        # 清理二维码区域
        for widget in self.qr_frame.winfo_children():
            widget.destroy()
        self.qr_label = ttk.Label(self.qr_frame, text="正在获取二维码...")
        self.qr_label.pack()
        
        # 在新线程中执行登录
        threading.Thread(target=self._login_worker, daemon=True).start()
    
    def retry_login(self):
        """重新登录"""
        self.log_message("🔄 重新开始登录流程")
        
        # 重置状态
        self.token = ""
        self.cookies = {}
        self.session_id = ""
        self.login_status_var.set("未登录")
        self.login_status_label.config(foreground="red")
        
        # 开始新的登录
        self.start_login()
    
    def _login_worker(self):
        """登录工作线程"""
        try:
            # 第一步：启动登录会话
            self.log_message("📱 启动登录会话...")
            self.session_id = str(int(time.time() * 1000)) + str(int(time.time() * 100) % 100)
            
            # 模拟浏览器请求头
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': 'https://mp.weixin.qq.com/',
                'Origin': 'https://mp.weixin.qq.com'
            }
            self.session.headers.update(headers)
            
            # 启动登录
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
                    self.log_message("✅ 登录会话启动成功")
                    self._show_qrcode()
                    self._start_scan_check()
                else:
                    raise Exception(f"启动登录失败: {result}")
            else:
                raise Exception(f"请求失败: {response.status_code}")
                
        except Exception as e:
            self.log_message(f"❌ 登录启动失败: {e}", "ERROR")
            self.login_btn.config(state='normal', text="🚀 开始登录")
            self.retry_btn.config(state='normal')
    
    def _show_qrcode(self):
        """显示二维码"""
        try:
            # 清空之前的显示
            for widget in self.qr_frame.winfo_children():
                widget.destroy()
            
            # 构建二维码URL并下载
            qr_url = f"https://mp.weixin.qq.com/cgi-bin/scanloginqrcode?action=getqrcode&random={int(time.time())}"
            
            # 使用session下载二维码图片
            self.log_message("📥 正在下载二维码图片...")
            response = self.session.get(qr_url)
            
            if response.status_code == 200 and response.content:
                # 检查是否为图片数据
                if response.headers.get('content-type', '').startswith('image'):
                    # 将图片数据转换为base64
                    qr_base64 = base64.b64encode(response.content).decode('utf-8')
                    self.log_message(f"✅ 二维码下载成功，大小: {len(response.content)} 字节")
                    
                    # 创建HTML页面显示二维码
                    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>微信公众号登录二维码</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            text-align: center;
            padding: 50px;
            background-color: #f5f5f5;
            margin: 0;
        }}
        .container {{
            background: white;
            border-radius: 10px;
            padding: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            display: inline-block;
            max-width: 400px;
        }}
        h1 {{
            color: #333;
            margin-bottom: 20px;
            font-size: 24px;
        }}
        .qr-code {{
            margin: 20px 0;
            padding: 20px;
            border: 2px solid #eee;
            border-radius: 10px;
            background: #fafafa;
        }}
        .qr-code img {{
            width: 200px;
            height: 200px;
            border: none;
        }}
        .instructions {{
            color: #666;
            font-size: 16px;
            margin-top: 20px;
            line-height: 1.5;
        }}
        .status {{
            margin-top: 15px;
            padding: 10px;
            background: #e3f2fd;
            border-radius: 5px;
            color: #1976d2;
            font-size: 14px;
        }}
        .info {{
            margin-top: 10px;
            padding: 8px;
            background: #f3e5f5;
            border-radius: 5px;
            color: #7b1fa2;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔗 微信公众号登录</h1>
        <div class="qr-code">
            <img src="data:image/png;base64,{qr_base64}" alt="微信登录二维码" />
        </div>
        <div class="instructions">
            📱 请使用微信扫描上方二维码登录<br>
            需要有公众号管理权限的微信账号
        </div>
        <div class="status" id="status">
            ⏳ 等待扫码...
        </div>
        <div class="info">
            💡 提示：如需刷新二维码，请返回程序重新点击登录按钮
        </div>
    </div>
    
    <script>
        let refreshCount = 0;
        const statusDiv = document.getElementById('status');
        
        function updateStatus() {{
            refreshCount++;
            if (refreshCount < 120) {{
                setTimeout(() => {{
                    statusDiv.innerHTML = '⏳ 等待扫码... (' + Math.floor(refreshCount/4) + 's)';
                    updateStatus();
                }}, 1000);
            }} else {{
                statusDiv.innerHTML = '⏰ 二维码可能已过期，请返回程序重新获取';
                statusDiv.style.background = '#fff3e0';
                statusDiv.style.color = '#f57c00';
            }}
        }}
        
        updateStatus();
    </script>
</body>
</html>
"""
                    
                else:
                    # 不是图片数据，可能是错误响应
                    self.log_message(f"⚠️ 响应不是图片格式: {response.headers.get('content-type')}")
                    self.log_message(f"响应内容: {response.text[:200]}")
                    raise Exception("获取的不是二维码图片数据")
            else:
                raise Exception(f"下载二维码失败: {response.status_code}")
            
            # 保存HTML文件
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
                f.write(html_content)
                temp_html_path = f.name
            
            self.temp_qr_html = temp_html_path
            
            # 创建GUI元素
            info_label = ttk.Label(self.qr_frame, text="📱 二维码已生成", font=("Arial", 12))
            info_label.pack(pady=5)
            
            link_label = ttk.Label(self.qr_frame, text="点击此处打开二维码页面", 
                                  foreground="blue", cursor="hand2", font=("Arial", 11))
            link_label.pack(pady=10)
            
            def open_qrcode():
                if hasattr(self, 'temp_qr_html'):
                    webbrowser.open(f'file://{os.path.abspath(self.temp_qr_html)}')
                    self.log_message("🔗 已在浏览器中打开二维码页面，请用微信扫描")
                else:
                    self.log_message("❌ 二维码文件未生成，请重试")
            
            link_label.bind("<Button-1>", lambda e: open_qrcode())
            
            # 添加状态信息
            status_label = ttk.Label(self.qr_frame, text=f"状态: 图片已下载 ({len(response.content)} 字节)", 
                                   font=("Courier", 8), foreground="green")
            status_label.pack(pady=5)
            
            self.log_message("📱 二维码已生成，请用微信扫描登录")
            
        except Exception as e:
            self.log_message(f"❌ 二维码生成失败: {e}", "ERROR")
    
    def _start_scan_check(self):
        """开始检查扫码状态"""
        self.log_message("👀 开始检查扫码状态...")
        self._check_scan_status()
    
    def _check_scan_status(self):
        """检查扫码状态"""
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
                    # 如果不是JSON格式，可能是HTML或其他格式
                    self.log_message(f"⚠️ 响应不是JSON格式: {response.text[:200]}", "WARNING")
                    self.root.after(1500, self._check_scan_status)
                    return
                
                # 调试信息
                self.log_message(f"🔍 扫码检查响应: {result}")
                
                if result.get('base_resp', {}).get('ret') == 0:
                    status = result.get('status', 0)
                    
                    self.log_message(f"🔍 扫码状态: {status}")
                    
                    if status == 1:
                        # 登录成功，可以获取用户列表
                        self.log_message("🎉 扫码登录成功!")
                        self._complete_login()
                    elif status == 4:
                        # 已扫码，等待用户确认
                        acct_size = result.get('acct_size', 0)
                        if acct_size == 1:
                            self.log_message("📱 已扫码，请在微信中确认登录")
                        elif acct_size > 1:
                            self.log_message("📱 已扫码，请在微信中选择账号登录")
                        else:
                            self.log_message("⚠️ 该微信没有关联的公众号账号")
                        self.root.after(1500, self._check_scan_status)
                    elif status == 2:
                        # 二维码过期
                        self.log_message("⏰ 二维码已过期，请重新获取")
                        self.login_btn.config(state='normal', text="🚀 开始登录")
                        return
                    elif status == 3:
                        # 取消登录
                        self.log_message("❌ 用户取消登录")
                        self.login_btn.config(state='normal', text="🚀 开始登录")
                        return
                    elif status == 0:
                        # 等待扫码
                        self.root.after(1500, self._check_scan_status)
                    else:
                        self.log_message(f"⚠️ 未知登录状态: {status}")
                        self.root.after(1500, self._check_scan_status)
                else:
                    error_msg = result.get('base_resp', {}).get('err_msg', '未知错误')
                    self.log_message(f"❌ 扫码状态检查失败: {error_msg}", "ERROR")
                    self.login_btn.config(state='normal', text="🚀 开始登录")
            else:
                self.log_message(f"❌ 检查扫码状态请求失败: {response.status_code}", "ERROR")
                self.login_btn.config(state='normal', text="🚀 开始登录")
                
        except Exception as e:
            self.log_message(f"❌ 检查扫码状态出错: {e}", "ERROR")
            self.login_btn.config(state='normal', text="🚀 开始登录")
    
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
                    parsed_url = urlparse(f"http://localhost{redirect_url}")
                    self.token = parse_qs(parsed_url.query).get('token', [''])[0]
                    
                    if self.token:
                        # 保存cookies
                        self.cookies = dict(self.session.cookies)
                        
                        # 获取用户信息
                        self._get_user_info()
                        
                        self.login_status_var.set("✅ 已登录")
                        self.login_status_label.config(foreground="green")
                        self.login_btn.config(state='normal', text="✅ 已登录")
                        self.retry_btn.config(state='normal')
                        
                        self.log_message("🎉 登录完成，可以开始搜索公众号")
                        return
                
            raise Exception("获取登录token失败")
            
        except Exception as e:
            self.log_message(f"❌ 完成登录失败: {e}", "ERROR")
            self.login_btn.config(state='normal', text="🚀 开始登录")
            self.retry_btn.config(state='normal')
    
    def _get_user_info(self):
        """获取用户信息"""
        try:
            info_url = f"https://mp.weixin.qq.com/cgi-bin/loginpage?token={self.token}&lang=zh_CN"
            response = self.session.get(info_url)
            
            if response.status_code == 200:
                # 这里可以解析用户信息，暂时跳过
                self.log_message("✅ 用户信息获取成功")
            
        except Exception as e:
            self.log_message(f"⚠️ 获取用户信息失败: {e}", "WARNING")
    
    def search_accounts(self):
        """搜索公众号"""
        if not self.token:
            messagebox.showerror("错误", "请先登录微信公众号")
            return
        
        keyword = self.search_var.get().strip()
        if not keyword:
            messagebox.showerror("错误", "请输入搜索关键词")
            return
        
        self.log_message(f"🔍 搜索公众号: {keyword}")
        self.search_btn.config(state='disabled', text="搜索中...")
        
        # 在新线程中执行搜索
        threading.Thread(target=self._search_worker, args=(keyword,), daemon=True).start()
    
    def _search_worker(self, keyword):
        """搜索工作线程"""
        try:
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
                    self._display_search_results(accounts)
                    self.log_message(f"✅ 找到 {len(accounts)} 个公众号")
                else:
                    error_msg = result.get('base_resp', {}).get('err_msg', '未知错误')
                    if 'freq control' in error_msg:
                        self.log_message("❌ 触发频率限制，请稍后再试", "ERROR")
                    else:
                        self.log_message(f"❌ 搜索失败: {error_msg}", "ERROR")
            else:
                self.log_message(f"❌ 搜索请求失败: {response.status_code}", "ERROR")
                
        except Exception as e:
            self.log_message(f"❌ 搜索出错: {e}", "ERROR")
        finally:
            self.search_btn.config(state='normal', text="🔍 搜索")
    
    def _display_search_results(self, accounts):
        """显示搜索结果"""
        # 清空现有结果
        for item in self.accounts_tree.get_children():
            self.accounts_tree.delete(item)
        
        # 添加新结果
        for i, account in enumerate(accounts, 1):
            self.accounts_tree.insert('', 'end', text=str(i), 
                                    values=(
                                        account.get('nickname', ''),
                                        account.get('alias', ''),
                                        account.get('signature', '')[:50] + '...' if len(account.get('signature', '')) > 50 else account.get('signature', '')
                                    ),
                                    tags=(json.dumps(account),))
    
    def on_account_select(self, event):
        """公众号选择事件"""
        selection = self.accounts_tree.selection()
        if selection:
            item = self.accounts_tree.item(selection[0])
            account_data = json.loads(item['tags'][0])
            
            self.current_account = account_data
            self.selected_account_var.set(f"{account_data.get('nickname', '')} ({account_data.get('alias', '')})")
            self.log_message(f"✅ 已选择公众号: {account_data.get('nickname', '')}")
    
    def _set_date_range(self, days):
        """设置日期范围"""
        today = datetime.now()
        
        if days == 0:  # 今天
            start_date = today
            end_date = today
        else:  # 最近N天
            start_date = today - timedelta(days=days)
            end_date = today
        
        self.start_date_var.set(start_date.strftime("%Y-%m-%d"))
        self.end_date_var.set(end_date.strftime("%Y-%m-%d"))
        
        self.log_message(f"📅 已设置日期范围: {start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}")
    
    def collect_articles(self):
        """收集文章链接"""
        if not self.current_account:
            messagebox.showerror("错误", "请先选择一个公众号")
            return
        
        try:
            limit = int(self.limit_var.get())
            
            # 解析日期
            start_date_str = self.start_date_var.get().strip()
            end_date_str = self.end_date_var.get().strip()
            
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
            
            if start_date > end_date:
                messagebox.showerror("错误", "起始日期不能晚于结束日期")
                return
                
        except ValueError as e:
            messagebox.showerror("错误", "请输入有效的数字和日期格式 (YYYY-MM-DD)")
            return
        
        # 清空之前收集的文章
        self.collected_articles.clear()
        
        self.log_message(f"📥 开始收集文章链接 (最多{limit}篇，{start_date_str} 至 {end_date_str})")
        self.collect_btn.config(state='disabled', text="收集中...")
        
        # 在新线程中执行收集
        threading.Thread(target=self._collect_worker, args=(limit, start_date, end_date), daemon=True).start()
    
    def _parse_articles_from_response(self, result):
        """从API响应中解析文章列表"""
        articles = []
        
        try:
            # 获取 publish_page 字段
            publish_page_str = result.get('publish_page', '')
            if not publish_page_str:
                return articles
            
            # 解析 JSON 字符串
            publish_page = json.loads(publish_page_str)
            publish_list = publish_page.get('publish_list', [])
            
            for publish_item in publish_list:
                # 解析每个发布项的信息
                publish_info_str = publish_item.get('publish_info', '')
                if not publish_info_str:
                    continue
                
                publish_info = json.loads(publish_info_str)
                appmsgex_list = publish_info.get('appmsgex', [])
                
                # 提取每篇文章
                for appmsg in appmsgex_list:
                    # 处理链接中的转义字符
                    link = appmsg.get('link', '').replace('\\/', '/')
                    
                    article = {
                        'title': appmsg.get('title', ''),
                        'link': link,
                        'author_name': appmsg.get('author_name', ''),
                        'digest': appmsg.get('digest', ''),
                        'update_time': appmsg.get('update_time', 0),
                        'create_time': appmsg.get('create_time', 0)
                    }
                    articles.append(article)
            
        except Exception as e:
            self.log_message(f"⚠️ 解析文章列表出错: {e}", "WARNING")
        
        return articles
    
    def _collect_worker(self, limit, start_date, end_date):
        """收集工作线程"""
        try:
            fakeid = self.current_account.get('fakeid', '')
            if not fakeid:
                raise Exception("无法获取公众号ID")
            
            collected_count = 0
            begin = 0
            page_size = 20
            
            # 计算时间范围（注意：end_date 要包含整天，所以加1天再减1秒）
            start_timestamp = int(start_date.timestamp())
            end_timestamp = int((end_date + timedelta(days=1) - timedelta(seconds=1)).timestamp())
            
            # 添加调试信息
            self.log_message(f"🕐 时间范围: {start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}")
            self.log_message(f"🕐 时间戳范围: {start_timestamp} 至 {end_timestamp}")
            
            # 用于收集符合时间范围的文章
            filtered_articles = []
            
            while True:  # 持续获取直到没有更多文章或达到时间限制
                self._wait_for_rate_limit()
                
                self.progress_var.set(f"正在获取第 {begin//page_size + 1} 页，已收集 {collected_count} 篇")
                
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
                    
                    # 调试信息 - 简化日志输出
                    self.log_message(f"🔍 API响应状态: {result.get('base_resp', {})}")
                    
                    if result.get('base_resp', {}).get('ret') == 0:
                        # 解析文章列表
                        articles = self._parse_articles_from_response(result)
                        
                        # 调试信息
                        self.log_message(f"📋 获取到 {len(articles)} 篇文章")
                        if articles:
                            first_article = articles[0]
                            first_article_time = datetime.fromtimestamp(first_article.get('update_time', 0)).strftime('%Y-%m-%d %H:%M:%S')
                            self.log_message(f"📝 第一篇文章: {first_article.get('title', '')} (时间: {first_article_time})")
                        
                        if not articles:
                            self.log_message("✅ 已获取所有文章")
                            break
                        
                        # 检查是否所有文章都早于起始时间（按时间倒序，如果第一篇都早于起始时间，则可以停止）
                        first_article_time = articles[0].get('update_time', 0) if articles else 0
                        if first_article_time < start_timestamp:
                            self.log_message(f"✅ 已达到起始日期限制 ({start_date.strftime('%Y-%m-%d')})")
                            break
                        
                        # 过滤时间范围内的文章
                        for article in articles:
                            article_time = article.get('update_time', 0)
                            article_date_str = datetime.fromtimestamp(article_time).strftime('%Y-%m-%d %H:%M:%S')
                            
                            # 如果文章时间早于起始时间，跳过这篇文章
                            if article_time < start_timestamp:
                                self.log_message(f"📅 跳过早于起始日期的文章: {article.get('title', '')} ({article_date_str})")
                                continue
                            
                            # 如果文章时间晚于结束时间，跳过这篇文章
                            if article_time > end_timestamp:
                                self.log_message(f"📅 跳过晚于结束日期的文章: {article.get('title', '')} ({article_date_str})")
                                continue
                            
                            # 文章在时间范围内，添加到过滤列表
                            self.log_message(f"✅ 符合时间范围的文章: {article.get('title', '')} ({article_date_str})")
                            filtered_articles.append(article)
                        
                        begin += page_size
                        
                    else:
                        error_msg = result.get('base_resp', {}).get('err_msg', '未知错误')
                        if 'freq control' in error_msg:
                            self.log_message("❌ 触发频率限制，收集暂停", "ERROR")
                            break
                        else:
                            raise Exception(f"获取文章失败: {error_msg}")
                else:
                    raise Exception(f"请求失败: {response.status_code}")
            
            # 按时间倒序排序（最新的在前面）
            filtered_articles.sort(key=lambda x: x.get('update_time', 0), reverse=True)
            
            # 应用数量限制
            final_articles = filtered_articles[:limit]
            
            self.log_message(f"📊 时间范围内共有 {len(filtered_articles)} 篇文章，限制为 {limit} 篇，最终获取 {len(final_articles)} 篇")
            
            # 添加到收集列表
            for article in final_articles:
                article_info = {
                    'title': article.get('title', ''),
                    'link': article.get('link', ''),
                    'author': article.get('author_name', ''),
                    'publish_time': datetime.fromtimestamp(article.get('update_time', 0)).strftime('%Y-%m-%d %H:%M:%S'),
                    'account_name': self.current_account.get('nickname', ''),
                    'account_alias': self.current_account.get('alias', ''),
                    'digest': article.get('digest', '')
                }
                
                self.collected_articles.append(article_info)
                collected_count += 1
            
            self.log_message(f"🎉 收集完成，共获取 {collected_count} 篇文章链接")
            self.stats_var.set(f"已收集: {len(self.collected_articles)} 篇文章")
            
        except Exception as e:
            self.log_message(f"❌ 收集失败: {e}", "ERROR")
        finally:
            self.collect_btn.config(state='normal', text="📥 获取文章链接")
            self.progress_var.set("")
    
    def export_data(self, format_type):
        """导出数据"""
        if not self.collected_articles:
            messagebox.showwarning("警告", "没有可导出的数据")
            return
        
        # 确保输出目录存在
        output_dir = os.path.join(os.path.dirname(__file__), 'output', 'links')
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"wechat_articles_{timestamp}"
        
        if format_type == 'csv':
            filepath = os.path.join(output_dir, f"{filename}.csv")
            self._export_csv(filepath)
        
        elif format_type == 'json':
            filepath = os.path.join(output_dir, f"{filename}.json")
            self._export_json(filepath)
        
        elif format_type == 'txt':
            filepath = os.path.join(output_dir, f"{filename}.txt")
            self._export_txt(filepath)
    
    def _export_csv(self, filepath):
        """导出CSV格式"""
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['title', 'link', 'author', 'publish_time', 'account_name', 'account_alias', 'digest']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for article in self.collected_articles:
                    writer.writerow(article)
            
            self.log_message(f"✅ CSV导出成功: {filepath}")
            messagebox.showinfo("成功", f"CSV文件已导出到:\n{filepath}")
            
        except Exception as e:
            self.log_message(f"❌ CSV导出失败: {e}", "ERROR")
            messagebox.showerror("错误", f"导出失败: {e}")
    
    def _export_json(self, filepath):
        """导出JSON格式"""
        try:
            with open(filepath, 'w', encoding='utf-8') as jsonfile:
                json.dump(self.collected_articles, jsonfile, ensure_ascii=False, indent=2)
            
            self.log_message(f"✅ JSON导出成功: {filepath}")
            messagebox.showinfo("成功", f"JSON文件已导出到:\n{filepath}")
            
        except Exception as e:
            self.log_message(f"❌ JSON导出失败: {e}", "ERROR")
            messagebox.showerror("错误", f"导出失败: {e}")
    
    def _export_txt(self, filepath):
        """导出TXT格式(只包含链接)"""
        try:
            with open(filepath, 'w', encoding='utf-8') as txtfile:
                for article in self.collected_articles:
                    txtfile.write(f"{article['link']}\n")
            
            self.log_message(f"✅ TXT导出成功: {filepath}")
            messagebox.showinfo("成功", f"TXT文件已导出到:\n{filepath}")
            
        except Exception as e:
            self.log_message(f"❌ TXT导出失败: {e}", "ERROR")
            messagebox.showerror("错误", f"导出失败: {e}")
    
    def open_output_folder(self):
        """打开输出文件夹"""
        try:
            output_dir = os.path.join(os.path.dirname(__file__), 'output', 'links')
            os.makedirs(output_dir, exist_ok=True)
            
            # 根据操作系统打开文件夹
            if os.name == 'nt':  # Windows
                os.startfile(output_dir)
            elif os.name == 'posix':  # macOS and Linux
                subprocess.call(['open', output_dir])  # macOS
                # subprocess.call(['xdg-open', output_dir])  # Linux
            
            self.log_message(f"📁 已打开输出文件夹: {output_dir}")
            
        except Exception as e:
            self.log_message(f"❌ 无法打开文件夹: {e}", "ERROR")
            messagebox.showerror("错误", f"无法打开文件夹: {e}")
    
    def clear_data(self):
        """清空数据"""
        if messagebox.askyesno("确认", "确定要清空所有收集的数据吗？"):
            self.collected_articles.clear()
            self.stats_var.set("已收集: 0 篇文章")
            self.log_message("🗑️ 数据已清空")
    
    def run(self):
        """运行程序"""
        self.log_message("🚀 微信公众号文章链接收集器启动")
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        self.root.mainloop()
    
    def _on_closing(self):
        """窗口关闭事件处理"""
        self._cleanup()
        self.root.destroy()
    
    def _cleanup(self):
        """清理临时文件"""
        try:
            if hasattr(self, 'temp_qr_html') and os.path.exists(self.temp_qr_html):
                os.unlink(self.temp_qr_html)
                logger.info("🧹 已清理临时二维码文件")
        except Exception as e:
            logger.warning(f"⚠️ 清理临时文件失败: {e}")


def main():
    """主函数"""
    try:
        print("🚀 启动微信公众号文章链接收集器...")
        collector = WeChatLinkCollector()
        collector.run()
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 