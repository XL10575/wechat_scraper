# 微信公众号文章爬虫工具

项目文档：https://thedream.feishu.cn/docx/MZlNdoxoLotUOuxBkOocfnlinIh?from=from_copylink

## 项目简介

这是一个用于抓取和处理微信公众号文章的工具集，支持文章内容提取、批量处理、格式转换和导出功能。

## 项目结构

### 核心文件

- **`main.py`** - 微信文章URL处理器的主入口文件，提供命令行接口，支持单个或批量URL处理，可输出多种格式（JSON、Markdown、PDF、HTML）

- **`simple_url_scraper.py`** - 核心的URL处理工具，使用Selenium和BeautifulSoup实现微信文章内容抓取，包含浏览器自动化和内容解析功能

- **`wechat_gui.py`** - 图形用户界面，为微信文章下载提供可视化操作界面，集成了链接收集器和文章处理功能

- **`wechat_article_link_collector.py`** - 微信公众号文章链接批量获取工具，基于微信公众平台后台编辑功能的搜索API实现，支持批量收集指定公众号的文章链接

- **`feishu_exporter.py`** - 飞书知识库导出器，支持将微信公众号文章导出为适合飞书知识库的格式，包含改进的内容提取和反爬虫处理

### 配置和工具文件

- **`config.py`** - 项目配置文件，包含URL配置、文件路径、浏览器设置、爬虫设置、内容过滤和输出设置等全局配置项

- **`utils.py`** - 实用工具函数集合，提供JSON保存、随机延迟、文本清理、文章去重、数据验证和文件名格式化等功能

- **`requirements.txt`** - Python依赖包列表，包含项目运行所需的所有第三方库及其版本信息

- **`.gitignore`** - Git版本控制忽略文件配置

## 主要功能

1. **文章内容抓取** - 自动化浏览器抓取微信文章内容
2. **批量处理** - 支持批量URL处理和文章收集
3. **多格式输出** - 支持JSON、Markdown、PDF、HTML等多种输出格式
4. **图形界面** - 提供用户友好的GUI操作界面
5. **飞书集成** - 支持导出到飞书知识库格式
6. **反爬虫处理** - 包含验证码处理和请求频率控制

## 技术栈

- **Python 3.x** - 主要开发语言
- **Selenium** - 浏览器自动化
- **BeautifulSoup** - HTML解析
- **Tkinter** - GUI界面
- **Requests** - HTTP请求处理
- **Loguru** - 日志记录

## 注意事项

本工具仅供学习和研究使用，请遵守相关网站的使用条款和robots.txt规定，合理使用爬虫功能。