#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
整合版自动下载上传工具
结合了：1.检测链接 2.下载文件 3.上传至云文档 4.移动到知识库
支持PDF和DOCX格式，包含重复检查
"""

import os
import json
import time
import requests
import argparse
from pathlib import Path
from typing import Optional, Dict, List, Union
from loguru import logger
from feishu_user_client import FeishuUserAPIClient
from simple_url_scraper import SimpleUrlScraper
import re
from datetime import datetime

class IntegratedAutoUploader:
    """整合版自动下载上传器"""
    
    def __init__(self, app_id: str = None, app_secret: str = None):
        """初始化整合上传器"""
        # 优先从环境变量获取配置
        self.app_id = app_id or os.getenv('FEISHU_APP_ID')
        self.app_secret = app_secret or os.getenv('FEISHU_APP_SECRET')
        
        if not self.app_id or not self.app_secret:
            # 尝试从配置文件读取
            try:
                with open('user_feishu_config.json', 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.app_id = self.app_id or config.get('app_id')
                    self.app_secret = self.app_secret or config.get('app_secret')
            except:
                pass
                
        if not self.app_id or not self.app_secret:
            raise ValueError("❌ 飞书APP ID和Secret未配置！请设置环境变量或配置文件")
        
        # 初始化飞书客户端
        self.feishu_client = FeishuUserAPIClient(self.app_id, self.app_secret)
        
        # 初始化下载器（延迟加载）
        self.url_scraper = None
        
        # 配置信息 - 优先从环境变量获取
        self.space_id = os.getenv('FEISHU_SPACE_ID', "7511922459407450115")
        self.parent_wiki_token = "Rkr5w3y8hib7dRk1KpFcMZ7tnGc"  # 目标父页面token
        self.ro_folder_token = "BTZkfStogleXeZdbyH7cEyvdnog"  # RO公众号文章文件夹
        
        # 输出目录
        self.output_dir = Path("output/auto_download")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 上传记录
        self.upload_log_file = "integrated_upload_log.json"
        self.upload_log = self._load_upload_log()
        
        logger.info("🚀 整合版自动下载上传器初始化完成")
        logger.info(f"📊 配置信息: Space ID={self.space_id}")
    
    def _load_upload_log(self) -> Dict:
        """加载上传日志"""
        try:
            if os.path.exists(self.upload_log_file):
                with open(self.upload_log_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"加载上传日志失败: {e}")
        return {}
    
    def _save_upload_log(self):
        """保存上传日志"""
        try:
            with open(self.upload_log_file, 'w', encoding='utf-8') as f:
                json.dump(self.upload_log, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存上传日志失败: {e}")
    
    def _is_url_processed(self, url: str) -> bool:
        """检查URL是否已处理"""
        return url in self.upload_log and self.upload_log[url].get('status') == 'completed'
    
    def _mark_url_processed(self, url: str, file_path: str, wiki_token: str = None, error: str = None):
        """标记URL处理状态"""
        self.upload_log[url] = {
            'timestamp': time.time(),
            'file_path': str(file_path) if file_path else None,
            'wiki_token': wiki_token,
            'status': 'completed' if wiki_token else 'failed',
            'error': error
        }
        self._save_upload_log()
    
    def _get_scraper(self) -> SimpleUrlScraper:
        """获取URL抓取器（延迟初始化）"""
        if not self.url_scraper:
            logger.info("🔧 初始化URL抓取器...")
            self.url_scraper = SimpleUrlScraper(headless=True)
        return self.url_scraper
    
    def _is_valid_wechat_url(self, url: str) -> bool:
        """检查是否是有效的微信文章URL"""
        if not url or not url.startswith('http'):
            return False
        return 'mp.weixin.qq.com/s' in url
    
    def _extract_title_from_url_light(self, url: str) -> Optional[str]:
        """轻量级方法从URL获取文章标题，不启动浏览器"""
        try:
            logger.debug(f"🚀 尝试轻量级获取标题: {url[:50]}...")
            
            # 使用requests获取页面HTML
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # 简单解析title标签
            import re
            title_match = re.search(r'<title[^>]*>([^<]+)</title>', response.text, re.IGNORECASE)
            if title_match:
                title = title_match.group(1).strip()
                # 清理微信公众号特有的标题格式
                if title:
                    logger.debug(f"✅ 轻量级方法获取标题成功: {title}")
                    return title
            
            # 尝试从og:title获取
            og_title_match = re.search(r'<meta[^>]*property=["\']og:title["\'][^>]*content=["\']([^"\']+)["\'][^>]*>', response.text, re.IGNORECASE)
            if og_title_match:
                title = og_title_match.group(1).strip()
                if title:
                    logger.debug(f"✅ 从og:title获取标题成功: {title}")
                    return title
            
            logger.debug(f"⚠️ 轻量级方法未找到标题")
            return None
            
        except Exception as e:
            logger.debug(f"⚠️ 轻量级获取标题失败: {e}")
            return None
    
    def check_file_duplicate_by_title(self, title: str, filename: str = None) -> bool:
        """通过标题检查云文档和知识库中是否已存在同名文件"""
        try:
            logger.info(f"🔍 开始全面重名检测: {title}")
            
            # 1. 检查云文档中是否有重名文件
            if filename:
                logger.debug(f"🗂️ 检查云文档重名: {filename}")
                drive_exists = self.feishu_client.check_file_exists_in_drive(
                    self.ro_folder_token, 
                    filename
                )
                if drive_exists:
                    logger.warning(f"📋 云文档中已存在同名文件: {filename}")
                    return True
            
            # 2. 检查知识库中是否有重名文件  
            logger.debug(f"📚 检查知识库重名: {title}")
            wiki_exists = self.feishu_client.check_file_exists_in_wiki(
                self.space_id, 
                title, 
                self.parent_wiki_token
            )
            
            if wiki_exists:
                logger.warning(f"📋 知识库中已存在同名文件: {title}")
                return True
            
            logger.debug(f"✅ 重名检测通过，无重复文件")
            return False
            
        except Exception as e:
            logger.error(f"检查文件重复时出错: {e}")
            return False
    
    def download_article(self, url: str, format_type: str = "pdf") -> Union[Path, str, None]:
        """下载微信文章为指定格式
        
        Args:
            url: 微信文章URL
            format_type: 文件格式 ("pdf" 或 "docx")
            
        Returns:
            Path: 下载的文件路径（成功）
            "DUPLICATE_SKIPPED": 跳过下载（检测到重复文件）
            None: 下载失败
        """
        try:
            logger.info(f"📥 开始下载文章: {url[:50]}...")
            logger.info(f"📄 格式: {format_type.upper()}")
            
            # 🔥 延迟浏览器初始化：先轻量级获取标题，再做重复检测
            logger.info(f"🚀 使用轻量级方法获取文章标题...")
            
            # 简单从URL获取基本信息，不初始化浏览器
            title = self._extract_title_from_url_light(url)
            if not title:
                # 如果轻量级方法失败，才使用浏览器
                logger.info(f"⚠️ 轻量级方法失败，使用浏览器获取文章信息...")
                scraper = self._get_scraper()
                article_info = scraper.extract_article_info(url)
                if not article_info or 'error' in article_info:
                    logger.error("无法获取文章信息")
                    return None
                title = article_info.get('title', 'unknown_article')
            
            safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)[:80]
            if not safe_title.strip():
                safe_title = f"article_{datetime.now().strftime('%H%M%S')}"
            
            # 生成文件名
            file_ext = f".{format_type}"
            filename = f"{safe_title}{file_ext}"
            
            # 检查是否已存在同名文件（同时检查云文档和知识库）
            logger.info(f"🔍 重复检测：{safe_title}")
            if self.check_file_duplicate_by_title(safe_title, filename):
                logger.warning(f"🚫 跳过下载，已存在同名文件: {filename}")
                return "DUPLICATE_SKIPPED"  # 🔥 特殊返回值表示跳过而非失败
            
            # 📥 真正开始下载，此时才初始化浏览器
            logger.info(f"✅ 重复检测通过，开始实际下载...")
            scraper = self._get_scraper()
            
            # 生成文件路径
            output_path = self.output_dir / filename
            
            # 处理文件名冲突
            counter = 1
            original_path = output_path
            while output_path.exists():
                filename = f"{safe_title}_{counter}{file_ext}"
                output_path = self.output_dir / filename
                counter += 1
            
            # 下载文件
            logger.info(f"💾 保存为: {filename}")
            
            success = False
            if format_type == "pdf":
                success = scraper.save_as_pdf(url, str(output_path))
            elif format_type == "docx":
                success = scraper.save_as_docx(url, str(output_path))
            
            if success and output_path.exists():
                file_size = output_path.stat().st_size
                logger.success(f"✅ 下载成功: {filename} ({file_size} bytes)")
                return output_path
            else:
                logger.error(f"❌ 下载失败: {filename}")
                return None
                
        except Exception as e:
            logger.error(f"下载文章时出错: {e}")
            return None
    
    def upload_to_drive(self, file_path: Path) -> Optional[str]:
        """上传文件到飞书云文档
        
        Args:
            file_path: 本地文件路径
            
        Returns:
            文件token，失败返回None
        """
        try:
            filename = file_path.name
            title = file_path.stem  # 不含扩展名的文件名
            
            logger.info(f"☁️ 上传文件到云文档: {filename}")
            
            # 🆕 上传前再次检查云文档重名（防止多线程并发问题）
            logger.debug(f"🔍 上传前最后检查云文档重名: {filename}")
            if self.feishu_client.check_file_exists_in_drive(self.ro_folder_token, filename):
                logger.warning(f"📋 云文档上传时发现重名文件，跳过上传: {filename}")
                # 尝试获取已存在文件的token（如果需要的话）
                return "DUPLICATE"
            
            file_token = self.feishu_client.upload_file_to_drive(
                str(file_path),
                parent_node=self.ro_folder_token,
                parent_type="explorer"
            )
            
            if file_token:
                drive_url = f"https://thedream.feishu.cn/file/{file_token}"
                logger.success(f"✅ 云文档上传成功: {drive_url}")
                return file_token
            else:
                logger.error(f"❌ 云文档上传失败: {filename}")
                return None
                
        except Exception as e:
            logger.error(f"上传到云文档时出错: {e}")
            return None
    
    def move_to_wiki(self, file_token: str, file_name: str) -> Optional[str]:
        """移动文件到知识库
        
        Args:
            file_token: 云文档文件token
            file_name: 文件名
            
        Returns:
            知识库文档token，失败返回None
        """
        try:
            logger.info(f"📚 移动文件到知识库: {file_name}")
            
            # 🆕 注释掉有问题的token检查，避免400错误
            # 该检查会用云文档token查询知识库API，导致400错误
            logger.debug(f"🔍 跳过token重复检查（避免API错误）...")
            
            # 🆕 额外检查：基于文件名在知识库中搜索重复
            title_without_ext = os.path.splitext(file_name)[0]
            if self.feishu_client.check_file_exists_in_wiki(self.space_id, title_without_ext, self.parent_wiki_token):
                logger.warning(f"🚫 知识库中已存在同名文档，取消转移: {title_without_ext}")
                return "DUPLICATE_TITLE"
            
            # 使用move_docs_to_wiki API
            url = f"https://open.feishu.cn/open-apis/wiki/v2/spaces/{self.space_id}/nodes/move_docs_to_wiki"
            
            # 获取访问令牌
            if not self.feishu_client.ensure_valid_token():
                logger.error("无法获取有效的访问令牌")
                return None
            
            headers = {
                'Authorization': f'Bearer {self.feishu_client.access_token}',
                'Content-Type': 'application/json'
            }
            
            data = {
                "obj_token": file_token,
                "obj_type": "file",
                "parent_wiki_token": self.parent_wiki_token
            }
            
            logger.info(f"🔄 API调用: {url}")
            logger.debug(f"📋 请求数据: {json.dumps(data, indent=2, ensure_ascii=False)}")
            
            response = requests.post(url, headers=headers, json=data)
            logger.info(f"📡 响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                if result.get('code') == 0:
                    data_result = result.get('data', {})
                    if 'wiki_token' in data_result:
                        wiki_token = data_result['wiki_token']
                        wiki_url = f"https://thedream.feishu.cn/wiki/{wiki_token}"
                        logger.success(f"✅ 移动到知识库成功: {wiki_url}")
                        return wiki_token
                    elif 'task_id' in data_result:
                        task_id = data_result['task_id']
                        logger.info(f"⏳ 移动任务已提交: {task_id}")
                        return task_id  # 返回task_id作为标识
                else:
                    logger.error(f"❌ API返回错误: {result.get('msg')}")
            else:
                logger.error(f"❌ HTTP请求失败: {response.status_code}")
                logger.error(f"响应内容: {response.text}")
            
            return None
            
        except Exception as e:
            logger.error(f"移动到知识库时出错: {e}")
            return None
    
    def process_single_url(self, url: str, format_type: str = "pdf") -> bool:
        """处理单个URL的完整流程
        
        Args:
            url: 微信文章URL
            format_type: 文件格式 ("pdf" 或 "docx")
            
        Returns:
            是否处理成功
        """
        try:
            url = url.strip()
            logger.info("=" * 60)
            logger.info(f"🎯 开始处理URL: {url[:50]}...")
            
            # 检查URL是否已处理
            if self._is_url_processed(url):
                logger.warning(f"📋 URL已处理，跳过: {url[:50]}...")
                return True
            
            # 验证URL格式
            if not self._is_valid_wechat_url(url):
                logger.error(f"❌ 无效的微信文章URL: {url}")
                self._mark_url_processed(url, None, error="无效URL")
                return False
            
            # 步骤1: 下载文章
            logger.info("📥 步骤1: 下载文章")
            file_path = self.download_article(url, format_type)
            if not file_path:
                self._mark_url_processed(url, None, error="下载失败")
                return False
            
            # 步骤2: 上传到云文档
            logger.info("☁️ 步骤2: 上传到云文档")
            file_token = self.upload_to_drive(file_path)
            
            # 处理重复文件的情况
            if file_token == "DUPLICATE":
                logger.warning(f"📋 文件已存在，跳过处理: {file_path.name}")
                self._mark_url_processed(url, file_path, error="文件已存在")
                return True  # 返回True因为这不是错误
            
            if not file_token:
                self._mark_url_processed(url, file_path, error="云文档上传失败")
                return False
            
            # 步骤3: 移动到知识库
            logger.info("📚 步骤3: 移动到知识库")
            wiki_result = self.move_to_wiki(file_token, file_path.name)
            
            # 🆕 处理重复文件的情况
            if wiki_result in ["DUPLICATE_IN_WIKI", "DUPLICATE_TITLE"]:
                if wiki_result == "DUPLICATE_IN_WIKI":
                    logger.warning(f"🚫 文件已存在于知识库中，停止处理: {file_path.name}")
                    self._mark_url_processed(url, file_path, error="文件已存在于知识库")
                elif wiki_result == "DUPLICATE_TITLE":
                    logger.warning(f"🚫 知识库中已存在同名文档，停止处理: {file_path.name}")
                    self._mark_url_processed(url, file_path, error="知识库中存在同名文档")
                
                # 清理本地文件
                try:
                    if file_path.exists():
                        file_path.unlink()
                        logger.info(f"🗑️ 已清理本地文件: {file_path.name}")
                except Exception as e:
                    logger.warning(f"⚠️ 清理本地文件失败: {e}")
                
                return False  # 返回False表示重复，需要在上层处理
            
            if not wiki_result:
                self._mark_url_processed(url, file_path, error="知识库移动失败")
                return False
            
            # 标记处理完成
            self._mark_url_processed(url, file_path, wiki_result)
            
            logger.success(f"🎉 完整流程处理成功: {file_path.name}")
            return True
            
        except Exception as e:
            logger.error(f"处理URL时出错: {e}")
            self._mark_url_processed(url, None, error=str(e))
            return False
    
    def process_multiple_urls(self, urls: List[str], format_type: str = "pdf", delay: int = 2) -> Dict[str, int]:
        """批量处理多个URL
        
        Args:
            urls: URL列表
            format_type: 文件格式
            delay: 处理间隔（秒）
            
        Returns:
            处理结果统计
        """
        stats = {'total': len(urls), 'success': 0, 'failed': 0, 'skipped': 0}
        
        logger.info(f"🚀 开始批量处理 {stats['total']} 个URL")
        logger.info(f"📄 文件格式: {format_type.upper()}")
        logger.info(f"⏱️ 处理间隔: {delay}秒")
        
        for i, url in enumerate(urls, 1):
            logger.info(f"\n📊 进度: [{i}/{stats['total']}]")
            
            try:
                success = self.process_single_url(url, format_type)
                if success:
                    # 检查是否是跳过的情况
                    if self._is_url_processed(url) and self.upload_log[url].get('error') in [None, "无效URL"]:
                        if "跳过" in str(self.upload_log[url]):
                            stats['skipped'] += 1
                        else:
                            stats['success'] += 1
                    else:
                        stats['success'] += 1
                else:
                    stats['failed'] += 1
                    
            except Exception as e:
                logger.error(f"处理URL {i} 时出错: {e}")
                stats['failed'] += 1
            
            # 添加延迟（最后一个不延迟）
            if i < len(urls) and delay > 0:
                logger.info(f"⏳ 等待 {delay} 秒...")
                time.sleep(delay)
        
        # 输出统计
        logger.info("\n" + "=" * 60)
        logger.info("📊 批量处理完成统计:")
        logger.info(f"  总URL数: {stats['total']}")
        logger.info(f"  成功处理: {stats['success']}")
        logger.info(f"  跳过重复: {stats['skipped']}")
        logger.info(f"  处理失败: {stats['failed']}")
        
        if stats['failed'] == 0:
            logger.success("🎉 全部处理成功！")
        else:
            logger.warning(f"⚠️ 有 {stats['failed']} 个URL处理失败")
        
        return stats
    
    def cleanup(self):
        """清理资源"""
        try:
            if self.url_scraper:
                self.url_scraper.cleanup()
                logger.info("✅ 资源清理完成")
        except Exception as e:
            logger.error(f"资源清理时出错: {e}")

def load_urls_from_file(file_path: str) -> List[str]:
    """从文件加载URL列表"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip()]
        logger.info(f"📄 从文件加载了 {len(urls)} 个URL: {file_path}")
        return urls
    except Exception as e:
        logger.error(f"❌ 加载URL文件失败: {e}")
        return []

def main():
    """主函数 - 支持命令行参数"""
    parser = argparse.ArgumentParser(description='整合版自动下载上传工具')
    parser.add_argument('--input', type=str, help='输入URL文件路径')
    parser.add_argument('--url', type=str, help='单个URL')
    parser.add_argument('--format', type=str, default='pdf', choices=['pdf', 'docx'], help='文件格式')
    parser.add_argument('--delay', type=int, default=3, help='处理间隔（秒）')
    parser.add_argument('--max-files', type=int, help='最大处理文件数')
    parser.add_argument('--auto-mode', action='store_true', help='自动模式（从GitHub Actions调用）')
    
    args = parser.parse_args()
    
    # 初始化上传器
    try:
        uploader = IntegratedAutoUploader()
    except Exception as e:
        logger.error(f"❌ 初始化失败: {e}")
        return
    
    try:
        if args.auto_mode:
            # GitHub Actions自动模式
            logger.info("🚀 GitHub Actions - RO文章自动更新开始")
            logger.info("=" * 60)
            
            # 检查飞书配置
            if os.path.exists('user_feishu_config.json'):
                logger.info("✅ 飞书应用配置已加载")
            else:
                logger.error("❌ 飞书配置文件不存在")
                return
            
            # 处理收集到的文章
            if args.input and os.path.exists(args.input):
                urls = load_urls_from_file(args.input)
                if urls:
                    logger.info(f"📚 步骤3: 处理文章下载上传...")
                    
                    # 限制处理数量
                    if args.max_files and len(urls) > args.max_files:
                        urls = urls[:args.max_files]
                        logger.info(f"📊 限制处理数量为: {args.max_files}")
                    
                    success_count = 0
                    for i, url in enumerate(urls, 1):
                        logger.info(f"📄 处理 {i}/{len(urls)}: {url[:50]}...")
                        logger.info(f"   URL: {url[:80]}...")
                        
                        try:
                            success = uploader.process_single_url(url, args.format)
                            if success:
                                success_count += 1
                                logger.info(f"   ✅ 上传成功")
                            else:
                                logger.info(f"   ❌ 上传失败")
                        except Exception as e:
                            logger.error(f"   ❌ 处理出错: {e}")
                        
                        # 添加延迟
                        if i < len(urls):
                            logger.info(f"   ⏳ 等待 {args.delay} 秒...")
                            time.sleep(args.delay)
                    
                    # 输出统计
                    success_rate = (success_count / len(urls) * 100) if urls else 0
                    logger.info(f"📊 处理完成: {success_count}/{len(urls)} 成功")
                    
                    # GitHub Actions 输出格式
                    print(f"🎉 RO自动更新完成！")
                    print(f"📊 收集文章: {len(urls)} 篇")
                    print(f"📊 成功上传: {success_count}/{len(urls)} 篇")
                    print(f"📊 成功率: {success_rate:.1f}%")
                else:
                    logger.warning("⚠️ 没有找到要处理的URL")
            else:
                logger.error("❌ 输入文件不存在或未指定")
                
        elif args.url:
            # 单个URL处理
            logger.info(f"🎯 处理单个URL: {args.url}")
            success = uploader.process_single_url(args.url, args.format)
            if success:
                logger.success("✅ 处理成功!")
            else:
                logger.error("❌ 处理失败!")
                
        elif args.input:
            # 批量URL处理
            urls = load_urls_from_file(args.input)
            if urls:
                if args.max_files and len(urls) > args.max_files:
                    urls = urls[:args.max_files]
                    logger.info(f"📊 限制处理数量为: {args.max_files}")
                
                stats = uploader.process_multiple_urls(urls, args.format, args.delay)
                logger.info("📊 处理完成")
            else:
                logger.error("❌ 没有找到要处理的URL")
        else:
            # 默认模式
            logger.info("整合版自动上传器已准备就绪")
            logger.info("使用 --help 查看可用参数")
            
    except Exception as e:
        logger.error(f"❌ 运行时错误: {e}")
    finally:
        uploader.cleanup()

if __name__ == "__main__":
    main() 