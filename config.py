# -*- coding: utf-8 -*-
"""
Configuration settings for WeChat scraper
"""
import os

# URLs
SOGOU_WECHAT_SEARCH_URL = "https://weixin.sogou.com/"
WECHAT_BASE_URL = "https://mp.weixin.qq.com"

# File paths
OUTPUT_DIR = "output"
LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "wechat_scraper.log")

# Browser settings
USER_AGENTS = [
    # WeChat-like user agents
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/18A373 MicroMessenger/8.0.37(0x18002530) NetType/WIFI Language/zh_CN",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/19A346 MicroMessenger/8.0.38(0x18002631) NetType/WIFI Language/zh_CN",
    "Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Mobile Safari/537.36 MicroMessenger/8.0.37(0x18002530) NetType/WIFI Language/zh_CN",
    # Regular mobile user agents
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Mobile Safari/537.36",
    # Desktop fallbacks
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

# Scraping settings
DEFAULT_SCROLL_DELAY = 6  # seconds - 增加到6秒确保图片充分加载
MAX_SCROLL_ATTEMPTS = 100
PAGE_LOAD_TIMEOUT = 30  # seconds
ELEMENT_WAIT_TIMEOUT = 10  # seconds
REQUEST_DELAY_RANGE = (2, 5)  # seconds (min, max)

# Content filtering
EXCLUDED_ELEMENTS = [
    'script', 'style', 'iframe', 'noscript',
    # WeChat specific ad/promotion elements
    '.rich_media_area_extra', '.reward_area', '.share_area',
    '.js_vote_area', '.js_editor_vote_card', '.weapp_display_element',
    '.qr_code_pc_outer', '.code-snippet__fix'
]

# Output settings
DEFAULT_OUTPUT_FILENAME = "wechat_articles.json"
JSON_INDENT = 2

# Create directories if they don't exist
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True) 