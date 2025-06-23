#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WeChat Article URL Processor
微信文章URL处理工具

专门处理用户提供的微信文章URL，直接保存为飞书知识库格式
"""

import argparse
import sys
import time
import json
from pathlib import Path
from typing import List, Dict, Any

from loguru import logger
from simple_url_scraper import SimpleUrlScraper
from feishu_exporter import FeishuExporter
from utils import save_to_json
from config import LOG_FILE


def setup_logging(log_level: str = "INFO") -> None:
    """设置日志配置"""
    # 移除默认处理器
    logger.remove()
    
    # 添加控制台处理器
    logger.add(
        sys.stderr,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True
    )
    
    # 添加文件处理器
    logger.add(
        LOG_FILE,
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        rotation="10 MB",
        retention="7 days",
        encoding="utf-8"
    )


def parse_arguments() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="微信文章URL处理工具 - 直接处理URL并保存为多种格式",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
🚀 使用方法：

1. 处理单个URL（PDF格式，保持原始样式）：
   %(prog)s --url "https://mp.weixin.qq.com/s/LiS8ytwKsKP9yAHGp96G_Q" --format pdf

2. 处理URL文件（多种格式）：
   %(prog)s --urls_file urls.txt --format all

3. 处理多个URL（飞书格式）：
   %(prog)s --urls "url1" "url2" "url3" --format individual

4. 无头模式：
   %(prog)s --urls_file urls.txt --headless --format pdf

✨ 特点：
- 🎯 直接处理微信文章URL，无需搜索
- 🖥️ 可见模式便于手动处理验证码
- 📄 完美飞书集成（individual格式）
- 📑 PDF格式保持原始样式和图片
- 🔄 智能重试和错误处理
- 📊 详细的处理统计

📋 格式说明：
- pdf: 保持原始格式的PDF文件（推荐！）
- complete_html: 包含图片的完整HTML文件
- individual: 每篇文章单独Markdown文件（适合飞书）
- markdown: 合并的Markdown文件
- json: 结构化JSON数据
- all: 所有格式都导出

📋 URL格式示例：
   https://mp.weixin.qq.com/s/LiS8ytwKsKP9yAHGp96G_Q
        """
    )
    
    # URL输入方式 (互斥组)
    url_group = parser.add_mutually_exclusive_group(required=True)
    url_group.add_argument(
        '--url',
        type=str,
        help='单个微信文章URL'
    )
    url_group.add_argument(
        '--urls',
        nargs='+',
        help='多个微信文章URL (空格分隔)'
    )
    url_group.add_argument(
        '--urls_file',
        type=str,
        help='包含微信文章URL的文件路径 (每行一个URL)'
    )
    
    # 输出格式
    parser.add_argument(
        '--format',
        choices=['json', 'markdown', 'html', 'individual', 'pdf', 'complete_html', 'all'],
        default='pdf',
        help='输出格式（默认pdf，保持原始格式）'
    )
    
    # 输出选项
    parser.add_argument(
        '--output', '--output_filename',
        type=str,
        help='自定义输出文件名前缀'
    )
    
    # 浏览器选项
    parser.add_argument(
        '--headless',
        action='store_true',
        help='无头模式运行（不显示浏览器窗口）'
    )
    
    # 日志选项
    parser.add_argument(
        '--log_level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='日志级别（默认INFO）'
    )
    
    return parser.parse_args()


def load_urls_from_file(file_path: str) -> List[str]:
    """从文件加载URL列表"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            urls = []
            for line_num, line in enumerate(f, 1):
                url = line.strip()
                # 跳过空行和注释
                if url and not url.startswith('#'):
                    # 验证URL格式
                    if url.startswith('http') and 'mp.weixin.qq.com/s' in url:
                        urls.append(url)
                    else:
                        logger.warning(f"第{line_num}行: 无效的微信文章URL: {url}")
        
        logger.info(f"从文件 {file_path} 加载了 {len(urls)} 个有效URL")
        return urls
        
    except Exception as e:
        logger.error(f"读取URL文件失败: {e}")
        return []


def main() -> int:
    """主函数"""
    try:
        # 解析参数
        args = parse_arguments()
        
        # 设置日志
        setup_logging(args.log_level)
        
        logger.info("=" * 60)
        logger.info("🚀 微信文章URL处理工具启动")
        logger.info("=" * 60)
        
        # 获取URL列表
        urls = []
        
        if args.url:
            urls = [args.url]
            logger.info(f"处理单个URL: {args.url}")
            
        elif args.urls:
            urls = args.urls
            logger.info(f"处理命令行提供的 {len(urls)} 个URL")
            
        elif args.urls_file:
            urls = load_urls_from_file(args.urls_file)
            if not urls:
                logger.error("❌ URL文件为空或读取失败")
                return 1
        
        # 验证URL
        valid_urls = []
        for url in urls:
            if url.startswith('http') and 'mp.weixin.qq.com/s' in url:
                valid_urls.append(url)
            else:
                logger.warning(f"跳过无效URL: {url}")
        
        if not valid_urls:
            logger.error("❌ 没有有效的微信文章URL")
            return 1
        
        logger.info(f"📋 有效URL数量: {len(valid_urls)}")
        logger.info(f"🖥️ 浏览器模式: {'无头模式' if args.headless else '可见模式'}")
        logger.info(f"📄 输出格式: {args.format}")
        
        # 初始化URL处理器
        logger.info("🔧 初始化URL处理器...")
        scraper = SimpleUrlScraper(headless=args.headless)
        
        start_time = time.time()
        
        try:
            # 生成输出文件名
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            if args.output:
                base_filename = args.output
            else:
                base_filename = f"wechat_articles_{timestamp}"
            
            # 导出结果
            success = False
            output_files = []
            
            if args.format == 'pdf' or args.format == 'all':
                # PDF格式 - 保持原始样式
                logger.info("💾 生成PDF文件（保持原始格式）...")
                pdf_dir = f"output/pdf"
                saved_pdfs = scraper.process_urls_as_pdf(valid_urls, pdf_dir)
                
                if saved_pdfs:
                    logger.success(f"✅ 成功生成 {len(saved_pdfs)} 个PDF文件")
                    output_files.append(f"{pdf_dir}/ ({len(saved_pdfs)} 个PDF文件)")
                    success = True
            
            if args.format == 'complete_html' or args.format == 'all':
                # 完整HTML格式 - 包含图片
                logger.info("💾 生成完整HTML文件（包含图片）...")
                html_dir = "output/complete_html"
                html_success_count = 0
                
                from tqdm import tqdm
                for i, url in enumerate(tqdm(valid_urls, desc="生成HTML")):
                    try:
                        # 获取文章信息用于命名
                        article_info = scraper.extract_article_info(url)
                        if 'error' not in article_info:
                            title = article_info.get('title', f'文章_{i+1}')
                            import re
                            safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)[:50]
                            html_filename = f"{i+1:02d}_{safe_title}.html"
                            html_path = f"{html_dir}/{html_filename}"
                            
                            if scraper.save_complete_html(url, html_path):
                                html_success_count += 1
                    except Exception as e:
                        logger.error(f"生成HTML失败: {e}")
                
                if html_success_count > 0:
                    logger.success(f"✅ 成功生成 {html_success_count} 个完整HTML文件")
                    output_files.append(f"{html_dir}/ ({html_success_count} 个HTML文件)")
                    success = True
            
            # 处理传统格式（需要先获取文章内容）
            if args.format in ['json', 'markdown', 'html', 'individual', 'all']:
                logger.info("🚀 开始提取文章内容...")
                articles = scraper.process_urls(valid_urls)
                
                if not articles:
                    logger.warning("⚠️ 未获取到任何文章内容")
                else:
                    logger.info("💾 导出传统格式文件...")
                    
                    if args.format == 'json' or args.format == 'all':
                        # 导出JSON
                        json_filename = f"{base_filename}.json"
                        if save_to_json(articles, json_filename):
                            logger.success(f"✅ JSON已导出: {json_filename}")
                            output_files.append(json_filename)
                            success = True
                    
                    if args.format in ['markdown', 'html', 'individual', 'all']:
                        # 使用飞书导出器
                        exporter = FeishuExporter()
                        
                        if args.format == 'markdown' or args.format == 'all':
                            md_filename = f"{base_filename}.md"
                            if exporter.export_to_markdown(articles, md_filename):
                                output_files.append(md_filename)
                                success = True
                        
                        if args.format == 'html' or args.format == 'all':
                            html_filename = f"{base_filename}.html"
                            if exporter.export_to_html(articles, html_filename):
                                output_files.append(html_filename)
                                success = True
                        
                        if args.format == 'individual' or args.format == 'all':
                            if exporter.export_articles_individually(articles, 'markdown'):
                                output_files.append("output/individual_articles/")
                                success = True
            
            if not success:
                logger.error("❌ 导出失败")
                return 1
            
            # 统计信息
            elapsed_time = time.time() - start_time
            
            logger.info("=" * 60)
            logger.info("📊 处理完成统计")
            logger.info("=" * 60)
            logger.info(f"📄 总URL数量: {len(valid_urls)}")
            logger.info(f"⏱️ 总耗时: {elapsed_time:.2f}秒")
            logger.info(f"🚀 平均耗时: {elapsed_time/len(valid_urls):.2f}秒/篇")
            
            logger.info("\n📁 输出文件:")
            for file in output_files:
                logger.info(f"  📄 {file}")
            
            # 格式使用提示
            if args.format == 'pdf' or args.format == 'all':
                logger.info("\n🎉 PDF格式优势:")
                logger.info("  • 完美保持原文章的所有格式和样式")
                logger.info("  • 包含所有图片、表格、链接等内容")
                logger.info("  • 可直接打印或分享，格式不会改变")
                logger.info("  • 适合存档和正式文档用途")
            
            if args.format == 'complete_html' or args.format == 'all':
                logger.info("\n🌐 完整HTML格式优势:")
                logger.info("  • 保持原始网页格式")
                logger.info("  • 图片下载到本地，离线可用")
                logger.info("  • 可在任何浏览器中打开")
                logger.info("  • 支持复制粘贴到其他应用")
            
            if args.format in ['individual', 'all']:
                logger.info("\n🚀 飞书知识库使用指南:")
                logger.info("  1. 打开 output/individual_articles/ 文件夹")
                logger.info("  2. 选择所有 .md 文件")
                logger.info("  3. 拖拽到飞书知识库进行批量上传")
                logger.info("  4. 每个文件会自动创建为独立的知识库页面")
            
            logger.success("🎉 URL处理任务完成!")
            return 0
            
        finally:
            # 清理资源
            logger.info("🧹 清理资源...")
            scraper.cleanup()
    
    except KeyboardInterrupt:
        logger.warning("⚠️  用户中断操作")
        return 130
    
    except Exception as e:
        logger.error(f"❌ 程序执行失败: {str(e)}")
        logger.debug("详细错误信息:", exc_info=True)
        return 1


def show_usage_examples():
    """显示使用示例"""
    print("\n🚀 微信文章URL处理工具")
    print("=" * 50)
    print("✨ 直接处理微信文章URL，支持多种格式输出")
    print("✨ PDF格式完美保持原文样式和图片")
    print("✨ 完美集成飞书知识库")
    print("")
    print("📋 使用方法示例:")
    print("")
    print("1. 🎯 生成PDF（保持原始格式，推荐！）:")
    print('   python main.py --url "https://mp.weixin.qq.com/s/xxxxx" --format pdf')
    print("")
    print("2. 📁 批量生成PDF:")
    print("   python main.py --urls_file urls.txt --format pdf")
    print("")
    print("3. 🌐 生成完整HTML（包含图片）:")
    print('   python main.py --url "https://mp.weixin.qq.com/s/xxxxx" --format complete_html')
    print("")
    print("4. 📄 飞书格式（Markdown）:")
    print("   python main.py --urls_file urls.txt --format individual")
    print("")
    print("5. 🔧 生成所有格式:")
    print("   python main.py --urls_file urls.txt --format all")
    print("")
    print("6. 🖥️ 无头模式:")
    print("   python main.py --urls_file urls.txt --headless --format pdf")
    print("")
    print("📋 格式说明:")
    print("  • pdf          - PDF文件，保持原始格式（推荐！）")
    print("  • complete_html - 完整HTML，包含图片")
    print("  • individual   - 独立Markdown文件（适合飞书批量上传）")
    print("  • markdown     - 合并Markdown文件")
    print("  • json         - 结构化JSON数据")
    print("  • all          - 所有格式都生成")
    print("")
    print("📋 URL格式要求:")
    print("   https://mp.weixin.qq.com/s/文章ID")
    print("")
    print("🔍 获取完整帮助:")
    print("   python main.py --help")
    print("")


if __name__ == "__main__":
    # 如果没有参数，显示使用示例
    if len(sys.argv) == 1:
        show_usage_examples()
        sys.exit(0)
    
    exit_code = main()
    sys.exit(exit_code) 