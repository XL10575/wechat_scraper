#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub Workflow状态检查工具
帮助用户快速检查workflow执行状态
"""

import webbrowser
import time

def main():
    print("🔍 GitHub Workflow状态检查指南")
    print("=" * 60)
    
    print("\n📋 检查步骤：")
    print("1. 打开GitHub仓库的Actions页面")
    print("2. 查看最新的workflow运行状态")
    print("3. 检查各个步骤的执行情况")
    
    # 获取GitHub仓库URL
    repo_url = input("\n请输入您的GitHub仓库URL (例如: https://github.com/username/repo): ").strip()
    
    if repo_url:
        # 构建Actions页面URL
        if repo_url.endswith('/'):
            repo_url = repo_url[:-1]
        
        actions_url = f"{repo_url}/actions"
        
        print(f"\n🔗 正在打开Actions页面: {actions_url}")
        webbrowser.open(actions_url)
        
        print("\n" + "=" * 60)
        print("📊 Workflow状态说明：")
        print("🟡 黄色圆圈 = 正在运行中")
        print("✅ 绿色对勾 = 执行成功")
        print("❌ 红色叉号 = 执行失败")
        print("⏸️ 灰色图标 = 已取消")
        
        print("\n🔍 重点检查的步骤：")
        print("1. '📥 检出代码' - 应该快速完成")
        print("2. '🐍 设置Python环境' - 安装Python和依赖")
        print("3. '🌐 安装Chrome浏览器' - 在Ubuntu上安装Chrome")
        print("4. '🔐 配置飞书认证信息和微信登录状态' - 恢复您的登录状态")
        print("5. '🤖 执行RO自动更新' - 核心功能，收集和上传文章")
        
        print("\n⚠️ 常见问题排查：")
        print("• 如果在'配置微信登录状态'步骤失败 → 检查WECHAT_COOKIES_B64和WECHAT_USER_AGENT secrets")
        print("• 如果在'执行RO自动更新'步骤失败 → 检查飞书相关的secrets配置")
        print("• 如果显示'未找到微信登录状态' → 重新运行setup_github_secrets.py生成新的secrets")
        
        print("\n📋 需要配置的Secrets清单：")
        secrets_list = [
            "FEISHU_APP_ID",
            "FEISHU_APP_SECRET", 
            "FEISHU_ACCESS_TOKEN",
            "FEISHU_REFRESH_TOKEN",
            "FEISHU_SPACE_TOKEN",
            "FEISHU_SPACE_ID",
            "WECHAT_COOKIES_B64",
            "WECHAT_USER_AGENT"
        ]
        
        for secret in secrets_list:
            print(f"• {secret}")
        
        print(f"\n🔗 Secrets配置页面: {repo_url}/settings/secrets/actions")
        
        # 询问是否需要打开secrets配置页面
        open_secrets = input("\n是否需要打开Secrets配置页面检查？(y/n): ").strip().lower()
        if open_secrets in ['y', 'yes', '是']:
            secrets_url = f"{repo_url}/settings/secrets/actions"
            print(f"🔗 正在打开Secrets配置页面: {secrets_url}")
            webbrowser.open(secrets_url)
        
        print("\n📈 监控建议：")
        print("• 第一次运行可能需要5-10分钟")
        print("• 可以实时查看日志输出")
        print("• 如果失败，查看具体错误信息")
        print("• 成功后会有上传的文件统计")
        
    else:
        print("❌ 未提供仓库URL")
    
    print("\n🎯 快速检查命令：")
    print("如果您想要快速检查最新的workflow状态，可以：")
    print("1. 进入仓库页面")
    print("2. 查看顶部是否有状态徽章")
    print("3. 点击Actions标签查看详细信息")

if __name__ == "__main__":
    main() 