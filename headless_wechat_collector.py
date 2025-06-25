#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
无头微信文章收集器

专为GitHub Actions等无头环境设计，基于保存的登录状态进行文章收集
"""

import pickle
import json
import requests
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from loguru import logger

class HeadlessWeChatCollector:
    """无头微信文章收集器"""
    
    def __init__(self, cookies_file: str = "wechat_cookies.pkl", session_file: str = "wechat_session.json"):
        """初始化收集器
        
        Args:
            cookies_file: cookies文件路径
            session_file: 会话信息文件路径
        """
        self.cookies_file = cookies_file
        self.session_file = session_file
        self.session = requests.Session()
        self.token = None
        self.user_agent = None
        
        # 设置请求超时和重试
        self.session.timeout = 30
        self.max_retries = 3
        
        logger.info("🚀 无头微信文章收集器初始化完成")
    
    def load_session(self) -> bool:
        """加载保存的登录状态"""
        try:
            # 1. 加载cookies
            try:
                with open(self.cookies_file, 'rb') as f:
                    cookies = pickle.load(f)
                    self.session.cookies.update(cookies)
                logger.info("✅ Cookies加载成功")
            except Exception as e:
                logger.error(f"❌ Cookies加载失败: {e}")
                return False
            
            # 2. 加载会话信息
            try:
                with open(self.session_file, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)
                    self.user_agent = session_data.get('user_agent')
                    if self.user_agent:
                        self.session.headers.update({'User-Agent': self.user_agent})
                logger.info("✅ 会话信息加载成功")
            except Exception as e:
                logger.error(f"❌ 会话信息加载失败: {e}")
                return False
            
            # 3. 验证登录状态并获取token
            return self._verify_login_status()
            
        except Exception as e:
            logger.error(f"❌ 加载登录状态失败: {e}")
            return False
    
    def _verify_login_status(self) -> bool:
        """验证登录状态并获取token"""
        try:
            logger.info("🔍 验证登录状态...")
            
            # 访问微信公众平台首页获取token
            home_url = "https://mp.weixin.qq.com/"
            
            for attempt in range(self.max_retries):
                try:
                    logger.info(f"🌐 尝试连接微信公众平台 (第{attempt+1}次)...")
                    response = self.session.get(home_url, timeout=30)
                    
                    if response.status_code == 200:
                        # 从响应中提取token
                        content = response.text
                        if 'token=' in content:
                            import re
                            token_match = re.search(r'token=(\d+)', content)
                            if token_match:
                                self.token = token_match.group(1)
                                logger.info(f"✅ 登录状态验证成功，token: {self.token[:10]}...")
                                return True
                        
                        logger.warning("⚠️ 未找到token，可能需要重新登录")
                        return False
                    else:
                        logger.warning(f"⚠️ 连接失败，状态码: {response.status_code}")
                        
                except requests.exceptions.Timeout:
                    logger.warning(f"⏰ 连接超时 (第{attempt+1}次)")
                except requests.exceptions.RequestException as e:
                    logger.warning(f"🌐 网络请求异常 (第{attempt+1}次): {e}")
                
                if attempt < self.max_retries - 1:
                    logger.info("⏳ 等待5秒后重试...")
                    time.sleep(5)
            
            logger.error("❌ 多次尝试后仍无法连接微信公众平台")
            return False
            
        except Exception as e:
            logger.error(f"❌ 验证登录状态出错: {e}")
            return False
    
    def _get_user_info(self):
        """获取用户信息（用于调试）"""
        try:
            user_info_url = "https://mp.weixin.qq.com/cgi-bin/loginpage"
            params = {'token': self.token, 'lang': 'zh_CN'}
            
            response = self.session.get(user_info_url, params=params, timeout=15)
            if response.status_code == 200:
                logger.info("✅ 用户信息获取成功")
                return response.json()
        except Exception as e:
            logger.warning(f"⚠️ 获取用户信息失败: {e}")
        return None
    
    def _wait_for_rate_limit(self):
        """等待避免频率限制"""
        time.sleep(2)  # 增加等待时间以避免被限制
    
    def search_account(self, keyword: str) -> List[Dict]:
        """搜索公众号"""
        try:
            logger.info(f"🔍 搜索公众号: {keyword}")
            
            if not self.token:
                logger.error("❌ Token未设置，无法搜索")
                return []
            
            search_url = "https://mp.weixin.qq.com/cgi-bin/searchbiz"
            params = {
                'action': 'search_biz',
                'token': self.token,
                'lang': 'zh_CN',
                'f': 'json',
                'ajax': 1,
                'random': str(time.time()),
                'query': keyword,
                'count': 10
            }
            
            for attempt in range(self.max_retries):
                try:
                    self._wait_for_rate_limit()
                    response = self.session.get(search_url, params=params, timeout=15)
                    
                    if response.status_code == 200:
                        result = response.json()
                        
                        if result.get('base_resp', {}).get('ret') == 0:
                            accounts = result.get('list', [])
                            logger.info(f"✅ 找到 {len(accounts)} 个公众号")
                            
                            for i, account in enumerate(accounts, 1):
                                nickname = account.get('nickname', '未知')
                                alias = account.get('alias', '无别名')
                                logger.info(f"  {i}. {nickname} ({alias})")
                            
                            return accounts
                        else:
                            error_msg = result.get('base_resp', {}).get('err_msg', '未知错误')
                            logger.error(f"❌ 搜索API返回错误: {error_msg}")
                    else:
                        logger.warning(f"⚠️ 搜索请求失败，状态码: {response.status_code}")
                        
                except requests.exceptions.Timeout:
                    logger.warning(f"⏰ 搜索请求超时 (第{attempt+1}次)")
                except Exception as e:
                    logger.warning(f"🌐 搜索请求异常 (第{attempt+1}次): {e}")
                
                if attempt < self.max_retries - 1:
                    logger.info("⏳ 等待3秒后重试...")
                    time.sleep(3)
            
            logger.error("❌ 多次尝试后搜索仍然失败")
            return []
            
        except Exception as e:
            logger.error(f"❌ 搜索公众号失败: {e}")
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
            
            # 计算时间范围（注意：end_date 要包含整天，所以加1天再减1秒）
            start_timestamp = int(start_date.timestamp())
            end_timestamp = int((end_date + timedelta(days=1) - timedelta(seconds=1)).timestamp())
            
            logger.info(f"⏰ 时间戳范围: {start_timestamp} - {end_timestamp}")
            
            # 用于收集符合时间范围的文章
            filtered_articles = []
            
            while len(filtered_articles) < max_articles:
                self._wait_for_rate_limit()
                
                logger.info(f"📄 获取第 {begin//page_size + 1} 页，已收集 {len(filtered_articles)} 篇")
                
                articles_url = "https://mp.weixin.qq.com/cgi-bin/appmsgpublish"
                params = {
                    'sub': 'list',
                    'search_field': 'null',
                    'begin': begin,
                    'count': page_size,
                    'query': '',
                    'fakeid': fakeid,
                    'type': '101_1',  # 修复：使用正确的type参数
                    'free_publish_type': 1,
                    'sub_action': 'list_ex',
                    'token': self.token,
                    'lang': 'zh_CN',
                    'f': 'json',
                    'ajax': 1
                }
                
                success = False
                for attempt in range(self.max_retries):
                    try:
                        response = self.session.get(articles_url, params=params, timeout=15)
                        
                        if response.status_code == 200:
                            result = response.json()
                            
                            if result.get('base_resp', {}).get('ret') == 0:
                                success = True
                                break
                            else:
                                error_msg = result.get('base_resp', {}).get('err_msg', '未知错误')
                                logger.warning(f"⚠️ API返回错误 (第{attempt+1}次): {error_msg}")
                        else:
                            logger.warning(f"⚠️ 请求失败 (第{attempt+1}次): {response.status_code}")
                            
                    except requests.exceptions.Timeout:
                        logger.warning(f"⏰ 请求超时 (第{attempt+1}次)")
                    except Exception as e:
                        logger.warning(f"🌐 请求异常 (第{attempt+1}次): {e}")
                    
                    if attempt < self.max_retries - 1:
                        time.sleep(3)
                
                if not success:
                    logger.error("❌ 多次尝试后API请求仍然失败")
                    break
                
                # 解析文章
                page_articles = self._parse_articles_from_response(result)
                logger.info(f"📋 当前页解析到 {len(page_articles)} 篇文章")
                
                if not page_articles:
                    logger.info("📄 没有更多文章")
                    break
                
                # 检查是否所有文章都早于起始时间（按时间倒序，如果第一篇都早于起始时间，则可以停止）
                first_article_time = page_articles[0].get('update_time', 0) if page_articles else 0
                if first_article_time < start_timestamp:
                    logger.info(f"✅ 已达到起始日期限制 ({start_date.strftime('%Y-%m-%d')})")
                    break
                
                # 过滤时间范围内的文章
                for article in page_articles:
                    article_time = article.get('update_time', 0)  # 修复：使用update_time字段
                    article_date_str = datetime.fromtimestamp(article_time).strftime('%Y-%m-%d %H:%M:%S')
                    
                    # 如果文章时间早于起始时间，跳过这篇文章
                    if article_time < start_timestamp:
                        logger.info(f"📅 跳过早于起始日期的文章: {article.get('title', '')[:30]}... ({article_date_str})")
                        continue
                    
                    # 如果文章时间晚于结束时间，跳过这篇文章
                    if article_time > end_timestamp:
                        logger.info(f"📅 跳过晚于结束日期的文章: {article.get('title', '')[:30]}... ({article_date_str})")
                        continue
                    
                    # 文章在时间范围内，添加到过滤列表
                    logger.info(f"✅ 符合时间范围的文章: {article.get('title', '')[:30]}... ({article_date_str})")
                    filtered_articles.append(article)
                    
                    # 如果已达到最大数量，停止收集
                    if len(filtered_articles) >= max_articles:
                        break
                
                # 如果已达到最大数量，停止收集
                if len(filtered_articles) >= max_articles:
                    logger.info(f"✅ 已达到最大文章数量限制: {max_articles}")
                    break
                
                begin += page_size
                
                # 避免无限循环
                if begin > 1000:
                    logger.warning("⚠️ 已达到最大页数限制")
                    break
            
            # 按时间倒序排序（最新的在前面）
            filtered_articles.sort(key=lambda x: x.get('update_time', 0), reverse=True)
            
            # 应用数量限制
            result_articles = filtered_articles[:max_articles]
            
            logger.info(f"✅ 收集完成，共 {len(result_articles)} 篇文章")
            return result_articles
            
        except Exception as e:
            logger.error(f"❌ 收集文章失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def _parse_articles_from_response(self, result: Dict) -> List[Dict]:
        """从API响应中解析文章列表"""
        articles = []
        
        try:
            publish_page_str = result.get('publish_page', '')
            if not publish_page_str:
                logger.warning("⚠️ 响应中没有publish_page数据")
                return articles
            
            publish_page = json.loads(publish_page_str)
            publish_list = publish_page.get('publish_list', [])
            logger.info(f"📋 发布列表长度: {len(publish_list)}")
            
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
                        'update_time': appmsg.get('update_time', 0),  # 修复：使用update_time字段
                        'create_time': appmsg.get('create_time', 0),
                        'publish_time': datetime.fromtimestamp(appmsg.get('update_time', 0)).strftime('%Y-%m-%d %H:%M:%S') if appmsg.get('update_time') else ''  # 修复：使用update_time字段
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
            logger.info(f"🚀 开始自动收集: {account_name} (最近{days_back}天)")
            
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
            
            logger.info(f"🎉 自动收集完成: {len(articles)} 篇文章")
            return articles
            
        except Exception as e:
            logger.error(f"❌ 自动收集失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
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