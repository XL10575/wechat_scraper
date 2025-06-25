#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信文章抓取工具 - EXE打包脚本
自动安装PyInstaller并打包项目为exe文件
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def install_pyinstaller():
    """安装PyInstaller"""
    print("🔧 检查并安装PyInstaller...")
    try:
        import PyInstaller
        print("✅ PyInstaller已安装")
        return True
    except ImportError:
        print("📦 正在安装PyInstaller...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
            print("✅ PyInstaller安装成功")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ PyInstaller安装失败: {e}")
            return False

def create_spec_file():
    """创建PyInstaller spec文件"""
    print("📝 创建PyInstaller配置文件...")
    
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['wechat_gui.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('feishu_integration_config.json', '.'),
        ('wiki_location_config.json', '.'),
        ('user_feishu_config.json', '.'),
        ('飞书API错误代码说明.md', '.'),
        ('DOCX导入功能更新说明.md', '.'),
        ('OAuth认证使用指南.md', '.'),
        ('README.md', '.'),
    ],
    hiddenimports=[
        'selenium',
        'selenium.webdriver',
        'selenium.webdriver.chrome',
        'selenium.webdriver.chrome.service',
        'selenium.webdriver.chrome.options',
        'selenium.webdriver.common.by',
        'selenium.webdriver.support.ui',
        'selenium.webdriver.support.expected_conditions',
        'webdriver_manager',
        'webdriver_manager.chrome',
        'undetected_chromedriver',
        'beautifulsoup4',
        'bs4',
        'loguru',
        'tqdm',
        'requests',
        'requests_toolbelt',
        'lxml',
        'PIL',
        'PIL.Image',
        'urllib3',
        'docx',
        'python_docx',
        'tkinter',
        'tkinter.ttk',
        'tkinter.scrolledtext',
        'tkinter.filedialog',
        'tkinter.messagebox',
        'json',
        'threading',
        'queue',
        'webbrowser',
        'datetime',
        'pathlib',
        'base64',
        'tempfile',
        'time',
        'os',
        'sys',
        'shutil',
        'zipfile',
        'io',
        'csv',
        'argparse',
        'typing',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'test_*',
        'debug_*',
        'temp_*',
        'logs',
        'output',
        '__pycache__',
        '.git',
        '.gitignore',
        '*.pyc',
        '*.pyo',
        '*.log',
        '*.backup',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='微信文章抓取工具',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 不显示控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # 可以添加图标文件路径
    version_file=None,
)
'''
    
    with open('wechat_scraper.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    print("✅ PyInstaller配置文件创建完成")

def clean_build_dirs():
    """清理构建目录"""
    print("🧹 清理旧的构建文件...")
    
    dirs_to_clean = ['build', 'dist', '__pycache__']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"  ✅ 清理 {dir_name}/")
    
    # 清理.pyc文件
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.pyc'):
                os.remove(os.path.join(root, file))

def build_exe():
    """构建exe文件"""
    print("🚀 开始构建exe文件...")
    print("⏳ 这可能需要几分钟时间，请耐心等待...")
    
    try:
        # 使用spec文件构建
        cmd = [sys.executable, "-m", "PyInstaller", "--clean", "wechat_scraper.spec"]
        
        print(f"执行命令: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
        
        if result.returncode == 0:
            print("✅ exe文件构建成功！")
            
            # 检查生成的exe文件
            exe_path = Path("dist/微信文章抓取工具.exe")
            if exe_path.exists():
                size_mb = exe_path.stat().st_size / (1024 * 1024)
                print(f"📦 生成的exe文件: {exe_path}")
                print(f"📊 文件大小: {size_mb:.1f} MB")
                return True
            else:
                print("❌ 未找到生成的exe文件")
                return False
        else:
            print("❌ 构建失败！")
            print("错误输出:")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ 构建过程出错: {e}")
        return False

def create_distribution_package():
    """创建分发包"""
    print("📦 创建分发包...")
    
    dist_dir = Path("WeChat_Article_Scraper_Portable")
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    
    dist_dir.mkdir()
    
    # 复制exe文件
    exe_source = Path("dist/微信文章抓取工具.exe")
    if exe_source.exists():
        shutil.copy2(exe_source, dist_dir / "微信文章抓取工具.exe")
    
    # 复制必要的配置文件
    config_files = [
        "README.md",
        "OAuth认证使用指南.md",
        "DOCX导入功能更新说明.md",
        "飞书API错误代码说明.md",
    ]
    
    for config_file in config_files:
        if os.path.exists(config_file):
            shutil.copy2(config_file, dist_dir)
    
    # 创建使用说明
    usage_guide = """# 微信文章抓取工具 - 使用说明

## 🚀 快速开始

1. **双击运行** `微信文章抓取工具.exe`
2. **选择功能标签页**：
   - 📄 单篇下载：下载单个微信文章
   - 📚 批量下载：批量下载多个文章
   - 🔗 链接收集：收集公众号历史文章链接
   - ⚙️ 设置：配置飞书集成和智能分类

## 📋 主要功能

### 📄 单篇下载
- 输入微信文章URL
- 选择下载格式（PDF推荐）
- 点击开始下载

### 📚 批量下载  
- 在文本框中输入多个URL（每行一个）
- 或从文件加载URL列表
- 支持多种格式同时下载

### 🔗 链接收集
- 扫码登录微信公众平台
- 搜索公众号
- 批量收集历史文章链接

### ⚙️ 飞书集成
- 配置飞书API令牌
- 智能分类上传到知识库
- 支持OAuth认证

## 📁 输出文件

下载的文件保存在程序目录下的 `output` 文件夹中：
- `output/pdf/` - PDF文件
- `output/html/` - HTML文件  
- `output/markdown/` - Markdown文件
- `output/docx/` - Word文档

## ⚠️ 注意事项

1. **首次运行**：程序会自动下载Chrome驱动
2. **网络连接**：需要稳定的网络连接
3. **防火墙**：允许程序访问网络
4. **杀毒软件**：如被误报，请添加信任

## 🔧 故障排除

如果遇到问题：
1. 检查网络连接
2. 重启程序
3. 查看日志文件（logs目录）
4. 参考README.md获取详细说明

## 📞 技术支持

如需帮助，请查看项目README.md文件获取详细信息。
"""
    
    with open(dist_dir / "使用说明.txt", 'w', encoding='utf-8') as f:
        f.write(usage_guide)
    
    print(f"✅ 分发包创建完成: {dist_dir}")
    return dist_dir

def main():
    """主函数"""
    print("=" * 60)
    print("🚀 微信文章抓取工具 - EXE打包程序")
    print("=" * 60)
    
    # 检查当前目录
    if not os.path.exists('wechat_gui.py'):
        print("❌ 错误：未找到 wechat_gui.py 文件")
        print("请确保在项目根目录下运行此脚本")
        return False
    
    # 安装PyInstaller
    if not install_pyinstaller():
        return False
    
    # 清理构建目录
    clean_build_dirs()
    
    # 创建spec文件
    create_spec_file()
    
    # 构建exe
    if not build_exe():
        return False
    
    # 创建分发包
    dist_dir = create_distribution_package()
    
    print("\n" + "=" * 60)
    print("🎉 打包完成！")
    print("=" * 60)
    print(f"📦 分发包位置: {dist_dir.absolute()}")
    print("📋 包含文件:")
    for file in dist_dir.iterdir():
        if file.is_file():
            size_mb = file.stat().st_size / (1024 * 1024)
            print(f"  - {file.name} ({size_mb:.1f} MB)")
    
    print("\n💡 使用提示:")
    print("1. 将整个文件夹复制到目标电脑")
    print("2. 双击运行 '微信文章抓取工具.exe'")
    print("3. 首次运行会自动下载Chrome驱动")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        if success:
            input("\n按回车键退出...")
        else:
            input("\n打包失败，按回车键退出...")
    except KeyboardInterrupt:
        print("\n\n❌ 用户中断操作")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        input("按回车键退出...") 