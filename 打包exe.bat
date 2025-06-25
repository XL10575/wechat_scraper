@echo off
chcp 65001 >nul
title 微信文章抓取工具 - EXE打包

echo.
echo ====================================
echo 🚀 微信文章抓取工具 - EXE打包
echo ====================================
echo.

echo 📋 开始自动打包流程...
echo 💡 这个过程可能需要5-10分钟，请耐心等待
echo.

python build_exe.py

echo.
echo 📦 打包完成！
echo 💡 生成的exe文件在 WeChat_Article_Scraper_Portable 文件夹中
echo.

pause 