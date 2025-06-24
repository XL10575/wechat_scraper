#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版微信登录状态保存工具
基于现有的链接收集器，手动登录后保存状态
"""

import os
import json
import pickle
import base64
import time
from wechat_article_link_collector import WeChatLinkCollector
from wechat_session_manager import WeChatSessionManager

def main():
    """主函数"""
    print("🚀 简化版微信登录状态保存工具")
    print("=" * 50)
    
    collector = None
    session_manager = WeChatSessionManager()
    
    try:
        print("📱 步骤1: 启动链接收集器并登录...")
        
        # 使用现有的链接收集器
        collector = WeChatLinkCollector(headless=False)
        
        print("🔐 请在打开的浏览器中手动登录微信公众号...")
        print("   1. 扫码登录微信公众号平台")
        print("   2. 确保进入到主页面")
        print("   3. 登录完成后回到这里按回车")
        
        input("\n✅ 登录完成后，按回车键继续...")
        
        print("\n💾 步骤2: 保存登录状态...")
        
        # 保存会话状态
        if session_manager.save_session_from_driver(collector.driver):
            print("✅ 会话状态保存成功")
        else:
            print("❌ 会话状态保存失败")
            return False
        
        print("\n🧪 步骤3: 生成GitHub Secrets配置...")
        
        # 读取保存的cookies并转换为Base64
        if os.path.exists("wechat_cookies.pkl"):
            with open("wechat_cookies.pkl", "rb") as f:
                cookies = pickle.load(f)
            
            cookies_b64 = base64.b64encode(pickle.dumps(cookies)).decode('utf-8')
            
            # 获取用户代理
            try:
                user_agent = collector.driver.execute_script("return navigator.userAgent;")
            except:
                user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            
            # 生成GitHub Secrets配置
            secrets_content = f"""# 微信登录状态 GitHub Secrets 配置

请在GitHub仓库中添加以下两个Secrets：

## WECHAT_COOKIES_B64
```
{cookies_b64}
```

## WECHAT_USER_AGENT
```
{user_agent}
```

## 配置步骤：
1. 访问：https://github.com/XL10575/RO_auto/settings/secrets/actions
2. 点击 "New repository secret"
3. 逐一添加上面的两个Secrets
4. 名称必须完全一致：WECHAT_COOKIES_B64 和 WECHAT_USER_AGENT

## 验证配置：
- 配置完成后，GitHub Actions将能够使用保存的微信登录状态
- 每次执行时都会自动恢复登录状态，无需手动登录
- 建议定期（1-2周）重新运行此脚本更新登录状态
"""
            
            with open("WECHAT_SESSION_SECRETS.md", "w", encoding="utf-8") as f:
                f.write(secrets_content)
            
            print("✅ GitHub Secrets配置已生成到: WECHAT_SESSION_SECRETS.md")
            
            # 显示会话信息
            session_info = session_manager.get_session_info()
            if session_info:
                print(f"\n📊 会话信息:")
                print(f"   保存时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(session_info['timestamp']))}")
                print(f"   用户代理: {session_info['user_agent']}")
                print(f"   Cookies数量: {len(cookies)}")
            
        else:
            print("❌ 没有找到保存的cookies文件")
            return False
        
        print("\n🎉 微信登录状态保存完成！")
        print("\n📋 下一步：")
        print("1. 查看 WECHAT_SESSION_SECRETS.md 文件")
        print("2. 按照说明将Secrets添加到GitHub仓库")
        print("3. 重新运行GitHub Actions测试自动更新")
        
        return True
        
    except Exception as e:
        print(f"❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        if collector:
            input("\n按回车键关闭浏览器...")
            collector.cleanup()

if __name__ == "__main__":
    success = main()
    if not success:
        print("\n❌ 登录状态保存失败")
        exit(1)
    else:
        print("\n✅ 登录状态保存成功") 