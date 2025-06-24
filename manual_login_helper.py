#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手动登录助手
指导用户使用现有GUI登录，然后保存会话状态
"""

import os
import json
import pickle
import base64
import time
import tkinter as tk
from tkinter import messagebox
from wechat_session_manager import WeChatSessionManager

def main():
    """主函数"""
    print("🚀 微信登录状态保存助手")
    print("=" * 50)
    
    print("📋 操作步骤：")
    print("1. 首先运行现有的GUI程序进行登录")
    print("2. 登录成功后，回到此程序保存会话状态")
    print()
    
    choice = input("请选择操作：\n1. 启动GUI程序登录\n2. 已经登录，保存会话状态\n请输入选择 (1或2): ")
    
    if choice == "1":
        print("\n🚀 正在启动GUI程序...")
        print("请在GUI程序中完成微信公众号登录")
        print("登录成功后，请关闭GUI程序并重新运行此脚本选择选项2")
        
        # 运行GUI程序
        import subprocess
        subprocess.run(["python", "wechat_gui.py"])
        
    elif choice == "2":
        save_session_from_cookies()
    else:
        print("❌ 无效选择")
        return False

def save_session_from_cookies():
    """从现有的cookies保存会话状态"""
    print("\n💾 正在保存微信登录状态...")
    
    session_manager = WeChatSessionManager()
    
    # 检查是否已有会话文件
    if session_manager.has_saved_session():
        print("✅ 发现现有会话文件")
        
        session_info = session_manager.get_session_info()
        if session_info:
            print(f"📊 会话信息:")
            print(f"   保存时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(session_info['timestamp']))}")
            print(f"   会话年龄: {session_info['age_hours']:.1f} 小时")
            print(f"   用户代理: {session_info['user_agent']}")
        
        choice = input("\n是否要重新生成GitHub Secrets配置？(y/n): ")
        if choice.lower() != 'y':
            print("操作取消")
            return
            
    else:
        print("❌ 没有找到保存的会话文件")
        print("📋 请先使用选项1启动GUI程序进行登录")
        return
    
    try:
        # 读取cookies文件
        if os.path.exists("wechat_cookies.pkl"):
            with open("wechat_cookies.pkl", "rb") as f:
                cookies = pickle.load(f)
        else:
            print("❌ 没有找到cookies文件，请先完成登录")
            return
        
        # 读取会话信息
        with open("wechat_session.json", "r", encoding="utf-8") as f:
            session_data = json.load(f)
        
        user_agent = session_data.get('user_agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        # 转换为Base64
        cookies_b64 = base64.b64encode(pickle.dumps(cookies)).decode('utf-8')
        
        # 生成GitHub Secrets配置文件
        secrets_content = f"""# 微信登录状态 GitHub Secrets 配置

请将以下内容添加到GitHub仓库的Secrets中：

## 步骤1：访问GitHub Secrets设置页面
https://github.com/XL10575/RO_auto/settings/secrets/actions

## 步骤2：添加以下两个Secrets

### Secret 1: WECHAT_COOKIES_B64
**名称:** `WECHAT_COOKIES_B64`
**值:**
```
{cookies_b64}
```

### Secret 2: WECHAT_USER_AGENT  
**名称:** `WECHAT_USER_AGENT`
**值:**
```
{user_agent}
```

## 步骤3：验证配置
- 配置完成后，GitHub Actions将自动使用保存的微信登录状态
- 无需手动登录即可执行自动更新任务
- 建议每1-2周重新运行此脚本更新登录状态

## 统计信息
- Cookies数量: {len(cookies)}
- 保存时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(session_data.get('timestamp', time.time())))}
- 用户代理: {user_agent}

## 注意事项
- 请确保Secret名称完全一致
- 如果登录失效，重新运行此脚本更新Secrets
- 建议定期检查GitHub Actions执行日志
"""
        
        # 保存到文件
        with open("WECHAT_SESSION_SECRETS.md", "w", encoding="utf-8") as f:
            f.write(secrets_content)
        
        print("✅ GitHub Secrets配置已生成")
        print(f"📁 配置文件: WECHAT_SESSION_SECRETS.md")
        print(f"📊 Cookies数量: {len(cookies)}")
        
        print("\n🎉 会话状态保存完成！")
        print("\n📋 下一步操作：")
        print("1. 打开生成的 WECHAT_SESSION_SECRETS.md 文件")
        print("2. 按照说明将两个Secrets添加到GitHub仓库")
        print("3. 重新运行GitHub Actions测试自动更新功能")
        
        # 询问是否直接打开配置文件
        choice = input("\n是否现在打开配置文件？(y/n): ")
        if choice.lower() == 'y':
            import subprocess
            subprocess.run(["notepad", "WECHAT_SESSION_SECRETS.md"])
        
        return True
        
    except Exception as e:
        print(f"❌ 保存会话状态失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ 用户中断操作")
    except Exception as e:
        print(f"\n❌ 执行失败: {e}")
        import traceback
        traceback.print_exc() 