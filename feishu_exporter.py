#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞书知识库导出器 - Feishu Knowledge Base Exporter

支持将微信公众号文章导出为适合飞书知识库的格式
"""

import os
import time
import json
import requests
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from datetime import datetime
from loguru import logger
from urllib.parse import quote, unquote
import re

from utils import clean_text, random_delay


class FeishuExporter:
    """飞书知识库导出器"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Referer': 'https://weixin.sogou.com/',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        })
    
    def improved_content_extraction(self, article_url: str, max_retries: int = 3) -> str:
        """改进的内容提取方法，处理验证码和反爬措施"""
        
        for attempt in range(max_retries):
            try:
                logger.debug(f"尝试获取内容 (第{attempt + 1}次): {article_url[:50]}...")
                
                # 随机延迟避免被检测
                random_delay(2, 5)
                
                # 更新请求头，模拟真实浏览器
                headers = self.session.headers.copy()
                headers.update({
                    'User-Agent': self._get_random_user_agent(),
                    'X-Requested-With': 'XMLHttpRequest',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'cross-site',
                })
                
                # 发送请求
                response = self.session.get(
                    article_url, 
                    headers=headers,
                    timeout=15, 
                    allow_redirects=True
                )
                response.raise_for_status()
                
                # 检查是否遇到验证码
                if self._is_captcha_page(response.text):
                    logger.warning(f"遇到验证码页面，尝试其他方法...")
                    content = self._try_alternative_extraction(article_url)
                    if content:
                        return content
                    continue
                
                # 解析内容
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # 检查是否是有效的微信文章页面
                if not self._is_valid_wechat_article(soup):
                    logger.warning("不是有效的微信文章页面")
                    continue
                
                # 提取文章内容
                content = self._extract_article_content(soup)
                
                if content and len(content.strip()) > 50:  # 确保内容不为空
                    logger.success(f"成功获取文章内容 ({len(content)} 字符)")
                    return content
                else:
                    logger.warning("提取的内容为空或过短")
                    
            except requests.exceptions.RequestException as e:
                logger.warning(f"请求失败 (第{attempt + 1}次): {str(e)}")
                if attempt < max_retries - 1:
                    random_delay(5, 10)  # 失败后等待更长时间
                    
            except Exception as e:
                logger.error(f"提取内容时出错: {str(e)}")
                break
        
        return "内容获取失败 - 可能遇到反爬限制"
    
    def _get_random_user_agent(self) -> str:
        """获取随机User-Agent"""
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15'
        ]
        import random
        return random.choice(user_agents)
    
    def _is_captcha_page(self, html_content: str) -> bool:
        """检查是否是验证码页面"""
        captcha_indicators = [
            '验证码', 'captcha', 'verify', '人机验证', 
            '点击完成验证', '安全验证', '请输入验证码'
        ]
        html_lower = html_content.lower()
        return any(indicator in html_lower for indicator in captcha_indicators)
    
    def _is_valid_wechat_article(self, soup: BeautifulSoup) -> bool:
        """检查是否是有效的微信文章页面"""
        # 检查常见的微信文章标识
        indicators = [
            soup.select('#js_content'),
            soup.select('.rich_media_content'),
            soup.select('[data-from="weixin"]'),
            soup.find('meta', property='og:type', content='article')
        ]
        return any(indicators)
    
    def _try_alternative_extraction(self, article_url: str) -> Optional[str]:
        """尝试替代的内容提取方法"""
        try:
            # 方法1: 尝试直接访问原始URL
            if 'sogou.com' in article_url:
                # 尝试解析出真实的微信URL
                real_url = self._extract_real_wechat_url(article_url)
                if real_url:
                    logger.info(f"尝试直接访问微信URL: {real_url[:50]}...")
                    response = self.session.get(real_url, timeout=10)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, 'html.parser')
                        content = self._extract_article_content(soup)
                        if content:
                            return content
            
            # 方法2: 尝试使用不同的请求参数
            # 这里可以添加更多的替代方法
            
        except Exception as e:
            logger.debug(f"替代提取方法失败: {str(e)}")
        
        return None
    
    def _extract_real_wechat_url(self, sogou_url: str) -> Optional[str]:
        """从搜狗链接中提取真实的微信URL"""
        try:
            # 发送请求获取重定向
            response = self.session.head(sogou_url, allow_redirects=True, timeout=10)
            final_url = response.url
            
            if 'mp.weixin.qq.com' in final_url:
                return final_url
                
        except Exception as e:
            logger.debug(f"提取真实URL失败: {str(e)}")
        
        return None
    
    def _extract_article_content(self, soup: BeautifulSoup) -> str:
        """从页面中提取文章内容"""
        # 优先级顺序的内容选择器
        content_selectors = [
            '#js_content',
            '.rich_media_content',
            '.appmsg_content_text',
            '.article_content',
            '[data-role="article-content"]',
            '.post_content',
            '.content'
        ]
        
        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                # 移除不需要的元素
                for unwanted in content_elem.select(
                    'script, style, .reward_area, .share_area, '
                    '.qr_code, .js_vote_area, .weapp_display_element, '
                    '.rich_media_area_extra, .code-snippet__fix'
                ):
                    unwanted.decompose()
                
                # 提取纯文本内容
                content = content_elem.get_text(separator='\n', strip=True)
                content = clean_text(content)
                
                if len(content.strip()) > 50:  # 确保内容有意义
                    return content
        
        return ""
    
    def export_to_markdown(self, articles: List[Dict[str, Any]], filename: str) -> bool:
        """导出为Markdown格式，适合飞书知识库"""
        try:
            os.makedirs("output", exist_ok=True)
            filepath = os.path.join("output", filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                # 写入文档头部
                f.write(f"# 微信公众号文章合集\n\n")
                f.write(f"**导出时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"**文章数量**: {len(articles)}\n\n")
                f.write("---\n\n")
                
                # 写入目录
                f.write("## 目录\n\n")
                for i, article in enumerate(articles, 1):
                    title = article.get('title', '未知标题')
                    f.write(f"{i}. [{title}](#{self._to_anchor(title)})\n")
                f.write("\n---\n\n")
                
                # 写入文章内容
                for i, article in enumerate(articles, 1):
                    title = article.get('title', '未知标题')
                    author = article.get('author', '未知作者')
                    publish_date = article.get('publish_date', '未知日期')
                    url = article.get('url', '')
                    content = article.get('content', '')
                    
                    # 文章标题
                    f.write(f"## {i}. {title}\n\n")
                    
                    # 文章元信息
                    f.write("**文章信息**:\n")
                    f.write(f"- 作者: {author}\n")
                    f.write(f"- 发布日期: {publish_date}\n")
                    f.write(f"- 原文链接: [点击查看]({url})\n\n")
                    
                    # 文章内容
                    if content and content != "Content not available":
                        f.write("**正文内容**:\n\n")
                        # 处理内容，确保Markdown格式正确
                        formatted_content = self._format_content_for_markdown(content)
                        f.write(formatted_content)
                    else:
                        f.write("*暂无法获取文章正文内容*\n")
                    
                    f.write("\n\n---\n\n")
            
            logger.success(f"✅ 成功导出Markdown文件: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 导出Markdown失败: {str(e)}")
            return False
    
    def export_to_html(self, articles: List[Dict[str, Any]], filename: str) -> bool:
        """导出为HTML格式"""
        try:
            os.makedirs("output", exist_ok=True)
            filepath = os.path.join("output", filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                # HTML文档结构
                f.write("""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>微信公众号文章合集</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; margin: 40px; }
        .header { border-bottom: 2px solid #eee; padding-bottom: 20px; margin-bottom: 30px; }
        .article { margin-bottom: 40px; padding: 20px; border: 1px solid #eee; border-radius: 8px; }
        .article-title { color: #333; font-size: 24px; margin-bottom: 10px; }
        .article-meta { color: #666; font-size: 14px; margin-bottom: 20px; }
        .article-content { color: #444; line-height: 1.8; }
        .toc { background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 30px; }
        .toc ul { list-style-type: none; padding-left: 0; }
        .toc li { margin: 5px 0; }
        .toc a { text-decoration: none; color: #007bff; }
        .toc a:hover { text-decoration: underline; }
    </style>
</head>
<body>
""")
                
                # 文档头部
                f.write(f"""
    <div class="header">
        <h1>微信公众号文章合集</h1>
        <p><strong>导出时间</strong>: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p><strong>文章数量</strong>: {len(articles)}</p>
    </div>
""")
                
                # 目录
                f.write('<div class="toc"><h2>目录</h2><ul>')
                for i, article in enumerate(articles, 1):
                    title = article.get('title', '未知标题')
                    f.write(f'<li><a href="#article-{i}">{i}. {self._escape_html(title)}</a></li>')
                f.write('</ul></div>')
                
                # 文章内容
                for i, article in enumerate(articles, 1):
                    title = article.get('title', '未知标题')
                    author = article.get('author', '未知作者')
                    publish_date = article.get('publish_date', '未知日期')
                    url = article.get('url', '')
                    content = article.get('content', '')
                    
                    f.write(f"""
    <div class="article" id="article-{i}">
        <h2 class="article-title">{i}. {self._escape_html(title)}</h2>
        <div class="article-meta">
            <p><strong>作者</strong>: {self._escape_html(author)}</p>
            <p><strong>发布日期</strong>: {self._escape_html(publish_date)}</p>
            <p><strong>原文链接</strong>: <a href="{url}" target="_blank">点击查看</a></p>
        </div>
        <div class="article-content">
""")
                    
                    if content and content != "Content not available":
                        formatted_content = self._format_content_for_html(content)
                        f.write(formatted_content)
                    else:
                        f.write('<p><em>暂无法获取文章正文内容</em></p>')
                    
                    f.write('</div></div>')
                
                f.write('</body></html>')
            
            logger.success(f"✅ 成功导出HTML文件: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 导出HTML失败: {str(e)}")
            return False
    
    def export_articles_individually(self, articles: List[Dict[str, Any]], format_type: str = 'markdown') -> bool:
        """单独导出每篇文章，适合批量上传到飞书"""
        try:
            # 创建独立文章目录
            output_dir = os.path.join("output", "individual_articles")
            os.makedirs(output_dir, exist_ok=True)
            
            success_count = 0
            
            for i, article in enumerate(articles, 1):
                title = article.get('title', f'文章_{i}')
                # 清理文件名，移除特殊字符
                safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)[:50]
                
                if format_type == 'markdown':
                    filename = f"{i:02d}_{safe_title}.md"
                    if self._export_single_article_markdown(article, os.path.join(output_dir, filename)):
                        success_count += 1
                elif format_type == 'html':
                    filename = f"{i:02d}_{safe_title}.html"
                    if self._export_single_article_html(article, os.path.join(output_dir, filename)):
                        success_count += 1
            
            logger.success(f"✅ 成功导出 {success_count}/{len(articles)} 篇独立文章到 {output_dir}")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"❌ 独立文章导出失败: {str(e)}")
            return False
    
    def _export_single_article_markdown(self, article: Dict[str, Any], filepath: str) -> bool:
        """导出单篇文章为Markdown"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                title = article.get('title', '未知标题')
                author = article.get('author', '未知作者')
                publish_date = article.get('publish_date', '未知日期')
                url = article.get('url', '')
                content = article.get('content', '')
                
                f.write(f"# {title}\n\n")
                f.write(f"**作者**: {author}\n")
                f.write(f"**发布日期**: {publish_date}\n")
                f.write(f"**原文链接**: [点击查看]({url})\n\n")
                f.write("---\n\n")
                
                if content and content != "Content not available":
                    formatted_content = self._format_content_for_markdown(content)
                    f.write(formatted_content)
                else:
                    f.write("*暂无法获取文章正文内容*\n")
            
            return True
        except Exception:
            return False
    
    def _export_single_article_html(self, article: Dict[str, Any], filepath: str) -> bool:
        """导出单篇文章为HTML"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                title = article.get('title', '未知标题')
                author = article.get('author', '未知作者')
                publish_date = article.get('publish_date', '未知日期')
                url = article.get('url', '')
                content = article.get('content', '')
                
                f.write(f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self._escape_html(title)}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; margin: 40px; }}
        .header {{ border-bottom: 2px solid #eee; padding-bottom: 20px; margin-bottom: 30px; }}
        .meta {{ color: #666; font-size: 14px; margin-bottom: 20px; }}
        .content {{ color: #444; line-height: 1.8; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{self._escape_html(title)}</h1>
    </div>
    <div class="meta">
        <p><strong>作者</strong>: {self._escape_html(author)}</p>
        <p><strong>发布日期</strong>: {self._escape_html(publish_date)}</p>
        <p><strong>原文链接</strong>: <a href="{url}" target="_blank">点击查看</a></p>
    </div>
    <div class="content">
""")
                
                if content and content != "Content not available":
                    formatted_content = self._format_content_for_html(content)
                    f.write(formatted_content)
                else:
                    f.write('<p><em>暂无法获取文章正文内容</em></p>')
                
                f.write('</div></body></html>')
            
            return True
        except Exception:
            return False
    
    def _to_anchor(self, text: str) -> str:
        """转换文本为锚点链接"""
        # 移除特殊字符，保留中英文和数字
        anchor = re.sub(r'[^\w\u4e00-\u9fff]+', '-', text).strip('-').lower()
        return anchor
    
    def _escape_html(self, text: str) -> str:
        """HTML转义"""
        return (text.replace('&', '&amp;')
                   .replace('<', '&lt;')
                   .replace('>', '&gt;')
                   .replace('"', '&quot;')
                   .replace("'", '&#x27;'))
    
    def _format_content_for_markdown(self, content: str) -> str:
        """格式化内容为Markdown"""
        # 处理段落
        paragraphs = content.split('\n')
        formatted_paragraphs = []
        
        for para in paragraphs:
            para = para.strip()
            if para:
                # 简单的格式化处理
                formatted_paragraphs.append(para)
        
        return '\n\n'.join(formatted_paragraphs) + '\n'
    
    def _format_content_for_html(self, content: str) -> str:
        """格式化内容为HTML"""
        # 处理段落
        paragraphs = content.split('\n')
        formatted_paragraphs = []
        
        for para in paragraphs:
            para = para.strip()
            if para:
                escaped_para = self._escape_html(para)
                formatted_paragraphs.append(f'<p>{escaped_para}</p>')
        
        return '\n'.join(formatted_paragraphs)


def main():
    """示例用法"""
    # 创建导出器
    exporter = FeishuExporter()
    
    # 首先获取文章列表
    scraper = SogouWeChatScraper()
    account_name = "人民日报"
    
    logger.info("开始获取文章列表...")
    articles = scraper.search_account_articles(account_name, max_pages=3)
    
    if not articles:
        logger.error("未找到任何文章")
        return
    
    # 改进的内容获取
    logger.info("开始获取文章内容...")
    for i, article in enumerate(articles):
        logger.info(f"正在处理第 {i+1}/{len(articles)} 篇文章: {article['title'][:30]}...")
        content = exporter.improved_content_extraction(article['url'])
        articles[i]['content'] = content
    
    # 导出为不同格式
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 1. 导出为Markdown合集
    exporter.export_to_markdown(articles, f"wechat_articles_{account_name}_{timestamp}.md")
    
    # 2. 导出为HTML合集
    exporter.export_to_html(articles, f"wechat_articles_{account_name}_{timestamp}.html")
    
    # 3. 导出为独立的Markdown文件（适合飞书批量上传）
    exporter.export_articles_individually(articles, 'markdown')
    
    logger.success("✅ 所有导出任务完成!")


if __name__ == "__main__":
    main() 