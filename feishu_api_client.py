#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞书API客户端 - Feishu API Client

用于自动上传PDF文件到飞书知识库
"""

import os
import time
import json
import requests
from typing import List, Dict, Any, Optional
from loguru import logger
from datetime import datetime


class FeishuAPIClient:
    """飞书API客户端"""
    
    def __init__(self, app_id: str, app_secret: str):
        """初始化飞书API客户端
        
        Args:
            app_id: 飞书应用ID
            app_secret: 飞书应用密钥
        """
        self.app_id = app_id
        self.app_secret = app_secret
        self.access_token = None
        self.token_expires_at = 0
        
        # API基础URL
        self.base_url = "https://open.feishu.cn/open-apis"
        
        # 初始化请求会话
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'WeChat-PDF-Downloader/1.0'
        })
        
        logger.info("飞书API客户端初始化完成")
    
    def get_access_token(self) -> Optional[str]:
        """获取访问令牌"""
        # 检查token是否还有效
        if self.access_token and time.time() < self.token_expires_at:
            return self.access_token
        
        try:
            url = f"{self.base_url}/auth/v3/tenant_access_token/internal"
            
            payload = {
                "app_id": self.app_id,
                "app_secret": self.app_secret
            }
            
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('code') == 0:
                self.access_token = data['tenant_access_token']
                # token有效期2小时，提前5分钟刷新
                self.token_expires_at = time.time() + data['expire'] - 300
                
                logger.success("飞书访问令牌获取成功")
                return self.access_token
            else:
                logger.error(f"获取访问令牌失败: {data.get('msg', '未知错误')}")
                return None
                
        except Exception as e:
            logger.error(f"获取访问令牌异常: {e}")
            return None
    
    def _make_authenticated_request(self, method: str, url: str, **kwargs) -> Optional[requests.Response]:
        """发送带认证的请求"""
        token = self.get_access_token()
        if not token:
            return None
        
        headers = kwargs.get('headers', {})
        headers['Authorization'] = f'Bearer {token}'
        kwargs['headers'] = headers
        
        try:
            response = self.session.request(method, url, **kwargs)
            if response.status_code != 200:
                logger.error(f"HTTP错误 {response.status_code}: {response.text}")
            response.raise_for_status()
            return response
        except Exception as e:
            logger.error(f"API请求失败: {e}")
            return None
    
    def list_wiki_files(self, space_id: str, parent_node_id: str = None) -> List[Dict]:
        """列出知识库中的文件
        
        Args:
            space_id: 知识库空间ID或space_token
            parent_node_id: 父节点ID，如果为None则列出根目录
            
        Returns:
            文件列表
        """
        try:
            # 直接使用space_id作为space_token
            url = f"{self.base_url}/wiki/v2/spaces/{space_id}/nodes"
            
            params = {
                'page_size': 50
            }
            
            if parent_node_id:
                params['parent_node_id'] = parent_node_id
            
            response = self._make_authenticated_request('GET', url, params=params)
            if not response:
                return []
            
            data = response.json()
            logger.debug(f"API响应: {data}")
            
            if data.get('code') == 0:
                items = data.get('data', {}).get('items', [])
                logger.info(f"获取到 {len(items)} 个文件/文档")
                return items
            else:
                logger.error(f"获取文件列表失败: {data.get('msg', '未知错误')} (code: {data.get('code')})")
                return []
                
        except Exception as e:
            logger.error(f"获取文件列表异常: {e}")
            return []
    
    def check_file_exists(self, space_id: str, filename: str, parent_node_id: str = None) -> bool:
        """检查文件是否已存在
        
        Args:
            space_id: 知识库空间ID
            filename: 文件名
            parent_node_id: 父节点ID
            
        Returns:
            是否存在
        """
        files = self.list_wiki_files(space_id, parent_node_id)
        
        # 去掉文件扩展名进行比较
        base_filename = os.path.splitext(filename)[0]
        
        for file_info in files:
            existing_filename = file_info.get('title', '')
            existing_base = os.path.splitext(existing_filename)[0]
            
            if base_filename == existing_base:
                logger.info(f"文件已存在: {existing_filename}")
                return True
        
        return False
    
    def upload_file_to_drive(self, file_path: str, parent_type: str = "explorer") -> Optional[str]:
        """上传文件到飞书云文档
        
        Args:
            file_path: 本地文件路径
            parent_type: 父节点类型
            
        Returns:
            文件token，如果失败返回None
        """
        try:
            if not os.path.exists(file_path):
                logger.error(f"文件不存在: {file_path}")
                return None
            
            filename = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            
            logger.info(f"开始上传文件: {filename} ({file_size} bytes)")
            
            # 第一步：预上传
            upload_info = self._pre_upload_file(filename, file_size, parent_type)
            if not upload_info:
                return None
            
            # 第二步：上传文件
            file_token = self._upload_file_content(file_path, upload_info)
            if file_token:
                logger.success(f"文件上传成功: {filename}")
                return file_token
            else:
                logger.error(f"文件上传失败: {filename}")
                return None
                
        except Exception as e:
            logger.error(f"上传文件异常: {e}")
            return None
    
    def _pre_upload_file(self, filename: str, file_size: int, parent_type: str) -> Optional[Dict]:
        """预上传文件"""
        try:
            url = f"{self.base_url}/drive/v1/files/upload_prepare"
            
            payload = {
                "file_name": filename,
                "file_size": file_size,
                "parent_type": parent_type
            }
            
            response = self._make_authenticated_request('POST', url, json=payload)
            if not response:
                return None
            
            data = response.json()
            
            if data.get('code') == 0:
                return data.get('data', {})
            else:
                logger.error(f"预上传失败: {data.get('msg', '未知错误')}")
                return None
                
        except Exception as e:
            logger.error(f"预上传异常: {e}")
            return None
    
    def _upload_file_content(self, file_path: str, upload_info: Dict) -> Optional[str]:
        """上传文件内容"""
        try:
            upload_id = upload_info.get('upload_id')
            if not upload_id:
                logger.error("未获取到upload_id")
                return None
            
            url = f"{self.base_url}/drive/v1/files/upload_part"
            
            # 读取文件内容
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            # 准备multipart数据
            files = {
                'file': (os.path.basename(file_path), file_content, 'application/pdf')
            }
            
            data = {
                'upload_id': upload_id,
                'seq': 0  # 分片序号，单文件上传为0
            }
            
            # 移除JSON Content-Type，让requests自动设置multipart
            headers = {'Authorization': f'Bearer {self.get_access_token()}'}
            
            response = self.session.post(url, files=files, data=data, headers=headers)
            response.raise_for_status()
            
            result = response.json()
            
            if result.get('code') == 0:
                # 完成上传
                return self._finish_upload(upload_id)
            else:
                logger.error(f"上传文件内容失败: {result.get('msg', '未知错误')}")
                return None
                
        except Exception as e:
            logger.error(f"上传文件内容异常: {e}")
            return None
    
    def _finish_upload(self, upload_id: str) -> Optional[str]:
        """完成文件上传"""
        try:
            url = f"{self.base_url}/drive/v1/files/upload_finish"
            
            payload = {
                "upload_id": upload_id,
                "block_num": 1  # 分片数量
            }
            
            response = self._make_authenticated_request('POST', url, json=payload)
            if not response:
                return None
            
            data = response.json()
            
            if data.get('code') == 0:
                file_token = data.get('data', {}).get('file_token')
                return file_token
            else:
                logger.error(f"完成上传失败: {data.get('msg', '未知错误')}")
                return None
                
        except Exception as e:
            logger.error(f"完成上传异常: {e}")
            return None
    
    def create_wiki_node(self, space_id: str, title: str, file_token: str, parent_node_id: str = None) -> Optional[str]:
        """在知识库中创建节点
        
        Args:
            space_id: 知识库空间ID
            title: 节点标题
            file_token: 文件token
            parent_node_id: 父节点ID
            
        Returns:
            节点ID，如果失败返回None
        """
        try:
            url = f"{self.base_url}/wiki/v2/spaces/{space_id}/nodes"
            
            payload = {
                "obj_type": "file",
                "title": title,
                "obj_token": file_token
            }
            
            if parent_node_id:
                payload["parent_node_id"] = parent_node_id
            
            response = self._make_authenticated_request('POST', url, json=payload)
            if not response:
                return None
            
            data = response.json()
            
            if data.get('code') == 0:
                node_id = data.get('data', {}).get('node', {}).get('node_id')
                logger.success(f"知识库节点创建成功: {title}")
                return node_id
            else:
                logger.error(f"创建知识库节点失败: {data.get('msg', '未知错误')}")
                return None
                
        except Exception as e:
            logger.error(f"创建知识库节点异常: {e}")
            return None
    
    def upload_pdf_to_wiki(self, file_path: str, space_id: str, parent_node_id: str = None) -> bool:
        """上传PDF到飞书知识库
        
        Args:
            file_path: PDF文件路径
            space_id: 知识库空间ID
            parent_node_id: 父节点ID
            
        Returns:
            是否成功
        """
        try:
            filename = os.path.basename(file_path)
            
            # 检查文件是否已存在
            if self.check_file_exists(space_id, filename, parent_node_id):
                logger.warning(f"文件已存在，跳过上传: {filename}")
                return True
            
            # 上传文件到云文档
            file_token = self.upload_file_to_drive(file_path)
            if not file_token:
                return False
            
            # 在知识库中创建节点
            title = os.path.splitext(filename)[0]  # 去掉.pdf扩展名
            node_id = self.create_wiki_node(space_id, title, file_token, parent_node_id)
            
            if node_id:
                logger.success(f"PDF文件已成功上传到飞书知识库: {filename}")
                return True
            else:
                logger.error(f"创建知识库节点失败: {filename}")
                return False
                
        except Exception as e:
            logger.error(f"上传PDF到知识库异常: {e}")
            return False


    def get_space_info_by_token(self, space_token: str) -> Optional[Dict]:
        """通过space_token获取知识库信息
        
        Args:
            space_token: 知识库token
            
        Returns:
            知识库信息，包含space_id
        """
        try:
            # 使用get_node API，这个可以通过token参数工作
            url = f"{self.base_url}/wiki/v2/spaces/get_node"
            
            response = self._make_authenticated_request('GET', url, params={'token': space_token})
            if not response:
                return None
            
            data = response.json()
            logger.debug(f"知识库信息API响应: {data}")
            
            if data.get('code') == 0:
                node_info = data.get('data', {}).get('node', {})
                # 从node信息中提取space信息
                space_info = {
                    'space_id': node_info.get('space_id'),
                    'title': node_info.get('title'),
                    'node_token': node_info.get('node_token'),
                    'name': node_info.get('title')  # 为了兼容性添加name字段
                }
                logger.info(f"获取到知识库信息: {space_info.get('name', 'Unknown')}")
                return space_info
            else:
                logger.error(f"获取知识库信息失败: {data.get('msg', '未知错误')} (code: {data.get('code')})")
                return None
                
        except Exception as e:
            logger.error(f"获取知识库信息异常: {e}")
            return None


def test_feishu_api():
    """测试飞书API功能"""
    # 测试配置
    app_id = "cli_a8c822312a75901c"
    app_secret = "25FN3qR3rjX4ylY4mvfn7eUajkEP4mam"
    space_token = "Rkr5w3y8hib7dRk1KpFcMZ7tnGc"  # 这是space_token
    
    # 初始化客户端
    client = FeishuAPIClient(app_id, app_secret)
    
    # 测试获取访问令牌
    token = client.get_access_token()
    if token:
        logger.success("访问令牌获取成功")
        
        # 先通过space_token获取space_id
        space_info = client.get_space_info_by_token(space_token)
        if space_info:
            space_id = space_info.get('space_id')
            logger.info(f"获取到space_id: {space_id}")
            
            if space_id:
                # 使用正确的space_id测试文件列表
                files = client.list_wiki_files(space_id)
                logger.info(f"知识库中有 {len(files)} 个文件/文档")
                
                # 测试上传功能
                test_pdf = "output/auto_download/test.pdf"
                if os.path.exists(test_pdf):
                    success = client.upload_pdf_to_wiki(test_pdf, space_id)
                    if success:
                        logger.success("测试上传成功")
                    else:
                        logger.error("测试上传失败")
                else:
                    logger.info("没有找到测试PDF文件，跳过上传测试")
            else:
                logger.error("无法获取space_id")
        else:
            logger.error("无法获取知识库信息")
    else:
        logger.error("访问令牌获取失败")


if __name__ == "__main__":
    test_feishu_api() 