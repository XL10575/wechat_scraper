@echo off
chcp 65001 >nul
title 清理构建文件

echo.
echo 🧹 清理PyInstaller构建文件...
echo.

if exist "build" (
    rmdir /s /q "build"
    echo ✅ 清理 build/ 目录
)

if exist "dist" (
    rmdir /s /q "dist"
    echo ✅ 清理 dist/ 目录
)

if exist "wechat_scraper.spec" (
    del "wechat_scraper.spec"
    echo ✅ 删除 wechat_scraper.spec
)

if exist "__pycache__" (
    rmdir /s /q "__pycache__"
    echo ✅ 清理 __pycache__/ 目录
)

echo.
echo ✅ 构建文件清理完成！
echo 💡 分发包 WeChat_Article_Scraper_Portable 已保留
echo.

pause 