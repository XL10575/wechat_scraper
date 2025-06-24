#!/usr/bin/env python3
"""
GitHub Actions 微信登录状态设置助手

这个脚本帮助你获取微信登录状态，并生成GitHub Secrets所需的值。
在设置完GitHub Secrets后，workflow就能自动运行了。

使用方法：
1. 运行这个脚本
2. 扫描二维码登录微信
3. 复制生成的Secrets值到GitHub仓库设置中
"""

import os
import sys
import json
import base64
import pickle
from datetime import datetime, timedelta

def main():
    print("🚀 GitHub Actions 微信登录状态设置助手")
    print("=" * 60)
    
    try:
        from login_and_save_session import WeChatSessionSaver
    except ImportError as e:
        print(f"❌ 导入模块失败: {e}")
        print("请确保已安装所有依赖: pip install -r requirements.txt")
        return False
    
    # 步骤1: 获取微信登录状态
    print("🔐 步骤1: 获取微信登录状态...")
    print("即将打开浏览器，请准备扫描微信二维码")
    input("按回车键继续...")
    
    try:
        # 创建会话保存器
        session_saver = WeChatSessionSaver()
        
        # 设置浏览器（非无头模式，显示二维码）
        if not session_saver.setup_driver(headless=False):
            print("❌ 浏览器启动失败")
            return False
        
        print("🔍 正在打开微信公众号平台...")
        login_success = session_saver.login_wechat()
        
        if not login_success:
            print("❌ 微信登录失败")
            session_saver.cleanup()
            return False
            
        print("✅ 微信登录成功！")
        
        # 步骤2: 保存登录状态
        print("💾 步骤2: 保存登录状态...")
        
        if not session_saver.save_session_state():
            print("❌ 保存登录状态失败")
            session_saver.cleanup()
            return False
        
        # 步骤3: 生成GitHub Secrets值
        print("🔑 步骤3: 生成GitHub Secrets值...")
        
        # 读取生成的文件
        if not os.path.exists('wechat_cookies.pkl'):
            print("❌ 未找到cookies文件")
            session_saver.cleanup()
            return False
        
        if not os.path.exists('wechat_session.json'):
            print("❌ 未找到session文件")
            session_saver.cleanup()
            return False
        
        # 读取cookies并转换为base64
        with open('wechat_cookies.pkl', 'rb') as f:
            cookies_data = f.read()
            cookies_b64 = base64.b64encode(cookies_data).decode('utf-8')
        
        # 读取session信息
        with open('wechat_session.json', 'r', encoding='utf-8') as f:
            session_data = json.load(f)
            user_agent = session_data.get('user_agent', '')
        
        print("\n" + "="*80)
        print("🎯 请将以下值添加到你的GitHub仓库的Secrets中:")
        print("="*80)
        print()
        print("1. 进入你的GitHub仓库")
        print("2. 点击 Settings -> Secrets and variables -> Actions")
        print("3. 点击 'New repository secret' 添加以下secrets:")
        print()
        print(f"Secret名称: WECHAT_COOKIES_B64")
        print(f"Secret值:")
        print(cookies_b64[:100] + "..." if len(cookies_b64) > 100 else cookies_b64)
        print("(完整值请查看 WECHAT_SESSION_SECRETS.md 文件)")
        print()
        print(f"Secret名称: WECHAT_USER_AGENT")
        print(f"Secret值:")
        print(user_agent)
        print()
        print("="*80)
        print("✅ 设置完成后，你的workflow就能自动运行了！")
        print()
        
        # 步骤4: 测试会话恢复
        print("🧪 步骤4: 测试会话恢复...")
        
        test_success = session_saver.test_session_restore()
        if test_success:
            print("✅ 会话恢复测试成功！")
        else:
            print("⚠️ 会话恢复测试失败，但这可能是正常的")
            print("GitHub Actions会使用保存的状态重新建立会话")
        
        # 清理浏览器
        session_saver.cleanup()
        
        print()
        print("📋 生成的文件:")
        print(f"  - wechat_cookies.pkl (cookies数据)")
        print(f"  - wechat_session.json (会话信息)")
        print(f"  - WECHAT_SESSION_SECRETS.md (GitHub Secrets配置)")
        print()
        print("🎉 设置完成！现在你可以:")
        print("1. 查看 WECHAT_SESSION_SECRETS.md 文件获取完整的Secret值")
        print("2. 将Secret值添加到GitHub仓库设置中")
        print("3. 手动触发workflow测试")
        print("4. 等待每天自动执行")
        print()
        print("💡 提示:")
        print("- workflow会在每天北京时间上午10:00自动执行")
        print("- 你也可以随时手动触发workflow")
        print("- 微信登录状态会自动维护，不需要重复设置")
        
        return True
        
    except Exception as e:
        print(f"❌ 设置过程出错: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1) 