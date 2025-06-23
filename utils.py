# -*- coding: utf-8 -*-
"""
Utility functions for WeChat scraper
"""
import json
import os
import time
import random
from typing import List, Dict, Any
from loguru import logger
from config import OUTPUT_DIR, JSON_INDENT, REQUEST_DELAY_RANGE


def save_to_json(data: List[Dict[str, Any]], filename: str) -> bool:
    """
    Save article data to JSON file
    
    Args:
        data: List of article dictionaries
        filename: Output filename
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Ensure output directory exists
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        # Full file path
        filepath = os.path.join(OUTPUT_DIR, filename)
        
        # Save data with proper formatting
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=JSON_INDENT, default=str)
        
        logger.info(f"Successfully saved {len(data)} articles to {filepath}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to save data to {filename}: {str(e)}")
        return False


def random_delay(min_delay: int = None, max_delay: int = None) -> None:
    """
    Add random delay to mimic human behavior
    
    Args:
        min_delay: Minimum delay in seconds
        max_delay: Maximum delay in seconds
    """
    if min_delay is None or max_delay is None:
        min_delay, max_delay = REQUEST_DELAY_RANGE
    
    delay = random.uniform(min_delay, max_delay)
    logger.debug(f"Waiting {delay:.2f} seconds...")
    time.sleep(delay)


def clean_text(text: str) -> str:
    """
    Clean and normalize text content
    
    Args:
        text: Raw text content
        
    Returns:
        str: Cleaned text
    """
    if not text:
        return ""
    
    # Remove extra whitespace and normalize
    text = ' '.join(text.split())
    
    # Remove common WeChat promotional text
    promotional_phrases = [
        "长按二维码关注", "扫描二维码关注", "点击关注", "微信号：",
        "往期精彩回顾", "点击阅读原文", "阅读原文", "分享给朋友"
    ]
    
    for phrase in promotional_phrases:
        text = text.replace(phrase, "")
    
    return text.strip()


def deduplicate_articles(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Remove duplicate articles based on URL
    
    Args:
        articles: List of article dictionaries
        
    Returns:
        List[Dict]: Deduplicated articles
    """
    seen_urls = set()
    unique_articles = []
    
    for article in articles:
        url = article.get('url', '')
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_articles.append(article)
        elif url in seen_urls:
            logger.debug(f"Duplicate article found: {article.get('title', 'Unknown')}")
    
    logger.info(f"Removed {len(articles) - len(unique_articles)} duplicate articles")
    return unique_articles


def validate_article_data(article: Dict[str, Any]) -> bool:
    """
    Validate article data structure
    
    Args:
        article: Article dictionary
        
    Returns:
        bool: True if valid, False otherwise
    """
    required_fields = ['title', 'url', 'publish_date', 'author']
    
    for field in required_fields:
        if field not in article or not article[field]:
            logger.warning(f"Article missing required field '{field}': {article.get('title', 'Unknown')}")
            return False
    
    return True


def format_filename(account_name: str, timestamp: str = None) -> str:
    """
    Format output filename based on account name and timestamp
    
    Args:
        account_name: WeChat account name
        timestamp: Optional timestamp string
        
    Returns:
        str: Formatted filename
    """
    # Clean account name for filename
    clean_name = "".join(c for c in account_name if c.isalnum() or c in (' ', '-', '_')).strip()
    clean_name = clean_name.replace(' ', '_')
    
    if timestamp is None:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
    
    return f"wechat_{clean_name}_{timestamp}.json" 