#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞书Token刷新工具
用于重新获取有效的access token和refresh token
"""

import json
import requests
import time
from datetime import datetime
from loguru import logger

class FeishuTokenRefresher:
    """飞书Token刷新器"""
    
    def __init__(self):
        self.api_base = "https://open.feishu.cn/open-apis"
        
    def get_app_access_token(self, app_id: str, app_secret: str) -> dict:
        """获取应用访问凭证（app_access_token）"""
        try:
            url = f"{self.api_base}/auth/v3/app_access_token/internal"
            
            payload = {
                "app_id": app_id,
                "app_secret": app_secret
            }
            
            headers = {
                "Content-Type": "application/json"
            }
            
            logger.info(f"🔑 正在获取应用访问凭证...")
            response = requests.post(url, json=payload, headers=headers)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("code") == 0:
                    logger.success(f"✅ 应用访问凭证获取成功")
                    return {
                        "success": True,
                        "app_access_token": result.get("app_access_token"),
                        "expire": result.get("expire")
                    }
                else:
                    logger.error(f"❌ 获取应用访问凭证失败: {result}")
                    return {"success": False, "error": result}
            else:
                logger.error(f"❌ HTTP请求失败: {response.status_code}")
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            logger.error(f"❌ 获取应用访问凭证异常: {e}")
            return {"success": False, "error": str(e)}
    
    def refresh_user_access_token(self, app_id: str, app_secret: str, refresh_token: str) -> dict:
        """使用refresh token刷新用户访问凭证"""
        try:
            # 先获取app_access_token
            app_token_result = self.get_app_access_token(app_id, app_secret)
            if not app_token_result.get("success"):
                return app_token_result
            
            app_access_token = app_token_result["app_access_token"]
            
            # 使用app_access_token刷新用户token
            url = f"{self.api_base}/authen/v1/refresh_access_token"
            
            headers = {
                "Authorization": f"Bearer {app_access_token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token
            }
            
            logger.info(f"🔄 正在刷新用户访问凭证...")
            response = requests.post(url, json=payload, headers=headers)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("code") == 0:
                    data = result.get("data", {})
                    logger.success(f"✅ 用户访问凭证刷新成功")
                    return {
                        "success": True,
                        "access_token": data.get("access_token"),
                        "refresh_token": data.get("refresh_token"),
                        "expires_in": data.get("expires_in"),
                        "token_type": data.get("token_type"),
                        "scope": data.get("scope")
                    }
                else:
                    logger.error(f"❌ 刷新用户访问凭证失败: {result}")
                    return {"success": False, "error": result}
            else:
                logger.error(f"❌ HTTP请求失败: {response.status_code}")
                logger.error(f"📄 响应内容: {response.text}")
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            logger.error(f"❌ 刷新用户访问凭证异常: {e}")
            return {"success": False, "error": str(e)}
    
    def test_access_token(self, access_token: str) -> bool:
        """测试access token是否有效"""
        try:
            url = f"{self.api_base}/authen/v1/user_info"
            
            headers = {
                "Authorization": f"Bearer {access_token}"
            }
            
            logger.info(f"🧪 测试访问凭证有效性...")
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("code") == 0:
                    user_info = result.get("data", {})
                    logger.success(f"✅ 访问凭证有效，用户: {user_info.get('name', '未知')}")
                    return True
                else:
                    logger.error(f"❌ 访问凭证无效: {result}")
                    return False
            else:
                logger.error(f"❌ 测试请求失败: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 测试访问凭证异常: {e}")
            return False
    
    def update_config_files(self, tokens: dict, app_id: str) -> bool:
        """更新配置文件"""
        try:
            current_time = time.time()
            
            # 更新 feishu_oauth_tokens.json
            oauth_config = {
                "access_token": tokens["access_token"],
                "refresh_token": tokens["refresh_token"],
                "expires_in": tokens["expires_in"],
                "token_type": tokens["token_type"],
                "scope": tokens["scope"],
                "created_at": int(current_time),
                "app_id": app_id
            }
            
            with open("feishu_oauth_tokens.json", "w", encoding="utf-8") as f:
                json.dump(oauth_config, f, ensure_ascii=False, indent=2)
            
            logger.success(f"✅ 已更新 feishu_oauth_tokens.json")
            
            # 更新 user_feishu_config.json 中的 access_token
            try:
                with open("user_feishu_config.json", "r", encoding="utf-8") as f:
                    user_config = json.load(f)
                
                user_config["access_token"] = tokens["access_token"]
                user_config["test_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                user_config["test_success"] = True
                
                with open("user_feishu_config.json", "w", encoding="utf-8") as f:
                    json.dump(user_config, f, ensure_ascii=False, indent=2)
                
                logger.success(f"✅ 已更新 user_feishu_config.json")
                
            except Exception as e:
                logger.warning(f"⚠️ 更新 user_feishu_config.json 失败: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 更新配置文件失败: {e}")
            return False

def main():
    """主函数"""
    refresher = FeishuTokenRefresher()
    
    logger.info("🚀 开始刷新飞书访问凭证...")
    
    # 尝试从两个配置文件读取应用信息
    app_configs = []
    
    # 配置1: user_feishu_config.json
    try:
        with open("user_feishu_config.json", "r", encoding="utf-8") as f:
            config1 = json.load(f)
        app_configs.append({
            "source": "user_feishu_config.json",
            "app_id": config1["app_id"],
            "app_secret": config1["app_secret"]
        })
    except Exception as e:
        logger.warning(f"⚠️ 读取 user_feishu_config.json 失败: {e}")
    
    # 配置2: feishu_oauth_tokens.json (如果有不同的app_id)
    try:
        with open("feishu_oauth_tokens.json", "r", encoding="utf-8") as f:
            oauth_tokens = json.load(f)
        
        oauth_app_id = oauth_tokens.get("app_id")
        if oauth_app_id and oauth_app_id not in [c["app_id"] for c in app_configs]:
            # 尝试从其他地方找到这个app_id的secret
            # 这里我们需要用户提供或者使用默认的
            logger.warning(f"⚠️ 在 feishu_oauth_tokens.json 中找到不同的app_id: {oauth_app_id}")
            logger.warning(f"⚠️ 但没有找到对应的app_secret，请手动配置")
            
    except Exception as e:
        logger.warning(f"⚠️ 读取 feishu_oauth_tokens.json 失败: {e}")
    
    if not app_configs:
        logger.error(f"❌ 没有找到有效的应用配置")
        return
    
    # 尝试每个配置
    for config in app_configs:
        app_id = config["app_id"]
        app_secret = config["app_secret"]
        
        logger.info(f"📱 尝试应用ID: {app_id} (来源: {config['source']})")
        
        # 先测试应用访问凭证
        app_token_result = refresher.get_app_access_token(app_id, app_secret)
        if not app_token_result.get("success"):
            logger.error(f"❌ 应用 {app_id} 获取访问凭证失败，尝试下一个...")
            continue
        
        # 尝试使用现有的refresh token
        try:
            with open("feishu_oauth_tokens.json", "r", encoding="utf-8") as f:
                oauth_tokens = json.load(f)
            
            refresh_token = oauth_tokens.get("refresh_token")
            
            if refresh_token:
                logger.info(f"🔄 尝试使用现有refresh token刷新...")
                
                # 刷新token
                result = refresher.refresh_user_access_token(app_id, app_secret, refresh_token)
                
                if result.get("success"):
                    # 测试新token
                    new_access_token = result["access_token"]
                    if refresher.test_access_token(new_access_token):
                        # 读取完整配置用于输出
                        try:
                            with open("user_feishu_config.json", "r", encoding="utf-8") as f:
                                full_config = json.load(f)
                        except:
                            full_config = {}
                        
                        # 更新配置文件
                        if refresher.update_config_files(result, app_id):
                            logger.success(f"🎉 飞书访问凭证刷新成功！")
                            
                            print("\n" + "="*60)
                            print("🎉 新的GitHub Secrets值：")
                            print("="*60)
                            print(f"FEISHU_APP_ID: {app_id}")
                            print(f"FEISHU_APP_SECRET: {app_secret}")
                            print(f"FEISHU_ACCESS_TOKEN: {result['access_token']}")
                            print(f"FEISHU_REFRESH_TOKEN: {result['refresh_token']}")
                            print(f"FEISHU_SPACE_TOKEN: {full_config.get('space_token', '')}")
                            print(f"FEISHU_SPACE_ID: {full_config.get('space_id', '')}")
                            print("="*60)
                            print("请将以上值更新到GitHub Secrets中！")
                            
                            return
                        else:
                            logger.error(f"❌ 更新配置文件失败")
                    else:
                        logger.error(f"❌ 新token测试失败")
                else:
                    logger.error(f"❌ 刷新token失败: {result.get('error')}")
            else:
                logger.warning(f"⚠️ 没有找到refresh token")
                
        except Exception as e:
            logger.warning(f"⚠️ 读取OAuth tokens失败: {e}")
    
    # 如果所有配置都失败，提示重新授权
    logger.error(f"❌ 所有应用配置都刷新失败，需要重新进行OAuth授权")
    logger.info(f"💡 运行 feishu_oauth_client.py 重新进行OAuth流程")
    logger.info(f"🔗 或者访问飞书开放平台检查应用状态")
    
    # 显示当前的应用配置供参考
    print("\n📋 当前发现的应用配置:")
    for config in app_configs:
        print(f"  - {config['app_id']} (来源: {config['source']})")

if __name__ == "__main__":
    main() 