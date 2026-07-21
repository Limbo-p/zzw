"""新浪财经首页新闻采集爬虫模板"""

import json
import os
import random
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

import requests
from lxml import html
from loguru import logger

from cjscript.config.settings import settings, PROJECT_ROOT

UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126.0",
]


def random_ua():
    return random.choice(UA_POOL)


def make_session():
    s = requests.Session()
    s.headers.update({
        "User-Agent": random_ua(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    })
    return s


def polite_delay():
    time.sleep(random.uniform(1.0, 2.0))


def url_fingerprint(url):
    import hashlib
    return hashlib.md5(url.strip().lower().encode()).hexdigest()


def fetch_article_urls(session, max_pages=3):
    """?7x24 API????URL??"""
    logger.info("??7x24????")

    api = "https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2509&k=&num=15&page={}"
    urls = []
    for pg in range(1, max_pages + 1):
        try:
            r = session.get(api.format(pg), timeout=10)
            data = r.json()
            items = data["result"]["data"]
            for item in items:
                url = item.get("url", "").rstrip(".")
                if url and "finance.sina.com.cn" in url:
                    urls.append(url)
            if len(items) < 15:
                break
        except Exception as e:
            logger.warning("API request failed page {}: {}", pg, e)
            break
    logger.info("??? {} ?7x24??", len(urls))
    return urls


def fetch_detail(session, url):
    try:
        polite_delay()
        resp = session.get(url, timeout=20)
        resp.encoding = "utf-8"
        tree = html.fromstring(resp.text)

        title = ""
        for sel in [".main-title", "h1", ".article-title", "title"]:
            el = tree.cssselect(sel)
            if el and el[0].text_content().strip():
                title = el[0].text_content().strip()
                break

        pub_time = ""
        for sel in [".date", ".time", ".info", ".article-info"]:
            el = tree.cssselect(sel)
            if el:
                pub_time = el[0].text_content().strip()
                break

        content = ""
        for sel in ["#artibody p", ".article-content p", ".main-content.w1240 p"]:
            paragraphs = tree.cssselect(sel)
            if paragraphs:
                content = "\n".join(p.text_content().strip() for p in paragraphs if p.text_content().strip())
                if len(content) > 100:
                    break

        return {
            "title": title,
            "source": "新浪财经",
            "pub_time": pub_time,
            "content": content,
            "url": url,
            "fingerprint": url_fingerprint(url),
            "crawled_at": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.warning("抓取失败 {}: {}", url, e)
        return None


def save_to_mongodb(results, collection="output/sina_7x24/"):
    if not results:
        return
    try:
        from pymongo import MongoClient
        client = MongoClient("172.19.0.2", 27017, serverSelectionTimeoutMS=3000)
        db = client["crawlab_test"]
        col = db[collection]
        task_id = os.environ.get("CRAWLAB_TASK_ID") or (Path(__file__).resolve().parent.parent.parent.name)
        if task_id:
            docs = [dict(r, task_id=task_id) for r in results]
        else:
            docs = results
        col.insert_many(docs)
        logger.info("MongoDB: {} results saved to crawlab_test.{}", len(results), collection)
    except Exception as e:
        logger.warning("MongoDB save failed: {}", e)


def run(max_articles=10, output_dir=None):
    """运行新浪财经爬虫"""
    logger.info("=" * 50)
    logger.info("新浪财经爬虫启动")

    session = make_session()
    urls = fetch_article_urls(session)

    if not urls:
        logger.warning("未提取到文章链接")
        return []

    results = []
    for i, url in enumerate(urls[:max_articles]):
        logger.info("[{}/{}] {}", i + 1, min(max_articles, len(urls)), url[:60])
        detail = fetch_detail(session, url)
        if detail:
            results.append(detail)

    out_dir = output_dir or (settings.output_dir / "sina_7x24")
    os.makedirs(out_dir, exist_ok=True)

    out_path = out_dir / f"sina_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(out_path, "w", encoding="utf-8") as f:
        for i, art in enumerate(results, 1):
            f.write(f"{'='*60}\n")
            f.write(f"[{i}] {art.get('title', '')}\n")
            f.write(f"source: {art.get('source', '')}\n")
            f.write(f"time: {art.get('pub_time', '')}\n")
            f.write(f"url: {art.get('url', '')}\n")
            f.write(f"{'-'*60}\n")
            f.write(f"{art.get('content', '')}\n\n")

    save_to_mongodb(results)

    logger.info("=" * 50)
    logger.info("完成: {} 条 -> {}", len(results), out_path)
    return results


if __name__ == "__main__":
    run()
