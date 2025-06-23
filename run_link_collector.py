#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信公众号文章链接收集器启动脚本
"""

import sys
import os

def main():
    """主函数"""
    print("=" * 60)
    print("🔗 微信公众号文章链接收集器 v1.0")
    print("=" * 60)
    print()
    print("功能说明:")
    print("• 🚀 扫码登录微信公众号")
    print("• 🔍 搜索目标公众号")
    print("• 📥 批量获取文章链接")
    print("• 📊 支持导出CSV/JSON/TXT格式")
    print("• ⏱️ 自动频率控制，避免触发限制")
    print()
    print("使用步骤:")
    print("1. 点击'开始登录'按钮")
    print("2. 用微信扫描二维码登录")
    print("3. 输入公众号名称搜索")
    print("4. 选择公众号并设置获取参数")
    print("5. 点击'获取文章链接'开始收集")
    print("6. 导出为需要的格式")
    print()
    print("注意事项:")
    print("• 请使用有公众号权限的微信账号登录")
    print("• 建议单次获取不超过500篇文章")
    print("• 登录有效期约4天，可重复使用")
    print("• 导出的TXT文件可直接用于wechat_scraper批量下载")
    print()
    print("=" * 60)
    
    try:
        from wechat_article_link_collector import WeChatLinkCollector
        
        print("🚀 正在启动...")
        collector = WeChatLinkCollector()
        collector.run()
        
    except ImportError as e:
        print(f"❌ 导入模块失败: {e}")
        print("请确保已安装所有依赖包:")
        print("pip install -r requirements.txt")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n👋 程序已退出")


if __name__ == "__main__":
    main() 