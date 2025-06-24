#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
更新飞书配置文件工具
使用正确的应用信息和最新的access token
"""

import json
import time
from datetime import datetime
from loguru import logger

def update_feishu_configs():
    """更新飞书配置文件"""
    
    # 正确的应用信息
    correct_app_id = "cli_a8c822312a75901c"
    correct_app_secret = "NDbCyKEwEIA8CZo2KHyqueIOlcafErko"
    
    # 读取OAuth tokens
    try:
        with open("feishu_oauth_tokens.json", "r", encoding="utf-8") as f:
            oauth_tokens = json.load(f)
        
        access_token = oauth_tokens["access_token"]
        refresh_token = oauth_tokens["refresh_token"]
        
        logger.info(f"✅ 读取到最新的access token: {access_token[:20]}...")
        
    except Exception as e:
        logger.error(f"❌ 读取OAuth tokens失败: {e}")
        return False
    
    # 读取现有的user_feishu_config.json保留其他配置
    try:
        with open("user_feishu_config.json", "r", encoding="utf-8") as f:
            user_config = json.load(f)
        
        logger.info(f"✅ 读取现有用户配置")
        
    except Exception as e:
        logger.warning(f"⚠️ 读取用户配置失败: {e}")
        user_config = {}
    
    # 更新用户配置
    user_config.update({
        "app_id": correct_app_id,
        "app_secret": correct_app_secret,
        "access_token": access_token,
        "test_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "test_success": True
    })
    
    # 保存更新后的用户配置
    try:
        with open("user_feishu_config.json", "w", encoding="utf-8") as f:
            json.dump(user_config, f, ensure_ascii=False, indent=2)
        
        logger.success(f"✅ 已更新 user_feishu_config.json")
        
    except Exception as e:
        logger.error(f"❌ 保存用户配置失败: {e}")
        return False
    
    # 输出GitHub Secrets值
    print("\n" + "="*60)
    print("🎉 更新后的GitHub Secrets值：")
    print("="*60)
    print(f"FEISHU_APP_ID: {correct_app_id}")
    print(f"FEISHU_APP_SECRET: {correct_app_secret}")
    print(f"FEISHU_ACCESS_TOKEN: {access_token}")
    print(f"FEISHU_REFRESH_TOKEN: {refresh_token}")
    print(f"FEISHU_SPACE_TOKEN: {user_config.get('space_token', '')}")
    print(f"FEISHU_SPACE_ID: {user_config.get('space_id', '')}")
    print("="*60)
    print("📋 请将以上值更新到GitHub Secrets中！")
    print("🔗 GitHub Secrets设置地址: https://github.com/YOUR_USERNAME/YOUR_REPO/settings/secrets/actions")
    
    return True

def test_new_config():
    """测试新配置是否有效"""
    try:
        import requests
        
        # 读取更新后的配置
        with open("user_feishu_config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
        
        access_token = config["access_token"]
        
        # 测试API调用
        url = "https://open.feishu.cn/open-apis/authen/v1/user_info"
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        
        logger.info("🧪 测试新配置的有效性...")
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            if result.get("code") == 0:
                user_info = result.get("data", {})
                logger.success(f"✅ 配置测试成功！用户: {user_info.get('name', '未知')}")
                return True
            else:
                logger.error(f"❌ API返回错误: {result}")
                return False
        else:
            logger.error(f"❌ HTTP请求失败: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"❌ 测试配置异常: {e}")
        return False

if __name__ == "__main__":
    logger.info("🚀 开始更新飞书配置...")
    
    if update_feishu_configs():
        logger.info("🧪 测试更新后的配置...")
        if test_new_config():
            logger.success("🎉 飞书配置更新完成且测试通过！")
        else:
            logger.warning("⚠️ 配置更新完成但测试失败，请检查")
    else:
        logger.error("❌ 配置更新失败") 