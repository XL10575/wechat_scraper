#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub Actions 自动部署脚本
自动读取本地配置并生成GitHub Secrets配置说明
"""

import json
import os
import sys
from pathlib import Path

def load_json_file(file_path):
    """安全加载JSON文件"""
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"⚠️ 读取文件 {file_path} 失败: {e}")
    return {}

def main():
    """主函数"""
    print("🚀 GitHub Actions 自动部署助手")
    print("=" * 60)
    
    # 检查必要文件
    required_files = [
        'feishu_oauth_tokens.json',
        'user_feishu_config.json',
        '.github/workflows/auto-update.yml'
    ]
    
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        print("❌ 缺少必要文件:")
        for file_path in missing_files:
            print(f"   - {file_path}")
        print("\n请确保已完成飞书配置和GitHub Actions工作流创建")
        return False
    
    # 读取配置文件
    print("📋 读取本地配置文件...")
    
    oauth_tokens = load_json_file('feishu_oauth_tokens.json')
    user_config = load_json_file('user_feishu_config.json')
    
    # 提取必要信息
    secrets_config = {
        'FEISHU_APP_ID': user_config.get('app_id', ''),
        'FEISHU_APP_SECRET': user_config.get('app_secret', ''),
        'FEISHU_ACCESS_TOKEN': oauth_tokens.get('access_token', ''),
        'FEISHU_REFRESH_TOKEN': oauth_tokens.get('refresh_token', ''),
        'FEISHU_SPACE_TOKEN': user_config.get('space_token', ''),
        'FEISHU_SPACE_ID': user_config.get('space_id', ''),
    }
    
    # 检查配置完整性
    missing_configs = []
    for key, value in secrets_config.items():
        if not value:
            missing_configs.append(key)
    
    if missing_configs:
        print("❌ 配置信息缺失:")
        for key in missing_configs:
            print(f"   - {key}")
        print("\n请完成飞书OAuth认证和用户配置")
        return False
    
    print("✅ 配置文件读取完成")
    
    # 生成GitHub Secrets配置说明
    print("\n📝 生成GitHub Secrets配置...")
    
    secrets_content = """
# GitHub Secrets 配置说明

请在GitHub仓库中配置以下Secrets：

## 🔧 进入Settings → Secrets and variables → Actions

然后逐一添加以下Secrets：

"""
    
    for key, value in secrets_config.items():
        # 隐藏敏感信息的部分内容
        if len(value) > 10:
            display_value = value[:6] + "..." + value[-4:]
        else:
            display_value = value
            
        secrets_content += f"""
### {key}
```
{value}
```
显示值: `{display_value}`

"""
    
    # 保存到文件
    with open('GITHUB_SECRETS.md', 'w', encoding='utf-8') as f:
        f.write(secrets_content)
    
    print("✅ GitHub Secrets配置已生成到: GITHUB_SECRETS.md")
    
    # 生成部署命令
    print("\n🚀 GitHub部署步骤:")
    print("1. 确保代码已推送到GitHub仓库")
    print("2. 根据 GITHUB_SECRETS.md 配置GitHub Secrets")
    print("3. 进入仓库的Actions页面启用工作流")
    print("4. 手动触发测试或等待定时执行")
    
    # 检查Git状态
    if os.path.exists('.git'):
        print("\n📋 Git仓库状态:")
        os.system('git status --porcelain')
        
        print("\n💡 推送到GitHub命令:")
        print("git add .")
        print("git commit -m 'Add GitHub Actions auto-update workflow'")
        print("git push origin main")
    else:
        print("\n💡 初始化Git仓库命令:")
        print("git init")
        print("git add .")
        print("git commit -m 'Initial commit: WeChat scraper with auto-update'")
        print("git remote add origin https://github.com/YOUR_USERNAME/wechat-scraper.git")
        print("git push -u origin main")
    
    print("\n🎉 部署准备完成！")
    print("📖 详细部署指南请查看: DEPLOY_GUIDE.md")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 