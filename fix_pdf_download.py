#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复PDF下载功能的脚本
添加重试机制和更好的错误处理
"""

import os
import base64
import time
from loguru import logger

def fix_save_as_pdf_method():
    """修复simple_url_scraper.py中的save_as_pdf方法"""
    
    # 新的save_as_pdf方法代码
    new_method_code = '''    def save_as_pdf(self, url: str, output_path: str, max_retries: int = 3) -> bool:
        """
        保存URL为PDF - 图片加载优化版本，带重试机制
        确保所有图片完全加载后再生成PDF
        """
        for attempt in range(max_retries):
            try:
                logger.info(f"正在保存PDF: {url} (尝试 {attempt + 1}/{max_retries})")
                
                if not self.driver:
                    self.driver = self.setup_browser(self.headless)
                    if not self.driver:
                        return False
                
                # 1. 访问页面，添加超时和重试机制
                start_time = time.time()
                
                # 设置页面加载超时
                self.driver.set_page_load_timeout(60)  # 60秒超时
                
                try:
                    self.driver.get(url)
                except Exception as e:
                    if "RemoteDisconnected" in str(e) or "Connection aborted" in str(e):
                        logger.warning(f"⚠️ 网络连接中断 (尝试 {attempt + 1}/{max_retries}): {e}")
                        if attempt < max_retries - 1:
                            # 重新初始化浏览器
                            try:
                                self.driver.quit()
                            except:
                                pass
                            self.driver = None
                            time.sleep(2)  # 等待2秒后重试
                            continue
                        else:
                            raise
                    else:
                        raise
                
                # 2. 等待基本内容加载
                self._wait_for_basic_page_load()
                
                # 3. 人类式滚动加载，确保图片完全加载
                self._human_like_scroll_and_load()
                
                # 4. 快速生成PDF（约0.5秒）
                # 滚动回顶部准备生成PDF
                self.driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(0.2)
                
                # 注入CSS样式来消除页面边距和优化排版
                css_style = """
                <style>
                    @page {
                        margin: 0 !important;
                        padding: 0 !important;
                        size: A4 !important;
                    }
                    
                    * {
                        box-sizing: border-box !important;
                    }
                    
                    body, html {
                        margin: 0 !important;
                        padding: 0 !important;
                        width: 100% !important;
                        max-width: 100% !important;
                    }
                    
                    /* 微信文章内容区域优化 */
                    #js_content,
                    .rich_media_content,
                    .rich_media_area_primary {
                        margin: 0 !important;
                        padding: 5px !important;
                        width: 100% !important;
                        max-width: 100% !important;
                    }
                    
                    /* 隐藏不需要的元素 */
                    .rich_media_meta_list,
                    .rich_media_tool,
                    .qr_code_pc_outer,
                    .reward_qrcode_area,
                    .reward_area,
                    #js_pc_qr_code_img,
                    .function_mod,
                    .profile_container,
                    .rich_media_global_msg {
                        display: none !important;
                    }
                </style>
                """
                
                # 将CSS样式注入页面
                self.driver.execute_script(f"""
                    var style = document.createElement('style');
                    style.type = 'text/css';
                    style.innerHTML = `{css_style}`;
                    document.head.appendChild(style);
                """)
                
                # 等待样式生效
                time.sleep(0.3)
                
                # 创建输出目录
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
                # 优化的PDF选项 - 填满页面，消除白边
                pdf_options = {
                    'paperFormat': 'A4',
                    'printBackground': True,
                    'marginTop': 0,        # 完全消除上边距
                    'marginBottom': 0,     # 完全消除下边距  
                    'marginLeft': 0,       # 完全消除左边距
                    'marginRight': 0,      # 完全消除右边距
                    'preferCSSPageSize': True,  # 启用CSS页面大小设置
                    'displayHeaderFooter': False,
                    # 调整缩放以更好地填满页面
                    'scale': 1.0,  # 使用100%缩放，配合CSS样式
                    'landscape': False,
                    # 新增：优化页面利用率
                    'transferMode': 'ReturnAsBase64',
                    'generateTaggedPDF': False  # 简化PDF结构
                }
                
                # 生成PDF
                pdf_data = self.driver.execute_cdp_cmd('Page.printToPDF', pdf_options)
                
                # 保存PDF文件
                with open(output_path, 'wb') as f:
                    f.write(base64.b64decode(pdf_data['data']))
                
                total_time = time.time() - start_time
                logger.success(f"PDF保存成功: {output_path}，总耗时: {total_time:.1f}秒")
                
                # 提示优化后的处理时间
                if total_time <= 30:
                    logger.success("✅ PDF生成完成，图片加载优化生效！")
                else:
                    logger.info(f"ℹ️ 耗时 {total_time:.1f}秒 - 为确保图片完整加载而增加的时间")
                
                return True
                
            except Exception as e:
                if "RemoteDisconnected" in str(e) or "Connection aborted" in str(e):
                    logger.warning(f"⚠️ 网络连接中断 (尝试 {attempt + 1}/{max_retries}): {e}")
                    if attempt < max_retries - 1:
                        # 重新初始化浏览器
                        try:
                            if self.driver:
                                self.driver.quit()
                        except:
                            pass
                        self.driver = None
                        time.sleep(3)  # 等待3秒后重试
                        continue
                    else:
                        logger.error(f"保存PDF失败，已重试{max_retries}次: {e}")
                        return False
                else:
                    logger.error(f"保存PDF失败: {e}")
                    if attempt < max_retries - 1:
                        logger.info(f"尝试重试 ({attempt + 2}/{max_retries})...")
                        time.sleep(2)
                        continue
                    else:
                        return False
        
        return False'''
    
    try:
        # 读取原始文件
        with open('simple_url_scraper.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 找到save_as_pdf方法的开始和结束位置
        start_marker = "    def save_as_pdf(self, url: str, output_path: str"
        end_marker = "    def save_as_docx(self, url: str, output_path: str) -> bool:"
        
        start_pos = content.find(start_marker)
        end_pos = content.find(end_marker)
        
        if start_pos == -1 or end_pos == -1:
            logger.error("无法找到save_as_pdf方法的位置")
            return False
        
        # 替换方法
        new_content = content[:start_pos] + new_method_code + "\n\n" + content[end_pos:]
        
        # 备份原文件
        backup_path = 'simple_url_scraper.py.backup'
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"✅ 已备份原文件到: {backup_path}")
        
        # 写入修复后的文件
        with open('simple_url_scraper.py', 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        logger.success("✅ save_as_pdf方法修复完成！")
        logger.info("📋 修复内容:")
        logger.info("  - 添加了重试机制 (最多3次)")
        logger.info("  - 改进了网络连接错误处理")
        logger.info("  - 增加了浏览器重新初始化逻辑")
        logger.info("  - 优化了错误日志输出")
        
        return True
        
    except Exception as e:
        logger.error(f"修复失败: {e}")
        return False

if __name__ == "__main__":
    logger.info("🚀 开始修复PDF下载功能...")
    
    if fix_save_as_pdf_method():
        logger.success("🎉 PDF下载功能修复完成！")
        logger.info("💡 现在下载功能具备以下特性:")
        logger.info("  ✅ 网络中断自动重试")
        logger.info("  ✅ 浏览器异常自动重启")
        logger.info("  ✅ 详细的错误诊断信息")
        logger.info("  ✅ 智能等待和超时控制")
    else:
        logger.error("❌ 修复失败，请检查错误信息") 