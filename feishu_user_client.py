#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞书用户身份API客户端 - Feishu User API Client

支持用户身份权限的飞书API客户端，支持完整的文件上传功能
"""

import os
import time
import json
import requests
from typing import List, Dict, Any, Optional
from loguru import logger
from datetime import datetime
import webbrowser
from urllib.parse import urlencode, parse_qs, urlparse
from feishu_oauth_client import FeishuOAuth2Client


class FeishuUserAPIClient:
    """飞书用户身份API客户端 - 集成OAuth2令牌管理"""
    
    def __init__(self, app_id: str, app_secret: str, access_token: str = None):
        """初始化飞书用户API客户端
        
        Args:
            app_id: 飞书应用ID
            app_secret: 飞书应用密钥
            access_token: 可选的访问令牌（会被OAuth2管理覆盖）
        """
        self.app_id = app_id
        self.app_secret = app_secret
        self.base_url = "https://open.feishu.cn/open-apis"
        
        # 初始化OAuth2客户端
        self.oauth_client = FeishuOAuth2Client(app_id, app_secret)
        
        # 优先使用OAuth2管理的token
        self.access_token = self.oauth_client.get_valid_access_token()
        if not self.access_token and access_token:
            logger.warning("OAuth2令牌不可用，使用提供的访问令牌")
            self.access_token = access_token
        
        logger.info("飞书用户身份API客户端初始化完成")
    
    def ensure_valid_token(self) -> bool:
        """确保有有效的访问令牌"""
        self.access_token = self.oauth_client.get_valid_access_token()
        
        if not self.access_token:
            logger.warning("没有有效的访问令牌，需要进行OAuth2授权")
            if self.oauth_client.start_oauth_flow():
                self.access_token = self.oauth_client.get_valid_access_token()
                if self.access_token:
                    logger.success("✅ OAuth2授权成功，获取到新的访问令牌")
                    return True
            
            logger.error("❌ 无法获取有效的访问令牌")
            return False
        
        return True
    
    def get_user_access_token(self) -> Optional[str]:
        """获取用户访问令牌（兼容性方法）"""
        return self.oauth_client.get_valid_access_token()
    
    def _exchange_code_for_token(self, code: str, redirect_uri: str) -> Optional[str]:
        """用授权码换取访问令牌（已废弃，使用OAuth2客户端）"""
        logger.warning("此方法已废弃，请使用OAuth2客户端")
        return None
    
    def set_access_token(self, access_token: str):
        """设置访问令牌"""
        self.access_token = access_token
    
    def _make_authenticated_request(self, method: str, url: str, **kwargs) -> Optional[requests.Response]:
        """发送带认证的请求"""
        if not self.access_token:
            logger.error("❌ 没有可用的访问令牌")
            return None
        
        headers = kwargs.get('headers', {})
        headers['Authorization'] = f'Bearer {self.access_token}'
        kwargs['headers'] = headers
        
        try:
            logger.debug(f"🌐 发送{method}请求: {url}")
            if 'json' in kwargs:
                logger.debug(f"📋 请求体: {json.dumps(kwargs['json'], indent=2, ensure_ascii=False)}")
            
            response = requests.request(method, url, **kwargs)
            
            logger.debug(f"📡 HTTP状态码: {response.status_code}")
            logger.debug(f"📝 响应头: {dict(response.headers)}")
            
            # 🆕 飞书API特殊处理：即使HTTP 200也要检查业务状态码
            if response.status_code == 200:
                try:
                    result = response.json()
                    business_code = result.get('code')
                    business_msg = result.get('msg', '无消息')
                    
                    logger.debug(f"🏢 业务状态码: {business_code}")
                    logger.debug(f"📝 业务消息: {business_msg}")
                    
                    if business_code != 0:
                        logger.warning(f"⚠️ 飞书API业务失败 - HTTP: 200, 业务代码: {business_code}")
                        logger.warning(f"📝 错误消息: {business_msg}")
                        logger.warning(f"📄 完整响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
                        
                        # 详细错误分析
                        if business_code == 230005:
                            logger.error("💡 错误230005详解: obj_type参数不正确或文档类型不支持")
                        elif business_code == 99991663:
                            logger.error("💡 错误99991663详解: 权限不足，无法移动云文档到知识库")
                        elif business_code == 1254050:
                            logger.error("💡 错误1254050详解: 文档不存在或已被删除")
                        elif business_code == 400:
                            logger.error("💡 错误400详解: 请求参数格式错误")
                        else:
                            logger.error(f"💡 未知业务错误代码: {business_code}")
                    else:
                        logger.debug(f"✅ 飞书API业务成功: HTTP 200, 业务代码: 0")
                        
                except json.JSONDecodeError:
                    logger.debug(f"📄 非JSON响应: {response.text[:200]}...")
            else:
                logger.error(f"❌ HTTP错误 {response.status_code}")
                logger.error(f"📄 错误响应内容: {response.text}")
                
                # 不对非200状态码抛出异常，而是返回响应让调用者处理
                return response
            
            return response
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ 网络请求异常: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ API请求失败: {e}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")
            return None
    
    def get_space_info_by_token(self, space_token: str) -> Optional[Dict]:
        """通过space_token获取知识库信息"""
        try:
            url = f"{self.base_url}/wiki/v2/spaces/get_node"
            
            response = self._make_authenticated_request('GET', url, params={'token': space_token})
            if not response:
                return None
            
            data = response.json()
            logger.debug(f"知识库信息API响应: {data}")
            
            if data.get('code') == 0:
                node_info = data.get('data', {}).get('node', {})
                space_info = {
                    'space_id': node_info.get('space_id'),
                    'title': node_info.get('title'),
                    'node_token': node_info.get('node_token'),
                    'name': node_info.get('title')
                }
                logger.info(f"获取到知识库信息: {space_info.get('name', 'Unknown')}")
                return space_info
            else:
                logger.error(f"获取知识库信息失败: {data.get('msg', '未知错误')} (code: {data.get('code')})")
                return None
                
        except Exception as e:
            logger.error(f"获取知识库信息异常: {e}")
            return None

    def get_wiki_node_info(self, node_token: str) -> Optional[Dict]:
        """获取知识库页面信息，包括space_id等"""
        try:
            url = f"{self.base_url}/wiki/v2/spaces/get_node"
            
            response = self._make_authenticated_request('GET', url, params={'token': node_token})
            if not response:
                return None
            
            data = response.json()
            logger.debug(f"获取页面信息API响应: {data}")
            
            if data.get('code') == 0:
                node_info = data.get('data', {}).get('node', {})
                return node_info
            else:
                logger.error(f"获取页面信息失败: {data.get('msg', '未知错误')} (code: {data.get('code')})")
                return None
                
        except Exception as e:
            logger.error(f"获取页面信息异常: {e}")
            return None
    
    def test_permissions(self) -> Dict[str, bool]:
        """测试用户权限"""
        permissions = {
            'wiki_access': False,
            'drive_access': False,
            'file_upload': False
        }
        
        try:
            # 测试知识库权限
            url = f"{self.base_url}/wiki/v2/spaces"
            response = self._make_authenticated_request('GET', url, params={'page_size': 10})
            
            if response and response.status_code == 200:
                data = response.json()
                if data.get('code') == 0:
                    permissions['wiki_access'] = True
                    logger.success("✅ 知识库权限正常")
                else:
                    logger.warning(f"⚠️ 知识库权限问题: {data.get('msg')}")
            
            # 测试云文档权限
            url = f"{self.base_url}/drive/v1/files"
            response = self._make_authenticated_request('GET', url, params={'page_size': 10})
            
            if response and response.status_code == 200:
                data = response.json()
                if data.get('code') == 0:
                    permissions['drive_access'] = True
                    permissions['file_upload'] = True  # 如果能访问drive，通常也能上传
                    logger.success("✅ 云文档和文件上传权限正常")
                else:
                    logger.warning(f"⚠️ 云文档权限问题: {data.get('msg')}")
            
        except Exception as e:
            logger.error(f"权限测试异常: {e}")
        
        return permissions
    
    def upload_file_to_drive(self, file_path: str, parent_node: str = None, parent_type: str = "explorer") -> Optional[str]:
        """上传文件到飞书云文档或知识库
        
        Args:
            file_path: 文件路径
            parent_node: 父节点token/ID，用于指定上传位置
            parent_type: 父节点类型，"explorer"为云文档，"knowledge_space"为知识库
        """
        try:
            if not os.path.exists(file_path):
                logger.error(f"文件不存在: {file_path}")
                return None
            
            filename = os.path.basename(file_path)
            logger.info(f"🚀 开始上传文件: {filename}")
            
            # 使用正确的上传API
            url = f"{self.base_url}/drive/v1/files/upload_all"
            
            # 先读取文件内容，确保获取准确的文件大小
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            # 确保文件内容不为空
            if not file_content:
                logger.error(f"❌ 文件内容为空: {file_path}")
                return None
            
            # 使用实际读取的文件内容大小，而不是os.path.getsize()
            actual_file_size = len(file_content)
            logger.info(f"📏 文件大小: {actual_file_size} bytes")
            
            # 根据飞书API规范，使用统一的MIME类型
            # 飞书建议PDF等二进制文件统一使用 application/octet-stream
            file_ext = filename.lower().split('.')[-1] if '.' in filename else ''
            if file_ext == 'pdf':
                mime_type = 'application/octet-stream'  # 飞书推荐的PDF上传MIME类型
            else:
                # 其他文件类型的MIME映射
                mime_types = {
                    'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    'doc': 'application/msword',
                    'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    'xls': 'application/vnd.ms-excel',
                    'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                    'ppt': 'application/vnd.ms-powerpoint',
                    'txt': 'text/plain',
                    'md': 'text/markdown',
                    'html': 'text/html',
                    'json': 'application/json'
                }
                mime_type = mime_types.get(file_ext, 'application/octet-stream')
            
            logger.debug(f"📋 文件信息: {filename}, MIME类型: {mime_type}")
            
            # 准备上传参数（所有值必须是字符串，确保无空格）
            upload_data = {
                'file_name': filename.strip(),  # 移除可能的空格
                'parent_type': parent_type.strip(),
                'size': str(actual_file_size).strip()  # 确保size无空格且不为0
            }
            
            # 验证size不为0
            if actual_file_size <= 0:
                logger.error(f"❌ 文件大小无效: {actual_file_size}")
                return None
            
            # 如果指定了parent_node，添加到上传参数中
            if parent_node:
                upload_data['parent_node'] = parent_node
                if parent_type == "knowledge_space":
                    logger.info(f"📚 上传到知识库空间: {parent_node}")
                else:
                    logger.info(f"📁 上传到云文档文件夹: {parent_node}")
            
            # 使用requests-toolbelt的MultipartEncoder确保正确的multipart/form-data格式
            try:
                from requests_toolbelt import MultipartEncoder
                
                # 构造multipart数据，确保所有值都是字符串且不含空格
                multipart_data = {
                    'file_name': upload_data['file_name'].strip(),
                    'parent_type': upload_data['parent_type'].strip(), 
                    'size': upload_data['size'].strip(),
                    'file': (filename.strip(), file_content, mime_type)
                }
                
                # 添加parent_node（如果存在）
                if 'parent_node' in upload_data:
                    multipart_data['parent_node'] = upload_data['parent_node'].strip()
                
                logger.debug(f"📋 上传参数: file_name={multipart_data['file_name']}, parent_type={multipart_data['parent_type']}, size={multipart_data['size']}")
                
                encoder = MultipartEncoder(fields=multipart_data)
                
                upload_headers = {
                    'Authorization': f'Bearer {self.access_token}',
                    'Content-Type': encoder.content_type  # 自动设置为multipart/form-data with boundary
                }
                
                logger.info(f"📤 使用MultipartEncoder发送上传请求...")
                logger.debug(f"Content-Type: {encoder.content_type}")
                response = requests.post(url, headers=upload_headers, data=encoder)
                
            except ImportError:
                # 如果没有requests-toolbelt，回退到标准requests方式
                logger.warning("⚠️ 未安装requests-toolbelt，使用标准requests方式")
                
                # 构造标准的files和data参数
                files = {
                    'file': (filename, file_content, mime_type)
                }
                
                upload_headers = {
                    'Authorization': f'Bearer {self.access_token}'
                    # 不设置Content-Type，让requests自动处理multipart/form-data
                }
                
                logger.info(f"📤 使用标准requests发送上传请求...")
                response = requests.post(url, headers=upload_headers, files=files, data=upload_data)
            
            logger.info(f"🔄 上传响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    logger.debug(f"📄 上传响应: {result}")
                    
                    if result.get('code') == 0:
                        file_token = result.get('data', {}).get('file_token')
                        logger.success(f"✅ 文件上传成功: {filename}")
                        logger.info(f"🔗 文件token: {file_token}")
                        return file_token
                    else:
                        error_code = result.get('code')
                        error_msg = result.get('msg', '未知错误')
                        logger.error(f"❌ 飞书API错误 {error_code}: {error_msg}")
                        
                        # 特殊处理常见错误
                        if error_code == 1062009:
                            logger.error("💡 错误1062009: size参数与文件实际大小不一致")
                        elif error_code == 1061002:
                            logger.error("💡 错误1061002: boundary格式错误")
                        elif error_code == 234006:
                            logger.error("💡 错误234006: 文件超过大小限制")
                        
                        return None
                except json.JSONDecodeError as e:
                    logger.error(f"❌ 响应JSON解析失败: {e}")
                    logger.debug(f"原始响应: {response.text}")
                    return None
            else:
                logger.error(f"❌ HTTP错误: {response.status_code}")
                try:
                    error_data = response.json()
                    logger.error(f"错误详情: {error_data}")
                except:
                    logger.error(f"错误内容: {response.text}")
                return None
                    
        except Exception as e:
            logger.error(f"上传文件异常: {e}")
            import traceback
            logger.debug(f"异常堆栈: {traceback.format_exc()}")
            return None
    
    def create_wiki_document(self, space_id: str, title: str, file_token: str, parent_node_token: str = None, file_type: str = "docx") -> Optional[str]:
        """在知识库中创建文档
        
        Args:
            space_id: 知识库ID
            title: 文档标题
            file_token: 文件token
            parent_node_token: 父文档节点token，如果指定则创建为子文档
            file_type: 文件类型，尝试不同的类型以支持PDF
            
        Returns:
            文档的node_token，如果失败返回None
        """
        try:
            url = f"{self.base_url}/wiki/v2/spaces/{space_id}/nodes"
            
            payload = {
                "obj_type": file_type,  # 使用指定的类型
                "title": title,
                "node_type": "origin"
            }
            
            # 只有在提供file_token时才添加obj_token
            if file_token:
                payload["obj_token"] = file_token
            
            # 如果指定了父节点，则创建为子文档
            if parent_node_token:
                payload["parent_node_token"] = parent_node_token
                logger.info(f"📁 将创建为子文档，父节点: {parent_node_token}")
            
            response = self._make_authenticated_request('POST', url, json=payload)
            if not response:
                return None
            
            data = response.json()
            logger.debug(f"创建文档API响应: {data}")
            
            if data.get('code') == 0:
                node_token = data.get('data', {}).get('node', {}).get('node_token')
                logger.success(f"文档创建成功: {title} (token: {node_token})")
                return node_token
            else:
                logger.error(f"创建文档失败: {data.get('msg', '未知错误')} (code: {data.get('code')})")
                return None
                
        except Exception as e:
            logger.error(f"创建文档异常: {e}")
            return None
    
    def upload_pdf_to_wiki(self, file_path: str, title: str, space_id: str, parent_node_token: str = None) -> Optional[str]:
        """上传PDF到飞书（云文档存储，知识库引用）
        
        Args:
            file_path: PDF文件路径
            title: 文档标题
            space_id: 知识库ID
            parent_node_token: 父文档节点token，用于创建子文档
            
        Returns:
            文档URL，如果失败返回None，如果重复返回"DUPLICATE"
        """
        try:
            filename = os.path.basename(file_path)
            
            logger.info(f"🚀 上传PDF到飞书: {filename}")
            logger.info(f"📝 文档标题: {title}")
            logger.info(f"📚 目标知识库ID: {space_id}")
            if parent_node_token:
                logger.info(f"📁 父节点: {parent_node_token}")
            
            # 确保有有效的OAuth2令牌
            if not self.ensure_valid_token():
                logger.error("无法获取有效的访问令牌")
                return None
            
            # 检查文件是否已存在
            logger.info("🔍 检查文件是否已存在...")
            if self.check_file_exists_in_wiki(space_id, title, parent_node_token):
                logger.warning(f"📋 文件已存在，跳过上传: {title}")
                return "DUPLICATE"
            
            # 上传PDF到云文档的RO公众号文章文件夹
            logger.info("📤 上传PDF到云文档'RO公众号文章'文件夹...")
            ro_folder_token = "BTZkfStogleXeZdbyH7cEyvdnog"  # RO公众号文章文件夹token
            file_token = self.upload_file_to_drive(file_path, parent_node=ro_folder_token, parent_type="explorer")
            
            if not file_token:
                logger.error("❌ PDF上传失败")
                return None
            
            drive_url = f"https://thedream.feishu.cn/file/{file_token}"
            logger.success(f"✅ PDF已上传到云文档: {drive_url}")
            
            # 创建知识库文档并直接关联PDF文件
            logger.info("📋 在知识库中创建PDF文档页面...")
            logger.info(f"🔗 关联云文档file_token: {file_token}")
            
            # 先尝试使用PDF类型关联云文档文件
            supported_file_types = ["pdf", "file", "docx"]  # 按优先级尝试不同类型
            node_token = None
            
            for file_type in supported_file_types:
                logger.info(f"🔄 尝试使用文件类型: {file_type}")
                node_token = self.create_wiki_document(
                    space_id=space_id,
                    title=title,
                    file_token=file_token,  # 传递云文档的file_token
                    parent_node_token=parent_node_token,
                    file_type=file_type
                )
                
                if node_token:
                    logger.success(f"✅ 使用文件类型 '{file_type}' 创建成功")
                    break
                else:
                    logger.warning(f"⚠️ 文件类型 '{file_type}' 创建失败，尝试下一个")
            
            if node_token:
                wiki_url = f"https://thedream.feishu.cn/wiki/{node_token}"
                logger.success(f"✅ 知识库PDF文档已创建: {wiki_url}")
                logger.info(f"📄 云文档链接: {drive_url}")
                logger.info("💡 PDF内容已直接关联到知识库文档")
                return wiki_url
            else:
                logger.warning("⚠️ 无法创建知识库文档，返回云文档链接")
                logger.info("💡 PDF已上传到云文档，可手动添加到知识库")
                return drive_url
            
        except Exception as e:
            logger.error(f"上传PDF到知识库异常: {e}")
            return None

    def check_file_exists_in_drive(self, folder_token: str, filename: str) -> bool:
        """检查云文档文件夹中是否已存在同名文件
        
        Args:
            folder_token: 云文档文件夹token
            filename: 要检查的文件名
            
        Returns:
            是否存在
        """
        try:
            logger.debug(f"🔍 检查云文档文件夹中是否存在同名文件: {filename}")
            
            # 列出云文档文件夹中的文件
            url = f"{self.base_url}/drive/v1/files"
            
            params = {
                'folder_token': folder_token,
                'page_size': 50
            }
            
            response = self._make_authenticated_request('GET', url, params=params)
            if not response:
                logger.warning("无法获取云文档文件列表，跳过重复检查")
                return False
            
            data = response.json()
            
            if data.get('code') == 0:
                files = data.get('data', {}).get('files', [])
                logger.debug(f"检查云文档文件夹中的 {len(files)} 个文件")
                
                # 检查是否有同名文件
                for file_info in files:
                    existing_name = file_info.get('name', '')
                    
                    # 精确匹配文件名
                    if filename == existing_name:
                        logger.info(f"发现云文档重复文件: {existing_name}")
                        return True
                    
                    # 也检查去掉扩展名的匹配
                    name_without_ext = filename.rsplit('.', 1)[0] if '.' in filename else filename
                    existing_without_ext = existing_name.rsplit('.', 1)[0] if '.' in existing_name else existing_name
                    
                    if name_without_ext == existing_without_ext:
                        logger.info(f"发现云文档类似文件: {existing_name}")
                        return True
                
                logger.debug(f"云文档中未发现重复文件: {filename}")
                return False
            else:
                logger.warning(f"获取云文档文件列表失败: {data.get('msg')}")
                return False
                
        except Exception as e:
            logger.error(f"检查云文档文件是否存在时出错: {e}")
            return False

    def check_file_exists_in_wiki(self, space_id: str, title: str, parent_node_token: str = None) -> bool:
        """检查知识库中是否已存在同名文件 - 改进的列举API方案
        
        Args:
            space_id: 知识库ID
            title: 文档标题
            parent_node_token: 父节点token
            
        Returns:
            是否存在
        """
        try:
            logger.info(f"🔍 检查知识库重复文件: {title}")
            
            # 🆕 改进方案：先检查指定父节点，再检查整个知识库
            
            # 方法1: 如果有parent_node_token，优先检查子节点
            if parent_node_token:
                logger.debug(f"🔍 检查父节点 {parent_node_token} 下的子节点")
                if self._check_wiki_by_list_children_improved(space_id, parent_node_token, title):
                    return True
            
            # 方法2: 检查整个知识库（使用分页列举）
            logger.debug(f"🔍 检查整个知识库")
            return self._check_wiki_by_list_all_nodes(space_id, title)
                
        except Exception as e:
            logger.error(f"检查文件是否存在时出错: {e}")
            return False

    def _check_wiki_by_list_children_improved(self, space_id: str, parent_node_token: str, title: str) -> bool:
        """改进的子节点检查 - 支持分页和递归检查子页面"""
        try:
            logger.debug(f"🔍 检查节点 {parent_node_token} 下的子节点和子页面")
            page_token = ""
            page_size = 50  # 最大值
            
            while True:
                url = f"{self.base_url}/wiki/v2/spaces/{space_id}/nodes"
                
                params = {
                    'parent_node_token': parent_node_token,
                    'page_size': page_size
                }
                
                if page_token:
                    params['page_token'] = page_token
                
                response = self._make_authenticated_request('GET', url, params=params)
                if not response:
                    logger.warning("无法获取子节点列表")
                    return False
                
                data = response.json()
                
                if data.get('code') != 0:
                    logger.warning(f"获取子节点失败: {data.get('msg')}")
                    return False
                
                items = data.get('data', {}).get('items', [])
                logger.debug(f"🔍 检查 {len(items)} 个直接子节点")
                
                # 检查当前页的直接子节点
                for item in items:
                    node_token = item.get('node_token', '')
                    node_title = item.get('title', '')
                    obj_type = item.get('obj_type', '')
                    
                    logger.debug(f"   📄 子节点: {node_title} (token: {node_token}, type: {obj_type})")
                    
                    # 1. 检查直接子节点本身
                    if self._is_title_match(node_title, title):
                        logger.warning(f"📋 在直接子节点中发现重复文件: {node_title}")
                        return True
                    
                    # 2. 🔥 如果子节点是文档类型，还要检查它的子页面
                    if obj_type in ['doc', 'docx'] and node_token:
                        logger.debug(f"   📂 检查文档 '{node_title}' 的子页面...")
                        if self._check_document_children(space_id, node_token, title):
                            return True
                
                # 检查是否有下一页
                page_token = data.get('data', {}).get('page_token', '')
                has_more = data.get('data', {}).get('has_more', False)
                
                if not has_more or not page_token:
                    break
            
            logger.debug(f"✅ 在节点 {parent_node_token} 及其子页面中未发现重复文件")
            return False
                
        except Exception as e:
            logger.debug(f"检查子节点出错: {e}")
            return False
    
    def _check_document_children(self, space_id: str, doc_node_token: str, title: str) -> bool:
        """检查文档的子页面（第二层递归）"""
        try:
            page_token = ""
            page_size = 50
            
            while True:
                url = f"{self.base_url}/wiki/v2/spaces/{space_id}/nodes"
                
                params = {
                    'parent_node_token': doc_node_token,
                    'page_size': page_size
                }
                
                if page_token:
                    params['page_token'] = page_token
                
                response = self._make_authenticated_request('GET', url, params=params)
                if not response:
                    logger.debug(f"无法获取文档 {doc_node_token} 的子页面")
                    return False
                
                data = response.json()
                
                if data.get('code') != 0:
                    logger.debug(f"获取文档子页面失败: {data.get('msg')}")
                    return False
                
                items = data.get('data', {}).get('items', [])
                if items:
                    logger.debug(f"      🔍 检查文档的 {len(items)} 个子页面")
                
                # 检查文档的子页面
                for item in items:
                    sub_title = item.get('title', '')
                    sub_token = item.get('node_token', '')
                    sub_type = item.get('obj_type', '')
                    
                    logger.debug(f"         📑 子页面: {sub_title} (type: {sub_type})")
                    
                    if self._is_title_match(sub_title, title):
                        logger.warning(f"📋 在文档子页面中发现重复文件: {sub_title}")
                        return True
                
                # 检查是否有下一页
                page_token = data.get('data', {}).get('page_token', '')
                has_more = data.get('data', {}).get('has_more', False)
                
                if not has_more or not page_token:
                    break
            
            return False
                
        except Exception as e:
            logger.debug(f"检查文档子页面出错: {e}")
            return False

    def _check_wiki_by_list_all_nodes(self, space_id: str, title: str) -> bool:
        """改进的全知识库检查 - 支持分页和性能优化"""
        try:
            page_token = ""
            page_size = 50  # 最大值
            checked_count = 0
            max_check_limit = 500  # 限制最大检查数量，避免性能问题
            
            logger.debug(f"🔍 开始分页检查知识库，最多检查 {max_check_limit} 个节点")
            
            while checked_count < max_check_limit:
                url = f"{self.base_url}/wiki/v2/spaces/{space_id}/nodes"
                
                params = {
                    'page_size': page_size
                }
                
                if page_token:
                    params['page_token'] = page_token
                
                response = self._make_authenticated_request('GET', url, params=params)
                if not response:
                    logger.warning("无法获取知识库节点列表")
                    return False
                
                data = response.json()
                
                if data.get('code') != 0:
                    logger.warning(f"获取节点列表失败: {data.get('msg')}")
                    return False
                
                items = data.get('data', {}).get('items', [])
                checked_count += len(items)
                
                logger.debug(f"🔍 检查第 {checked_count-len(items)+1}-{checked_count} 个节点")
                
                # 检查当前页的节点
                for item in items:
                    if self._is_title_match(item.get('title', ''), title):
                        logger.warning(f"📋 在知识库中发现重复文件: {item.get('title', '')} (共检查了{checked_count}个节点)")
                        return True
                
                # 检查是否有下一页
                page_token = data.get('data', {}).get('page_token', '')
                has_more = data.get('data', {}).get('has_more', False)
                
                if not has_more or not page_token:
                    logger.debug(f"✅ 已检查完所有节点，共 {checked_count} 个")
                    break
                
                # 添加短暂延迟避免请求过快
                import time
                time.sleep(0.1)
            
            if checked_count >= max_check_limit:
                logger.warning(f"⚠️ 已达到检查上限 ({max_check_limit} 个节点)，可能有未检查的文件")
            
            logger.debug(f"✅ 未发现重复文件: {title} (检查了 {checked_count} 个节点)")
            return False
                
        except Exception as e:
            logger.error(f"检查知识库节点出错: {e}")
            return False

    def _is_title_match(self, existing_title: str, target_title: str) -> bool:
        """改进的标题匹配逻辑"""
        if not existing_title or not target_title:
            return False
        
        # 1. 精确匹配
        if existing_title == target_title:
            return True
        
        # 2. 去扩展名匹配
        existing_clean = self._clean_title_for_comparison(existing_title)
        target_clean = self._clean_title_for_comparison(target_title)
        
        if existing_clean == target_clean and existing_clean:
            return True
        
        # 3. 忽略大小写匹配（可选）
        if existing_title.lower() == target_title.lower():
            return True
        
        return False

    def _clean_title_for_comparison(self, title: str) -> str:
        """清理标题用于比较，去除常见的扩展名和特殊字符"""
        if not title:
            return ""
        
        # 去除常见扩展名
        cleaned = title
        for ext in ['.pdf', '.PDF', '.docx', '.DOCX', '.doc', '.DOC']:
            if cleaned.endswith(ext):
                cleaned = cleaned[:-len(ext)]
                break
        
        # 去除首尾空白和特殊字符
        cleaned = cleaned.strip()
        
        return cleaned

    def get_wiki_node_by_token(self, obj_token: str, obj_type: str = "docx") -> Optional[Dict]:
        """通过token获取知识库节点信息
        
        使用新的get_node API检查文件是否存在于知识库中
        
        Args:
            obj_token: 文档或wiki的token
            obj_type: 对象类型 ("docx", "doc", "pdf"等)
            
        Returns:
            节点信息字典，如果不存在返回None
        """
        try:
            url = f"{self.base_url}/wiki/v2/spaces/get_node"
            
            params = {
                'token': obj_token,
                'obj_type': obj_type
            }
            
            response = self._make_authenticated_request('GET', url, params=params)
            if not response:
                return None
            
            data = response.json()
            
            if data.get('code') == 0:
                node_info = data.get('data', {}).get('node', {})
                logger.debug(f"✅ 获取到节点信息: {node_info.get('title', 'No title')}")
                return node_info
            else:
                logger.debug(f"🔍 节点不存在或无法访问: {data.get('msg', 'Unknown error')}")
                return None
                
        except Exception as e:
            logger.debug(f"获取节点信息时出错: {e}")
            return None

    def check_file_exists_by_token(self, file_token: str, obj_type: str = "docx") -> bool:
        """通过文件token检查文件是否存在于知识库中
        
        Args:
            file_token: 文件token
            obj_type: 文件类型
            
        Returns:
            是否存在于知识库
        """
        try:
            node_info = self.get_wiki_node_by_token(file_token, obj_type)
            if node_info:
                title = node_info.get('title', '')
                logger.info(f"📋 文件已存在于知识库: {title}")
                return True
            return False
        except Exception as e:
            logger.debug(f"检查文件token时出错: {e}")
            return False

    def _import_document_to_wiki(self, file_token: str, space_id: str, title: str, parent_node_token: str = None) -> Optional[str]:
        """使用飞书导入API将文档导入到知识库
        
        Args:
            file_token: 云文档的文件token
            space_id: 知识库ID
            title: 文档标题
            parent_node_token: 父节点token
            
        Returns:
            导入后的文档URL，如果失败返回None
        """
        try:
            # 使用飞书的文档导入API
            # 注意：这个API可能需要特殊权限，需要测试是否可用
            url = f"{self.base_url}/wiki/v2/spaces/{space_id}/nodes/import"
            
            payload = {
                "file_token": file_token,
                "title": title,
                "node_type": "origin"
            }
            
            if parent_node_token:
                payload["parent_node_token"] = parent_node_token
            
            logger.info(f"📤 调用文档导入API: {url}")
            logger.debug(f"📋 导入参数: {payload}")
            
            response = self._make_authenticated_request('POST', url, json=payload)
            if not response:
                logger.warning("⚠️ 文档导入API调用失败")
                return None
            
            data = response.json()
            logger.debug(f"导入API响应: {data}")
            
            if data.get('code') == 0:
                node_token = data.get('data', {}).get('node_token')
                if node_token:
                    wiki_url = f"https://thedream.feishu.cn/wiki/{node_token}"
                    logger.success(f"✅ 文档导入成功: {title} (token: {node_token})")
                    return wiki_url
                else:
                    logger.warning("⚠️ 导入API返回成功但未获取到node_token")
                    return None
            else:
                error_code = data.get('code')
                error_msg = data.get('msg', '未知错误')
                logger.warning(f"⚠️ 文档导入API失败: {error_code} - {error_msg}")
                
                # 特殊处理一些常见错误
                if error_code == 99991663:
                    logger.info("💡 此错误通常表示导入API不可用或权限不足")
                elif error_code == 230005:
                    logger.info("💡 此错误通常表示文件格式不支持导入")
                
                return None
                
        except Exception as e:
            logger.error(f"文档导入API异常: {e}")
            return None

    def get_tenant_access_token(self) -> Optional[str]:
        """获取应用身份访问令牌（用于上传文件等操作）"""
        try:
            url = f"{self.base_url}/auth/v3/tenant_access_token/internal"
            
            payload = {
                "app_id": self.app_id,
                "app_secret": self.app_secret
            }
            
            response = requests.post(url, json=payload)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('code') == 0:
                    tenant_token = data.get('tenant_access_token')
                    logger.debug(f"✅ 获取应用身份令牌成功")
                    return tenant_token
                else:
                    logger.error(f"❌ 获取应用身份令牌业务失败: {data.get('msg')}")
                    return None
            else:
                logger.error(f"❌ 获取应用身份令牌HTTP失败: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"获取应用身份令牌异常: {e}")
            return None

    def upload_media_for_import(self, file_path: str, parent_node: str = None) -> Optional[str]:
        """[V4 修复] 步骤一：上传素材文件用于导入 (使用应用身份令牌)"""
        try:
            filename = os.path.basename(file_path)
            logger.info(f"📤 [导入流程-1] 上传素材文件: {filename}")

            if not os.path.exists(file_path):
                logger.error(f"❌ [导入流程-1] 文件不存在: {file_path}")
                return None

            # 🔥 使用应用身份令牌而不是用户身份令牌
            tenant_token = self.get_tenant_access_token()
            if not tenant_token:
                logger.error("❌ [导入流程-1] 获取应用身份令牌失败")
                return None

            url = f"{self.base_url}/drive/v1/medias/upload_all"
            
            with open(file_path, 'rb') as f:
                file_content = f.read()

            if not file_content:
                logger.error(f"❌ [导入流程-1] 文件内容为空: {file_path}")
                return None
            
            file_size = len(file_content)
            
            form_data = {
                'file_name': filename,
                'parent_type': 'ccm_import_open', # 用于导入的特殊类型
                'size': str(file_size),
            }

            files = {'file': (filename, file_content)}
            
            logger.debug(f"  - API URL: {url}")
            logger.debug(f"  - Form Data: {form_data}")

            # 🔥 使用应用身份令牌
            headers = {'Authorization': f'Bearer {tenant_token}'}
            response = requests.post(url, files=files, data=form_data, headers=headers)

            logger.debug(f"  - HTTP状态码: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                logger.debug(f"  - 响应内容: {json.dumps(result, indent=2, ensure_ascii=False)}")
                if result.get("code") == 0:
                    file_token = result.get("data", {}).get("file_token")
                    logger.info(f"✅ [导入流程-1] 上传成功, file_token: {file_token}")
                    return file_token
                else:
                    logger.error(f"❌ [导入流程-1] 上传业务失败: {result.get('msg')}")
                    return None
            else:
                logger.error(f"❌ [导入流程-1] 上传HTTP请求失败, status={response.status_code}, body={response.text}")
                return None
        except Exception as e:
            logger.error(f"❌ [导入流程-1] 上传异常: {e}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")
            return None

    def create_import_task(self, file_token: str, file_name: str, mount_key: str = None) -> Optional[str]:
        """创建导入任务，将文件转换为飞书云文档
        
        Args:
            file_token: 文件token
            file_name: 文件名
            mount_key: 挂载点（可选）
            
        Returns:
            导入任务ticket，失败返回None
        """
        try:
            logger.info(f"📝 创建导入任务: {file_name}")
            
            url = f"{self.base_url}/drive/v1/import_tasks"
            
            # 根据飞书官方文档设置正确的参数
            payload = {
                "file_extension": "docx",  # 源文件扩展名
                "file_token": file_token,  # 上传文件的token
                "type": "docx",  # 🔥 修复：设置为"docx"导入为新版文档
                "file_name": file_name  # 导入后的文件名
            }
            
            # 如果指定了挂载点，添加到payload中
            if mount_key:
                payload["point"] = {
                    "mount_key": mount_key
                }
                logger.info(f"📁 指定挂载点: {mount_key}")
            
            logger.debug(f"📋 导入任务参数: {json.dumps(payload, indent=2, ensure_ascii=False)}")
            
            response = self._make_authenticated_request('POST', url, json=payload)
            if not response:
                logger.error("❌ 创建导入任务API调用失败")
                return None
            
            result = response.json()
            logger.debug(f"📄 导入任务创建响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
            
            if result.get('code') == 0:
                ticket = result.get('data', {}).get('ticket')
                if ticket:
                    logger.success(f"✅ 导入任务创建成功: {ticket}")
                    return ticket
                else:
                    logger.error("❌ 导入任务创建成功但未获取到ticket")
                    return None
            else:
                error_code = result.get('code')
                error_msg = result.get('msg', '未知错误')
                logger.error(f"❌ 创建导入任务失败: {error_code} - {error_msg}")
                return None
                
        except Exception as e:
            logger.error(f"创建导入任务异常: {e}")
            return None

    def query_import_result(self, ticket: str, max_wait_time: int = 60) -> Optional[Dict]:
        """[增强日志] 步骤三：查询导入任务结果"""
        logger.info(f"⏳ [导入流程-3] 查询导入结果, ticket: {ticket}")
        
        start_time = time.time()
        url = f"{self.base_url}/drive/v1/import_tasks/{ticket}"

        while time.time() - start_time < max_wait_time:
            logger.debug(f"  - 查询任务状态...")
            response = self._make_authenticated_request('GET', url)
            
            if not response:
                time.sleep(2)
                continue

            try:
                result = response.json()
            except json.JSONDecodeError:
                logger.error(f"❌ [导入流程-3] 无法解析JSON响应: {response.text}")
                time.sleep(2)
                continue

            if result.get("code") == 0:
                result_data = result.get("data", {}).get("result", {})
                job_status = result_data.get("job_status")
                
                logger.debug(f"  - 任务状态: {job_status}")

                if job_status == 1:  # 任务成功
                    doc_token = result_data.get("token")
                    logger.success(f"✅ [导入流程-3] 任务成功, 文档token: {doc_token}")
                    return {"token": doc_token, "url": result_data.get("url")}
                elif job_status == 2:  # 任务失败
                    error_msg = result_data.get("job_error_msg")
                    logger.error(f"❌ [导入流程-3] 任务失败: {error_msg}")
                    logger.debug(f"  - 失败任务的完整结果: {result_data}")
                    return None
                elif job_status in [0, 3]:  # 任务还在处理中或排队中
                    status_map = {0: "排队中", 3: "处理中"}
                    current_status_text = status_map.get(job_status, "处理中")
                    logger.info(f"  - 任务仍在{current_status_text}，等待2秒后重试...")
                    time.sleep(2)
                    continue
                else:  # 任务状态未知
                    logger.warning(f"  - 未知任务状态: {job_status}, 响应: {result_data}")
                    time.sleep(2)
                    continue
            else:
                logger.error(f"❌ [导入流程-3] 查询业务失败: {result.get('msg')}")
                return None
        
        logger.error("❌ [导入流程-3] 查询超时")
        return None

    def import_docx_as_feishu_doc(self, file_path: str, title: str, parent_node: str = None) -> Optional[str]:
        """完整的DOCX导入为飞书云文档流程
        
        Args:
            file_path: DOCX文件路径
            title: 文档标题
            parent_node: 父节点token（可选）
            
        Returns:
            飞书云文档URL，失败返回None
        """
        try:
            filename = os.path.basename(file_path)
            logger.info(f"🚀 开始完整的DOCX导入流程: {filename}")
            logger.info(f"📝 目标标题: {title}")
            
            # 步骤一：上传本地文件
            logger.info("📤 执行步骤一：上传素材文件...")
            file_token = self.upload_media_for_import(file_path, parent_node)
            if not file_token:
                logger.error("❌ 步骤一失败：文件上传失败")
                return None
            logger.success(f"✅ 步骤一成功：文件已上传，token: {file_token}")
            
            # 步骤二：创建导入任务
            logger.info("📋 执行步骤二：创建导入任务...")
            ticket = self.create_import_task(file_token, filename)
            if not ticket:
                logger.error("❌ 步骤二失败：创建导入任务失败")
                return None
            logger.success(f"✅ 步骤二成功：导入任务已创建，ticket: {ticket}")
            
            # 步骤三：查询导入结果
            logger.info("🔍 执行步骤三：等待导入完成...")
            import_result = self.query_import_result(ticket)
            if not import_result:
                logger.error("❌ 步骤三失败：导入任务失败或超时")
                return None
            
            doc_url = import_result.get('url')
            logger.success(f"🎉 DOCX导入飞书云文档成功！")
            logger.success(f"📄 文档链接: {doc_url}")
            
            return doc_url
            
        except Exception as e:
            logger.error(f"DOCX导入飞书云文档异常: {e}")
            return None

    def _find_target_wiki_location(self, title: str) -> Dict[str, str]:
        """根据文章标题找到目标知识库位置
        
        Args:
            title: 文档标题
            
        Returns:
            包含space_id和parent_node_token的字典
        """
        try:
            # 加载wiki位置配置
            wiki_config = {}
            for config_file in ['test_wiki_locations.json', 'wiki_location_config.json']:
                if os.path.exists(config_file):
                    with open(config_file, 'r', encoding='utf-8') as f:
                        wiki_config = json.load(f)
                    break
            
            if not wiki_config:
                logger.warning("⚠️ 未找到wiki位置配置文件，使用默认配置")
                # 使用默认配置
                with open('user_feishu_config.json', 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                return {
                    'space_id': user_config.get('space_id', '7511922459407450115'),
                    'parent_node_token': None
                }
            
            logger.info(f"🔍 智能分类分析标题: {title}")
            
            # 检查是否直接匹配配置中的位置
            if title in wiki_config:
                location_info = wiki_config[title]
                logger.info(f"✅ 找到直接匹配位置: {title}")
                return location_info
            
            # 如果是旧版配置格式，进行关键词匹配
            if 'wiki_locations' in wiki_config:
                title_lower = title.lower()
                default_location = wiki_config.get('default_wiki_location', '')
                wiki_locations = wiki_config.get('wiki_locations', [])
                
                for location in wiki_locations:
                    keywords = location.get('keywords', [])
                    wiki_url = location.get('wiki_url', '')
                    
                    for keyword in keywords:
                        if keyword.lower() in title_lower:
                            logger.info(f"✅ 关键词匹配: '{keyword}' → {wiki_url}")
                            # 从URL提取space_id和parent_node_token
                            return self._extract_location_from_url(wiki_url)
                
                # 没有匹配到关键词，使用默认位置
                logger.info(f"🏠 使用默认位置: {default_location}")
                return self._extract_location_from_url(default_location)
            
            # 使用第一个位置作为默认
            first_key = next(iter(wiki_config.keys()))
            logger.info(f"🏠 使用第一个配置位置: {first_key}")
            return wiki_config[first_key]
            
        except Exception as e:
            logger.error(f"智能分类分析异常: {e}")
            # 回退到默认配置
            with open('user_feishu_config.json', 'r', encoding='utf-8') as f:
                user_config = json.load(f)
            return {
                'space_id': user_config.get('space_id', '7511922459407450115'),
                'parent_node_token': None
            }

    def _extract_location_from_url(self, wiki_url: str) -> Dict[str, str]:
        """从wiki URL中提取space_id和parent_node_token
        
        Args:
            wiki_url: 飞书wiki URL
            
        Returns:
            包含space_id和parent_node_token的字典
        """
        try:
            # 从URL中提取parent_node_token
            parent_node_token = None
            
            if "/wiki/" in wiki_url:
                # 去掉查询参数
                clean_url = wiki_url.split("?")[0] if "?" in wiki_url else wiki_url
                
                if "/wiki/space/" in clean_url:
                    parent_node_token = clean_url.split("/wiki/space/")[-1]
                elif "/wiki/" in clean_url:
                    parent_node_token = clean_url.split("/wiki/")[-1]
            
            # 获取默认space_id
            with open('user_feishu_config.json', 'r', encoding='utf-8') as f:
                user_config = json.load(f)
            space_id = user_config.get('space_id', '7511922459407450115')
            
            logger.debug(f"📍 URL解析结果: space_id={space_id}, parent_node_token={parent_node_token}")
            
            return {
                'space_id': space_id,
                'parent_node_token': parent_node_token
            }
            
        except Exception as e:
            logger.error(f"URL解析异常: {e}")
            # 回退到默认配置
            with open('user_feishu_config.json', 'r', encoding='utf-8') as f:
                user_config = json.load(f)
            return {
                'space_id': user_config.get('space_id', '7511922459407450115'),
                'parent_node_token': None
            }

    def import_docx_to_wiki(self, file_path: str, title: str, space_id: str = None, parent_node_token: str = None) -> Optional[str]:
        """使用新的三步导入流程将DOCX导入为飞书云文档，然后转移到知识库
        
        Args:
            file_path: DOCX文件路径
            title: 文档标题
            space_id: 知识库ID（可选，会使用智能分类）
            parent_node_token: 父文档节点token（可选，会使用智能分类）
            
        Returns:
            文档URL，如果失败返回None，如果重复返回"DUPLICATE"
        """
        try:
            filename = os.path.basename(file_path)
            
            logger.info(f"📥 使用新导入流程处理DOCX到知识库: {filename}")
            logger.info(f"📝 文档标题: {title}")
            
            # 🆕 如果没有指定space_id或parent_node_token，使用智能分类
            if not space_id or parent_node_token is None:
                logger.info("🧠 未指定目标位置，启用智能分类...")
                target_location = self._find_target_wiki_location(title)
                space_id = target_location.get('space_id', space_id)
                parent_node_token = target_location.get('parent_node_token', parent_node_token)
                logger.info(f"🎯 智能分类结果: space_id={space_id}, parent_node_token={parent_node_token}")
            
            logger.info(f"📚 目标知识库ID: {space_id}")
            if parent_node_token:
                logger.info(f"📁 父节点: {parent_node_token}")
            else:
                logger.info(f"📁 转移到知识库根目录")
            
            # 确保有有效的OAuth2令牌
            if not self.ensure_valid_token():
                logger.error("无法获取有效的访问令牌")
                return None
            
            # 检查文件是否已存在
            logger.info("🔍 检查文件是否已存在...")
            if self.check_file_exists_in_wiki(space_id, title, parent_node_token):
                logger.warning(f"📋 文件已存在，跳过导入: {title}")
                return "DUPLICATE"
            
            # 🆕 使用新的三步导入流程将DOCX导入为飞书云文档
            logger.info("🚀 使用新的三步导入流程...")
            doc_url = self.import_docx_as_feishu_doc(file_path, title)
            
            if not doc_url:
                logger.error("❌ DOCX导入为飞书云文档失败")
                return None
            
            # 从URL中提取文档token
            import re
            # 支持多种格式：/docx/ 或 /docs/
            token_match = re.search(r'/(?:docx|docs)/([^/?]+)', doc_url)
            if not token_match:
                logger.error("❌ 无法从文档URL中提取token")
                logger.error(f"📄 原始URL: {doc_url}")
                return None
            
            doc_token = token_match.group(1)
            logger.info(f"📄 提取到文档token: {doc_token}")
            
            # 🆕 将飞书云文档转移到知识库
            logger.info("📚 将飞书云文档转移到知识库...")
            wiki_result = self._move_feishu_doc_to_wiki(
                doc_token=doc_token,
                space_id=space_id,
                parent_node_token=parent_node_token,
                title=title
            )
            
            if wiki_result:
                logger.success(f"✅ DOCX已成功导入为飞书云文档并转移到知识库")
                logger.success(f"📖 知识库链接: {wiki_result}")
                return wiki_result
            else:
                logger.warning("⚠️ 文档导入成功但转移到知识库失败")
                logger.info(f"📄 原飞书云文档链接: {doc_url}")
                return doc_url
            
        except Exception as e:
            logger.error(f"导入DOCX到知识库异常: {e}")
            return None

    def _move_feishu_doc_to_wiki(self, doc_token: str, space_id: str, parent_node_token: str = None, title: str = None) -> Optional[str]:
        """[重构] 将飞书云文档转移到知识库，并处理重试
        
        Args:
            doc_token: 飞书云文档token
            space_id: 知识库ID
            parent_node_token: 父节点token
            title: 文档标题 (用于日志)
            
        Returns:
            知识库文档URL，失败返回None
        """
        try:
            logger.info(f"📚 开始转移飞书云文档到知识库: {title or doc_token}")
            
            # 定义要尝试的obj_type顺序
            obj_types_to_try = ['docx', 'doc', 'docs']
            
            for obj_type in obj_types_to_try:
                logger.info(f"🔄 尝试使用 obj_type='{obj_type}' 进行转移...")
                
                url = f"{self.base_url}/wiki/v2/spaces/{space_id}/nodes/move_docs_to_wiki"
                
                payload = {
                    "obj_token": doc_token,
                    "obj_type": obj_type,
                }
                
                if parent_node_token:
                    payload["parent_wiki_token"] = parent_node_token
                
                logger.debug(f"🚀 调用转移API: {url}")
                logger.debug(f"📋 请求载荷: {json.dumps(payload, indent=2, ensure_ascii=False)}")
                
                response = self._make_authenticated_request('POST', url, json=payload)
                if not response:
                    logger.error("❌ 转移API调用失败 - 没有收到响应")
                    continue # 尝试下一个obj_type

                try:
                    result = response.json()
                except Exception as json_error:
                    logger.error(f"❌ 无法解析API响应为JSON: {json_error}")
                    logger.error(f"📄 原始响应内容: {response.text}")
                    continue # 尝试下一个obj_type

                business_code = result.get('code')
                
                if business_code == 0:
                    logger.success(f"✅ 使用 obj_type='{obj_type}' 提交转移请求成功")
                    data = result.get('data', {})
                    
                    # 处理异步任务
                    if 'task_id' in data:
                        task_id = data['task_id']
                        logger.info(f"⏳ 转移任务已提交，任务ID: {task_id}")
                        return self._wait_for_move_task(task_id)
                    
                    # 处理直接返回的结果
                    elif 'wiki_token' in data:
                        wiki_token = data['wiki_token']
                        wiki_url = f"https://thedream.feishu.cn/wiki/{wiki_token}"
                        logger.success(f"✅ 飞书云文档已直接转移到知识库: {wiki_url}")
                        return wiki_url
                    
                    else:
                        logger.warning("⚠️ 转移API返回成功但未获取到有效结果")
                        logger.debug(f"📄 API响应数据: {json.dumps(data, indent=2, ensure_ascii=False)}")
                        return None # 成功但无结果，不再重试
                        
                elif business_code == 230005:
                    logger.warning(f"❌ 使用 obj_type='{obj_type}' 失败 (错误230005)，继续尝试下一个...")
                    continue # obj_type错误，继续尝试
                
                else:
                    # 其他无法通过重试解决的错误
                    error_msg = result.get('msg', '未知错误')
                    logger.error(f"❌ 转移API返回无法恢复的错误: code={business_code}, msg='{error_msg}'")
                    logger.debug(f"📄 完整错误响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
                    return None # 无法恢复的错误，停止重试
            
            logger.error(f"❌ 所有obj_type尝试均失败，无法转移文档: {doc_token}")
            return None
            
        except Exception as e:
            logger.error(f"转移飞书云文档到知识库异常: {e}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")
            return None

    def _get_cloud_doc_info(self, doc_token: str) -> Optional[Dict]:
        """获取云文档信息
        
        Args:
            doc_token: 文档token
            
        Returns:
            文档信息，失败返回None
        """
        try:
            # 尝试通过搜索API获取文档信息
            url = f"{self.base_url}/drive/v1/files/{doc_token}"
            
            response = self._make_authenticated_request('GET', url)
            if response and response.status_code == 200:
                result = response.json()
                if result.get('code') == 0:
                    return result.get('data', {})
            
            logger.debug(f"⚠️ 无法获取云文档信息: {doc_token}")
            return None
            
        except Exception as e:
            logger.debug(f"获取云文档信息异常: {e}")
            return None

    def _wait_for_move_task(self, task_id: str, max_wait_time: int = 30) -> Optional[str]:
        """[重构] 等待转移任务完成，并根据官方文档解析结果
        
        Args:
            task_id: 任务ID
            max_wait_time: 最大等待时间（秒）
            
        Returns:
            转移成功后的知识库文档URL，失败返回None
        """
        try:
            logger.info(f"⏳ 等待转移任务完成: {task_id}")
            
            # 使用获取任务结果API
            url = f"{self.base_url}/wiki/v2/tasks/{task_id}"
            
            start_time = time.time()
            wait_interval = 2  # 查询间隔2秒
            
            while time.time() - start_time < max_wait_time:
                logger.debug(f"🔍 查询任务状态API: {url}")
                
                response = self._make_authenticated_request('GET', url)
                if not response:
                    logger.error("❌ 查询任务状态API调用失败 - 没有收到响应")
                    return None
                
                try:
                    result = response.json()
                    logger.debug(f"📄 任务状态查询完整响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
                except Exception as json_error:
                    logger.error(f"❌ 无法解析任务状态响应为JSON: {json_error}")
                    logger.error(f"📄 原始响应内容: {response.text}")
                    return None
                
                if result.get('code') == 0:
                    task_data = result.get('data', {}).get('task', {})
                    
                    # 检查 move_result 是否存在并且是一个列表
                    move_result_list = task_data.get('move_result')
                    
                    if not move_result_list:
                        logger.info(f"⏳ 任务仍在处理中，未返回move_result...")
                        time.sleep(wait_interval)
                        continue

                    # 遍历 move_result 列表
                    for move_result in move_result_list:
                        status = move_result.get('status')
                        status_msg = move_result.get('status_msg', '无状态信息')
                        
                        if status == 0:
                            # 任务成功
                            node = move_result.get('node', {})
                            wiki_token = node.get('node_token')
                            
                            if wiki_token:
                                wiki_url = f"https://thedream.feishu.cn/wiki/{wiki_token}"
                                logger.success(f"✅ 转移任务成功完成: {wiki_url}")
                                return wiki_url
                            else:
                                logger.error("❌ 任务成功但无法获取wiki_token")
                                logger.debug(f"📄 成功的节点信息: {json.dumps(node, indent=2, ensure_ascii=False)}")
                                return None
                        else:
                            # 任务失败
                            logger.error(f"❌ 转移任务失败 - 状态码: {status}, 消息: {status_msg}")
                            logger.debug(f"📄 失败的移动结果: {json.dumps(move_result, indent=2, ensure_ascii=False)}")
                            return None
                else:
                    error_code = result.get('code')
                    error_msg = result.get('msg', '未知错误')
                    logger.error(f"❌ 查询任务状态失败: {error_code} - {error_msg}")
                    return None

                # 如果没有明确的成功或失败状态，继续等待
                time.sleep(wait_interval)
            
            logger.warning(f"⏰ 转移任务等待超时（{max_wait_time}秒）")
            return None
            
        except Exception as e:
            logger.error(f"等待转移任务异常: {e}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")
            return None


def test_user_client():
    """测试用户身份客户端"""
    app_id = "cli_a8c822312a75901c"
    app_secret = "NDbCyKEwEIA8CZo2KHyqueIOlcafErko"
    space_token = "Rkr5w3y8hib7dRk1KpFcMZ7tnGc"
    
    # 初始化客户端
    client = FeishuUserAPIClient(app_id, app_secret)
    
    # 获取用户访问令牌
    token = client.get_user_access_token()
    if not token:
        logger.error("无法获取用户访问令牌")
        return
    
    # 测试权限
    permissions = client.test_permissions()
    logger.info(f"权限测试结果: {permissions}")
    
    # 测试知识库连接
    space_info = client.get_space_info_by_token(space_token)
    if space_info:
        space_id = space_info.get('space_id')
        wiki_name = space_info.get('name')
        logger.success(f"✅ 成功连接知识库: {wiki_name} (space_id: {space_id})")
        
        # 如果有文件上传权限，测试上传功能
        if permissions.get('file_upload'):
            test_pdf = "output/auto_download/test.pdf"
            if os.path.exists(test_pdf):
                success = client.upload_pdf_to_wiki(test_pdf, space_id)
                if success:
                    logger.success("🎉 测试上传成功！")
                else:
                    logger.error("测试上传失败")
            else:
                logger.info("没有找到测试PDF文件")
        else:
            logger.warning("没有文件上传权限")
    else:
        logger.error("无法连接知识库")


# 为了兼容GUI代码，创建别名
FeishuUserClient = FeishuUserAPIClient

if __name__ == "__main__":
    test_user_client() 