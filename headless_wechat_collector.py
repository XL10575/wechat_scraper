#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
无头微信公众号文章收集器
适用于GitHub Actions等自动化环境
基于已保存的登录状态进行文章收集
"""

import requests
import json
import time
import pickle
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from loguru import logger
import os


class HeadlessWeChatCollector:
    """无头微信公众号文章收集器"""
    
    def __init__(self, cookies_file: str = "wechat_cookies.pkl", session_file: str = "wechat_session.json"):
        """初始化收集器
        
        Args:
            cookies_file: cookies文件路径
            session_file: 会话信息文件路径
        """
        self.cookies_file = cookies_file
        self.session_file = session_file
        self.session = requests.Session()
        self.token = ""
        self.user_info = {}
        
        # 频率控制
        self.request_interval = 2.0
        self.last_request_time = 0
        
        logger.info("🚀 无头微信文章收集器初始化完成")
    
    def load_session(self) -> bool:
        """加载已保存的登录会话"""
        try:
            # 加载cookies
            if os.path.exists(self.cookies_file):
                with open(self.cookies_file, 'rb') as f:
                    cookies = pickle.load(f)
                    self.session.cookies.update(cookies)
                logger.info("✅ Cookies加载成功")
            else:
                logger.error(f"❌ Cookies文件不存在: {self.cookies_file}")
                return False
            
            # 加载会话信息
            if os.path.exists(self.session_file):
                with open(self.session_file, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)
                    user_agent = session_data.get('user_agent')
                    if user_agent:
                        self.session.headers.update({'User-Agent': user_agent})
                logger.info("✅ 会话信息加载成功")
            else:
                # 使用默认User-Agent
                self.session.headers.update({
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                })
                logger.warning("⚠️ 会话文件不存在，使用默认User-Agent")
            
            # 设置其他必要的请求头
            self.session.headers.update({
                'Referer': 'https://mp.weixin.qq.com/',
                'Origin': 'https://mp.weixin.qq.com'
            })
            
            # 验证登录状态
            return self._verify_login_status()
            
        except Exception as e:
            logger.error(f"❌ 加载会话失败: {e}")
            return False
    
    def _verify_login_status(self) -> bool:
        """验证登录状态"""
        try:
            logger.info("🔍 验证登录状态...")
            
            # 尝试访问主页获取token
            home_url = "https://mp.weixin.qq.com"
            response = self.session.get(home_url, timeout=10)
            
            if response.status_code == 200 and 'token=' in response.text:
                # 提取token
                import re
                token_match = re.search(r'token=([^&"\']+)', response.text)
                if token_match:
                    self.token = token_match.group(1)
                    logger.info(f"✅ 登录状态有效，token: {self.token[:10]}...")
                    
                    # 获取用户信息
                    self._get_user_info()
                    return True
                else:
                    logger.error("❌ 无法提取token")
                    return False
            else:
                logger.error(f"❌ 登录状态无效，状态码: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 验证登录状态失败: {e}")
            return False
    
    def _get_user_info(self):
        """获取用户信息"""
        try:
            user_url = "https://mp.weixin.qq.com/cgi-bin/loginpage"
            params = {'t': 'wxm-login', 'lang': 'zh_CN', 'token': self.token}
            
            response = self.session.get(user_url, params=params, timeout=10)
            if response.status_code == 200:
                # 简单解析用户信息（如果需要的话）
                logger.info("✅ 用户信息获取成功")
            
        except Exception as e:
            logger.warning(f"⚠️ 获取用户信息失败: {e}")
    
    def _wait_for_rate_limit(self):
        """频率控制"""
        current_time = time.time()
        time_diff = current_time - self.last_request_time
        
        if time_diff < self.request_interval:
            sleep_time = self.request_interval - time_diff
            logger.debug(f"⏳ 频率控制，等待 {sleep_time:.1f} 秒")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def search_account(self, keyword: str) -> List[Dict]:
        """搜索公众号
        
        Args:
            keyword: 搜索关键词
            
        Returns:
            公众号列表
        """
        try:
            logger.info(f"🔍 搜索公众号: {keyword}")
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
            
            response = self.session.get(search_url, params=params, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('base_resp', {}).get('ret') == 0:
                    accounts = result.get('list', [])
                    logger.info(f"✅ 找到 {len(accounts)} 个公众号")
                    return accounts
                else:
                    error_msg = result.get('base_resp', {}).get('err_msg', '未知错误')
                    logger.error(f"❌ 搜索失败: {error_msg}")
                    return []
            else:
                logger.error(f"❌ 搜索请求失败: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"❌ 搜索出错: {e}")
            return []
    
    def collect_articles(self, account: Dict, start_date: datetime, end_date: datetime, max_articles: int = 50) -> List[Dict]:
        """收集指定公众号的文章
        
        Args:
            account: 公众号信息
            start_date: 开始日期
            end_date: 结束日期
            max_articles: 最大文章数
            
        Returns:
            文章列表
        """
        try:
            fakeid = account.get('fakeid', '')
            if not fakeid:
                logger.error("❌ 无法获取公众号ID")
                return []
            
            account_name = account.get('nickname', '未知公众号')
            logger.info(f"📥 开始收集文章: {account_name}")
            logger.info(f"📅 时间范围: {start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}")
            logger.info(f"📊 最大数量: {max_articles}")
            
            articles = []
            begin = 0
            page_size = 20
            
            # 计算时间范围
            start_timestamp = int(start_date.timestamp())
            end_timestamp = int((end_date + timedelta(days=1) - timedelta(seconds=1)).timestamp())
            
            while len(articles) < max_articles:
                self._wait_for_rate_limit()
                
                logger.info(f"📄 获取第 {begin//page_size + 1} 页，已收集 {len(articles)} 篇")
                
                articles_url = "https://mp.weixin.qq.com/cgi-bin/appmsgpublish"
                params = {
                    'sub': 'list',
                    'search_field': 'null',
                    'begin': begin,
                    'count': page_size,
                    'query': '',
                    'fakeid': fakeid,
                    'type': 101_003,
                    'free_publish_type': 1,
                    'sub_action': 'list_ex',
                    'token': self.token,
                    'lang': 'zh_CN',
                    'f': 'json',
                    'ajax': 1
                }
                
                response = self.session.get(articles_url, params=params, timeout=15)
                
                if response.status_code != 200:
                    logger.error(f"❌ 请求失败: {response.status_code}")
                    break
                
                result = response.json()
                
                if result.get('base_resp', {}).get('ret') != 0:
                    error_msg = result.get('base_resp', {}).get('err_msg', '未知错误')
                    logger.error(f"❌ API返回错误: {error_msg}")
                    break
                
                # 解析文章
                page_articles = self._parse_articles_from_response(result)
                
                if not page_articles:
                    logger.info("📄 没有更多文章")
                    break
                
                # 筛选时间范围内的文章
                filtered_articles = []
                for article in page_articles:
                    article_time = article.get('create_time', 0)
                    if start_timestamp <= article_time <= end_timestamp:
                        filtered_articles.append(article)
                    elif article_time < start_timestamp:
                        # 如果文章时间早于开始时间，说明已经超出范围，停止收集
                        logger.info("⏰ 已收集到时间范围外的文章，停止收集")
                        return articles[:max_articles]
                
                articles.extend(filtered_articles)
                
                # 检查是否还有更多文章
                if len(page_articles) < page_size:
                    logger.info("📄 已收集完所有文章")
                    break
                
                begin += page_size
                
                # 避免无限循环
                if begin > 1000:
                    logger.warning("⚠️ 已达到最大页数限制")
                    break
            
            result_articles = articles[:max_articles]
            logger.info(f"✅ 收集完成，共 {len(result_articles)} 篇文章")
            return result_articles
            
        except Exception as e:
            logger.error(f"❌ 收集文章失败: {e}")
            return []
    
    def _parse_articles_from_response(self, result: Dict) -> List[Dict]:
        """从API响应中解析文章列表"""
        articles = []
        
        try:
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
                    link = appmsg.get('link', '').replace('\\/', '/')
                    
                    article = {
                        'title': appmsg.get('title', ''),
                        'url': link,  # 使用url字段以保持一致性
                        'link': link,  # 保留原字段名
                        'author_name': appmsg.get('author_name', ''),
                        'digest': appmsg.get('digest', ''),
                        'update_time': appmsg.get('update_time', 0),
                        'create_time': appmsg.get('create_time', 0),
                        'publish_time': datetime.fromtimestamp(appmsg.get('create_time', 0)).strftime('%Y-%m-%d %H:%M:%S') if appmsg.get('create_time') else ''
                    }
                    articles.append(article)
            
        except Exception as e:
            logger.error(f"❌ 解析文章列表出错: {e}")
        
        return articles
    
    def auto_collect_articles(self, account_name: str, days_back: int = 7, max_articles: int = 50) -> List[Dict]:
        """自动收集指定公众号的文章
        
        Args:
            account_name: 公众号名称
            days_back: 向前收集多少天的文章
            max_articles: 最大文章数
            
        Returns:
            文章列表
        """
        try:
            # 1. 加载登录状态
            if not self.load_session():
                logger.error("❌ 加载登录状态失败")
                return []
            
            # 2. 搜索公众号
            accounts = self.search_account(account_name)
            if not accounts:
                logger.error(f"❌ 未找到公众号: {account_name}")
                return []
            
            # 选择第一个匹配的公众号
            target_account = accounts[0]
            logger.info(f"✅ 选择公众号: {target_account.get('nickname', '')} ({target_account.get('alias', '')})")
            
            # 3. 计算时间范围
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            # 4. 收集文章
            articles = self.collect_articles(target_account, start_date, end_date, max_articles)
            
            return articles
            
        except Exception as e:
            logger.error(f"❌ 自动收集失败: {e}")
            return []


def main():
    """测试函数"""
    collector = HeadlessWeChatCollector()
    
    # 测试自动收集
    articles = collector.auto_collect_articles('仙境传说RO新启航', days_back=7, max_articles=20)
    
    if articles:
        print(f"\n✅ 收集到 {len(articles)} 篇文章:")
        for i, article in enumerate(articles, 1):
            print(f"{i}. {article['title']}")
            print(f"   URL: {article['url']}")
            print(f"   时间: {article['publish_time']}")
            print()
    else:
        print("❌ 未收集到文章")


if __name__ == "__main__":
    main() 