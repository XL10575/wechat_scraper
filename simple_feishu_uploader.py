#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的飞书文件上传器 - 绕过知识库API限制
"""

import os
import requests
import json
from loguru import logger
from typing import Optional

class SimpleFeishuUploader:
    """简化的飞书文件上传器"""
    
    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self.access_token = None
        self.base_url = "https://open.feishu.cn/open-apis"
        
    def get_access_token(self) -> Optional[str]:
        """获取访问令牌"""
        try:
            url = f"{self.base_url}/auth/v3/tenant_access_token/internal"
            payload = {
                "app_id": self.app_id,
                "app_secret": self.app_secret
            }
            
            response = requests.post(url, json=payload)
            response.raise_for_status()
            
            data = response.json()
            if data.get('code') == 0:
                self.access_token = data['tenant_access_token']
                logger.success("飞书访问令牌获取成功")
                return self.access_token
            else:
                logger.error(f"获取访问令牌失败: {data.get('msg')}")
                return None
                
        except Exception as e:
            logger.error(f"获取访问令牌异常: {e}")
            return None
    
    def upload_file_simple(self, file_path: str) -> Optional[str]:
        """简单上传文件到飞书云文档（不依赖知识库）"""
        try:
            if not self.access_token:
                if not self.get_access_token():
                    return None
            
            filename = os.path.basename(file_path)
            logger.info(f"开始上传文件: {filename}")
            
            # 使用简单的文件上传API
            url = f"{self.base_url}/drive/v1/files/upload_all"
            
            headers = {
                'Authorization': f'Bearer {self.access_token}'
            }
            
            # 准备文件和数据
            with open(file_path, 'rb') as f:
                files = {
                    'file': (filename, f, 'application/pdf')
                }
                data = {
                    'file_name': filename,
                    'parent_type': 'explorer'
                }
                
                response = requests.post(url, files=files, data=data, headers=headers)
                
            logger.info(f"上传响应状态: {response.status_code}")
            logger.info(f"上传响应内容: {response.text}")
            
            if response.status_code == 200:
                result = response.json()
                if result.get('code') == 0:
                    file_token = result.get('data', {}).get('file_token')
                    logger.success(f"文件上传成功: {filename}")
                    logger.info(f"文件token: {file_token}")
                    return file_token
                else:
                    logger.error(f"上传失败: {result.get('msg')}")
            else:
                logger.error(f"HTTP上传失败: {response.status_code}")
                
        except Exception as e:
            logger.error(f"上传文件异常: {e}")
        
        return None
    
    def create_shared_link(self, file_token: str) -> Optional[str]:
        """为上传的文件创建分享链接"""
        try:
            url = f"{self.base_url}/drive/v1/permissions/{file_token}/public"
            
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                "link_share_entity": "anyone_readable",
                "is_external_accessible": True
            }
            
            response = requests.patch(url, json=payload, headers=headers)
            logger.info(f"分享链接响应状态: {response.status_code}")
            logger.info(f"分享链接响应内容: {response.text}")
            
            if response.status_code == 200:
                result = response.json()
                if result.get('code') == 0:
                    share_url = result.get('data', {}).get('share_url')
                    logger.success(f"分享链接创建成功: {share_url}")
                    return share_url
                    
        except Exception as e:
            logger.error(f"创建分享链接异常: {e}")
        
        return None


def test_simple_uploader():
    """测试简化上传器"""
    app_id = "cli_a8c822312a75901c"
    app_secret = "25FN3qR3rjX4ylY4mvfn7eUajkEP4mam"
    
    uploader = SimpleFeishuUploader(app_id, app_secret)
    
    # 创建一个测试PDF文件
    test_file = "test_upload.pdf"
    
    # 如果没有测试文件，创建一个简单的文本文件
    if not os.path.exists(test_file):
        logger.info("创建测试文件...")
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write("这是一个测试文件，用于验证飞书上传功能。")
    
    # 测试上传
    file_token = uploader.upload_file_simple(test_file)
    
    if file_token:
        logger.success("上传测试成功！")
        
        # 尝试创建分享链接
        share_url = uploader.create_shared_link(file_token)
        if share_url:
            logger.success(f"文件可通过此链接访问: {share_url}")
    else:
        logger.error("上传测试失败")
    
    # 清理测试文件
    if os.path.exists(test_file):
        os.remove(test_file)

if __name__ == "__main__":
    test_simple_uploader() 