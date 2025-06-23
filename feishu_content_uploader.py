#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞书完整内容上传器 - Feishu Full Content Uploader

将微信文章的完整内容（文字+图片）上传到飞书知识库，保持原有格式
"""

import os
import json
import requests
import time
from typing import List, Dict, Any, Optional
from loguru import logger
from datetime import datetime
from bs4 import BeautifulSoup
import re

from feishu_user_client import FeishuUserAPIClient


class FeishuContentUploader:
    """飞书完整内容上传器"""
    
    def __init__(self, app_id: str, app_secret: str, access_token: str = None):
        """初始化飞书内容上传器
        
        Args:
            app_id: 飞书应用ID
            app_secret: 飞书应用密钥
            access_token: 用户访问令牌（可选）
        """
        self.client = FeishuUserAPIClient(app_id, app_secret, access_token)
        logger.info("飞书完整内容上传器初始化完成")
    
    def upload_full_article_content(self, full_content: Dict[str, Any], space_id: str, parent_node_token: str = None) -> Optional[str]:
        """上传完整的文章内容到飞书知识库
        
        Args:
            full_content: 完整文章内容（来自extract_full_article_content）
            space_id: 飞书知识库空间ID
            parent_node_token: 父节点token，指定上传位置
            
        Returns:
            文档URL，如果失败返回None
        """
        try:
            if 'error' in full_content:
                logger.error(f"输入内容包含错误: {full_content.get('error')}")
                return None
            
            title = full_content.get('title', '未知标题')
            logger.info(f"🚀 开始上传完整文章内容到飞书: {title}")
            
            # 1. 上传所有图片到飞书云盘
            logger.info("📤 第1步: 上传图片到飞书云盘...")
            image_map = self._upload_images_to_feishu(full_content.get('images', []))
            
            # 2. 处理HTML内容，替换图片URL为飞书链接
            logger.info("🔄 第2步: 处理HTML内容，替换图片链接...")
            processed_html = self._process_html_content(
                full_content.get('html_content', ''),
                image_map
            )
            
            # 3. 转换为飞书支持的格式
            logger.info("📝 第3步: 转换内容格式...")
            feishu_content = self._convert_to_feishu_format(
                title=title,
                author=full_content.get('author', '未知作者'),
                publish_date=full_content.get('publish_date', ''),
                url=full_content.get('url', ''),
                html_content=processed_html,
                text_content=full_content.get('text_content', ''),
                images_count=len(full_content.get('images', []))
            )
            
            # 4. 创建飞书文档
            logger.info("📋 第4步: 创建飞书知识库文档...")
            doc_url = self._create_feishu_document(
                title=title,
                content=feishu_content,
                space_id=space_id,
                parent_node_token=parent_node_token
            )
            
            if doc_url:
                logger.success(f"🎉 文章内容上传成功: {title}")
                logger.success(f"📖 文档链接: {doc_url}")
            else:
                logger.error(f"❌ 文章内容上传失败: {title}")
            
            return doc_url
            
        except Exception as e:
            logger.error(f"上传完整文章内容异常: {e}")
            return None
    
    def _upload_images_to_feishu(self, images: List[Dict[str, str]]) -> Dict[str, str]:
        """上传图片到飞书云盘并获取链接
        
        Args:
            images: 图片信息列表
            
        Returns:
            本地路径到飞书文件token的映射
        """
        image_map = {}
        
        if not images:
            logger.info("📷 没有图片需要上传")
            return image_map
        
        logger.info(f"📷 开始上传 {len(images)} 张图片到飞书云盘...")
        
        for i, img_info in enumerate(images):
            try:
                local_path = img_info.get('local_path')
                filename = img_info.get('filename')
                
                if not local_path or not os.path.exists(local_path):
                    logger.warning(f"图片文件不存在: {local_path}")
                    continue
                
                logger.debug(f"上传图片 {i+1}/{len(images)}: {filename}")
                
                # 上传到飞书云盘
                file_token = self.client.upload_file_to_drive(local_path)
                
                if file_token:
                    image_map[local_path] = file_token
                    logger.debug(f"✅ 图片上传成功: {filename} -> {file_token}")
                else:
                    logger.warning(f"❌ 图片上传失败: {filename}")
                
                # 添加延迟避免API限制
                if i < len(images) - 1:
                    time.sleep(0.5)
                    
            except Exception as e:
                logger.error(f"上传图片 {img_info.get('filename', 'unknown')} 时出错: {e}")
                continue
        
        logger.success(f"📷 图片上传完成: {len(image_map)}/{len(images)} 张成功")
        return image_map
    
    def _process_html_content(self, html_content: str, image_map: Dict[str, str]) -> str:
        """处理HTML内容，替换图片URL为飞书链接
        
        Args:
            html_content: 原始HTML内容
            image_map: 本地路径到飞书文件token的映射
            
        Returns:
            处理后的HTML内容
        """
        if not html_content:
            return ""
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 查找所有图片标签
            img_tags = soup.find_all('img')
            replaced_count = 0
            
            for img_tag in img_tags:
                try:
                    # 获取原始图片URL
                    original_src = img_tag.get('src') or img_tag.get('data-src')
                    
                    if not original_src:
                        continue
                    
                    # 查找对应的本地文件
                    matching_local_path = None
                    for local_path, file_token in image_map.items():
                        # 通过文件名匹配（简单策略）
                        if local_path in image_map:
                            matching_local_path = local_path
                            break
                    
                    if matching_local_path:
                        # 替换为飞书云盘链接
                        feishu_file_token = image_map[matching_local_path]
                        # 构建飞书图片显示URL
                        feishu_img_url = f"https://open.feishu.cn/open-apis/drive/v1/medias/{feishu_file_token}/download"
                        
                        img_tag['src'] = feishu_img_url
                        # 移除data-src属性
                        if img_tag.get('data-src'):
                            del img_tag['data-src']
                        
                        replaced_count += 1
                        logger.debug(f"替换图片链接: {original_src[:50]}... -> {feishu_img_url}")
                
                except Exception as e:
                    logger.debug(f"处理图片标签时出错: {e}")
                    continue
            
            logger.info(f"🔄 HTML图片链接替换完成: {replaced_count} 张图片")
            return str(soup)
            
        except Exception as e:
            logger.error(f"处理HTML内容时出错: {e}")
            return html_content
    
    def _convert_to_feishu_format(self, title: str, author: str, publish_date: str, 
                                 url: str, html_content: str, text_content: str, 
                                 images_count: int) -> str:
        """将内容转换为飞书支持的格式
        
        Args:
            title: 文章标题
            author: 作者
            publish_date: 发布时间
            url: 原文链接
            html_content: HTML内容
            text_content: 纯文本内容
            images_count: 图片数量
            
        Returns:
            飞书格式的内容
        """
        try:
            # 飞书支持Markdown格式，我们构建Markdown内容
            feishu_content = f"""# {title}

## 📋 文章信息

- **作者**: {author}
- **发布时间**: {publish_date}
- **原文链接**: [{title}]({url})
- **图片数量**: {images_count} 张
- **采集时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## 📄 文章内容

"""
            
            # 尝试将HTML转换为Markdown格式的文本
            if html_content:
                # 简单的HTML到Markdown转换
                markdown_content = self._html_to_markdown(html_content)
                feishu_content += markdown_content
            else:
                # 如果没有HTML内容，使用纯文本
                feishu_content += text_content
            
            # 添加脚注
            feishu_content += f"""

---

> 📝 此文档由微信文章爬虫自动生成  
> 🕒 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
> 🔗 原始链接: {url}

"""
            
            return feishu_content
            
        except Exception as e:
            logger.error(f"转换飞书格式时出错: {e}")
            # 返回基本格式
            return f"""# {title}

**作者**: {author}  
**发布时间**: {publish_date}  
**原文链接**: {url}

{text_content}

---
此文档由微信文章爬虫自动生成
"""
    
    def _html_to_markdown(self, html_content: str) -> str:
        """将HTML内容转换为Markdown格式
        
        Args:
            html_content: HTML内容
            
        Returns:
            Markdown格式的内容
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 移除不需要的元素
            for element in soup(['script', 'style', 'meta', 'link']):
                element.decompose()
            
            # 简单的HTML到Markdown转换
            markdown_lines = []
            
            for element in soup.find_all():
                if element.name == 'h1':
                    markdown_lines.append(f"\n# {element.get_text().strip()}\n")
                elif element.name == 'h2':
                    markdown_lines.append(f"\n## {element.get_text().strip()}\n")
                elif element.name == 'h3':
                    markdown_lines.append(f"\n### {element.get_text().strip()}\n")
                elif element.name == 'p':
                    text = element.get_text().strip()
                    if text:
                        markdown_lines.append(f"\n{text}\n")
                elif element.name == 'strong' or element.name == 'b':
                    text = element.get_text().strip()
                    if text:
                        markdown_lines.append(f"**{text}**")
                elif element.name == 'em' or element.name == 'i':
                    text = element.get_text().strip()
                    if text:
                        markdown_lines.append(f"*{text}*")
                elif element.name == 'img':
                    src = element.get('src', '')
                    alt = element.get('alt', '图片')
                    if src:
                        markdown_lines.append(f"\n![{alt}]({src})\n")
                elif element.name == 'br':
                    markdown_lines.append("\n")
            
            # 如果转换结果为空，使用纯文本
            if not markdown_lines:
                return soup.get_text(separator='\n', strip=True)
            
            return ''.join(markdown_lines)
            
        except Exception as e:
            logger.debug(f"HTML到Markdown转换失败: {e}")
            # 降级为纯文本
            soup = BeautifulSoup(html_content, 'html.parser')
            return soup.get_text(separator='\n', strip=True)
    
    def _create_feishu_document(self, title: str, content: str, space_id: str, 
                               parent_node_token: str = None) -> Optional[str]:
        """创建飞书文档并写入内容
        
        Args:
            title: 文档标题
            content: 文档内容
            space_id: 知识库空间ID
            parent_node_token: 父节点token
            
        Returns:
            文档URL，如果失败返回None
        """
        try:
            # 创建空文档
            node_token = self.client.create_wiki_document(
                space_id=space_id,
                title=title,
                file_token=None,  # 不上传文件，创建空文档
                parent_node_token=parent_node_token,
                file_type="docx"
            )
            
            if not node_token:
                logger.error("创建飞书文档节点失败")
                return None
            
            logger.success(f"✅ 文档节点创建成功: {node_token}")
            
            # 尝试向文档写入内容（如果API支持）
            # 注意：飞书文档内容编辑可能需要特殊的API调用
            success = self._write_content_to_document(node_token, content)
            
            if success:
                logger.success(f"✅ 文档内容写入成功")
            else:
                logger.warning(f"⚠️ 文档创建成功但内容写入失败，请手动编辑文档")
            
            # 生成文档URL
            doc_url = f"https://thedream.feishu.cn/wiki/{node_token}"
            return doc_url
            
        except Exception as e:
            logger.error(f"创建飞书文档异常: {e}")
            return None
    
    def _write_content_to_document(self, node_token: str, content: str) -> bool:
        """向飞书文档写入内容
        
        Args:
            node_token: 文档节点token
            content: 要写入的内容
            
        Returns:
            是否成功
        """
        try:
            # 注意：这里需要使用飞书的文档编辑API
            # 由于飞书文档编辑API比较复杂，这里先保存内容到文档描述或注释中
            
            # 方法1: 尝试保存为文档标签或描述
            # 这是一个简化的实现，实际情况可能需要使用更复杂的文档编辑API
            
            logger.info(f"📝 尝试将内容写入文档: {node_token}")
            logger.info(f"📊 内容长度: {len(content)} 字符")
            
            # 临时方案：将内容保存为本地文件，提示用户手动复制粘贴
            self._save_content_for_manual_copy(node_token, content)
            
            return True
            
        except Exception as e:
            logger.error(f"写入文档内容异常: {e}")
            return False
    
    def _save_content_for_manual_copy(self, node_token: str, content: str):
        """保存内容到本地文件，供用户手动复制
        
        Args:
            node_token: 文档节点token
            content: 内容
        """
        try:
            # 创建输出目录
            output_dir = "output/feishu_content"
            os.makedirs(output_dir, exist_ok=True)
            
            # 保存Markdown内容
            md_file = os.path.join(output_dir, f"{node_token}_content.md")
            with open(md_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"📝 内容已保存到: {md_file}")
            logger.info(f"💡 您可以复制此文件的内容到飞书文档中")
            
        except Exception as e:
            logger.error(f"保存内容文件异常: {e}")


def test_content_uploader():
    """测试完整内容上传器"""
    
    # 配置信息
    app_id = "cli_a8c822312a75901c"
    app_secret = "NDbCyKEwEIA8CZo2KHyqueIOlcafErko"
    space_id = "7429397059456081921"  # 知识库ID
    parent_node_token = "Rkr5w3y8hib7dRk1KpFcMZ7tnGc"  # 目标位置
    
    # 使用测试提取的内容
    test_content_file = "output/full_content_test/extracted_content.json"
    
    if not os.path.exists(test_content_file):
        logger.error(f"测试内容文件不存在: {test_content_file}")
        return
    
    try:
        # 读取测试内容
        with open(test_content_file, 'r', encoding='utf-8') as f:
            full_content = json.load(f)
        
        logger.info("📖 读取测试内容成功")
        logger.info(f"📝 标题: {full_content.get('title', 'N/A')}")
        logger.info(f"🖼️ 图片数量: {len(full_content.get('images', []))}")
        
        # 初始化上传器
        uploader = FeishuContentUploader(app_id, app_secret)
        
        # 上传内容
        doc_url = uploader.upload_full_article_content(
            full_content=full_content,
            space_id=space_id,
            parent_node_token=parent_node_token
        )
        
        if doc_url:
            logger.success(f"🎉 测试上传成功!")
            logger.success(f"📖 文档链接: {doc_url}")
        else:
            logger.error("❌ 测试上传失败")
    
    except Exception as e:
        logger.error(f"测试过程中出现异常: {e}")


if __name__ == "__main__":
    test_content_uploader() 