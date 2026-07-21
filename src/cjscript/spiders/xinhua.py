"""
中证网 (cs.com.cn) 新华社记者文章爬虫

策略:
  1. Playwright 打开搜索页，输入"新华社记者"获取文章 URL 列表
  2. 搜索结果阶段预过滤：来源含"新华社" + 作者含"记者"
  3. requests + lxml 抓取详情页（服务端渲染，无需浏览器）
  4. 详情页二次过滤：来源含"新华社"且正文含"新华社记者"

用法:
  python -m cjscript.spiders.xinhua
  python -m cjscript.main xinhua

依赖: pip install playwright requests lxml && playwright install chromium
"""

import hashlib
import json
import os
import random
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

import requests
from lxml import html
from loguru import logger

import sys

# When run directly (python xinhua.py), ensure src/ is on sys.path
_src = Path(__file__).resolve().parent.parent.parent
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from cjscript.config.settings import settings, PROJECT_ROOT

# ===== 工具函数 =====

UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
]


def random_ua():
    return random.choice(UA_POOL)


def make_session():
    s = requests.Session()
    s.headers.update({
        "User-Agent":      random_ua(),
        "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Cache-Control":   "no-cache",
    })
    return s


def polite_delay(min_s: float = 1.0, max_s: float = 3.0):
    time.sleep(random.uniform(min_s, max_s))


def url_fingerprint(url):
    return hashlib.md5(url.strip().lower().encode()).hexdigest()


def _extract_first(text, patterns):
    """依次用多个正则尝试提取，返回第一个成功的捕获组。"""
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            return m.group(1).strip()
    return ""


# ===== 阶段 1: Playwright 搜索 =====

def discover_article_urls(
    keyword: str = "新华社记者",
    max_pages: int = 3,
    headless: bool = True,
) -> list[dict]:
    """Playwright 打开搜索页，输入关键词，翻页提取文章列表。
    返回: [{"title","url","source","author","pub_time"}, ...]
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.error("playwright 未安装。请执行: pip install playwright && playwright install chromium")
        raise

    base_url = settings.cs_base_url
    search_url = f"{base_url}/searchlist.html"
    articles = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            user_agent=random_ua(),
            viewport={"width": 1280, "height": 800},
            locale="zh-CN",
        )
        page = context.new_page()

        try:
            logger.info("打开搜索页: {}", search_url)
            page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
        except Exception as e:
            logger.error("搜索页加载失败: {}", e)
            browser.close()
            return []

        logger.info("输入关键词: {}", keyword)
        try:
            page.fill("input#textfield, input[name='searchword']", keyword, timeout=5000)
        except Exception:
            logger.warning("未找到搜索输入框 #textfield，尝试通用 input")
            try:
                page.fill("input[type='text']", keyword)
            except Exception:
                logger.error("未找到任何输入框，搜索页 DOM 可能已变化")
                browser.close()
                return []
        try:
            page.click("input.submit, button.submit, .sea.submit")
        except Exception as e:
            logger.error("点击搜索按钮失败: {}", e)
            browser.close()
            return []

        # 等待 AJAX 结果
        for selector in ["#waslist", "#list", ".searchList", "table"]:
            try:
                page.wait_for_selector(selector, timeout=8000)
                logger.info("搜索结果容器: {}", selector)
                break
            except Exception:
                continue
        else:
            logger.warning("未识别到搜索结果容器，等待 5 秒后尝试提取")
            page.wait_for_timeout(5000)

        for pg in range(1, max_pages + 1):
            logger.info("翻页 {} / {}", pg, max_pages)
            page.wait_for_timeout(2000)

            content = page.content()
            tree = html.fromstring(content)

            # 通用搜索结果选择器
            result_items = tree.cssselect(
                "#waslist li, #list li, .searchList li, "
                ".list li, ul.list li, .result li, .item, "
                "tr"
            )
            if not result_items:
                logger.warning("第 {} 页未找到结果项", pg)
                snippet = tree.text_content()[:1000]
                logger.info("页面文本片段: {}", snippet)
                break

            for item in result_items:
                link = item.cssselect("a[href*='detail_']")
                if not link:
                    continue
                url = urljoin(base_url, link[0].get("href", ""))
                title = link[0].text_content().strip() or ""

                meta_text = item.text_content()
                source  = _extract_first(meta_text,
                    [r"来源[：:]\s*(.+?)(?:\s|作者|发布|$)",
                     r"来源[：:]\s*(\S+)"])
                author  = _extract_first(meta_text,
                    [r"作者[：:]\s*(.+?)(?:\s|发布|来源|$)",
                     r"作者[：:]\s*(\S+)"])
                pubtime = _extract_first(meta_text,
                    [r"发布时间[：:]\s*(\d{4}-\d{2}-\d{2})",
                     r"(\d{4}-\d{2}-\d{2}\s*\d{2}:\d{2})"])

                # 预过滤
                if source and "新华社" not in source:
                    continue
                if author and "记者" not in author:
                    continue

                articles.append({
                    "title":    title,
                    "url":      url,
                    "source":   source,
                    "author":   author,
                    "pub_time": pubtime,
                })

            if pg < max_pages:
                next_btn = page.query_selector(
                    ".pagination .next, a.next, .page-link:has-text('下一页'), "
                    "a:has-text('下一页'), a:has-text('>')"
                )
                if next_btn:
                    next_btn.click()
                else:
                    logger.info("无下一页，搜索结束")
                    break

        browser.close()

    logger.info("搜索阶段: {} 条（已预过滤）", len(articles))
    return articles


# ===== 阶段 2: 抓取详情页 =====

def fetch_detail(session, url: str) -> Optional[dict]:
    """抓取文章详情页（服务端渲染）。"""
    try:
        polite_delay(settings.pw_delay_min, settings.pw_delay_max)
        resp = session.get(url, timeout=settings.request_timeout)
        resp.raise_for_status()
        resp.encoding = "utf-8"
        tree = html.fromstring(resp.text)

        # 标题
        title = ""
        for sel in ["title", "h1", ".title", ".art_title"]:
            el = tree.cssselect(sel)
            if el:
                title = el[0].text_content().strip()
                if title:
                    break

        # 来源 & 时间
        source = ""
        pub_time = ""
        em_tags = tree.cssselect(".artc_info em")
        if em_tags:
            source = em_tags[0].text_content().strip()
        time_tags = tree.cssselect(".artc_info time, .artc_info .time, .pub_time")
        if time_tags:
            pub_time = time_tags[0].text_content().strip()

        # 正文
        content = ""
        for sel in ["section p", ".article-content p", ".art_con p", "#Content p", ".text p"]:
            paragraphs = tree.cssselect(sel)
            if paragraphs:
                content = "\n".join(
                    p.text_content().strip() for p in paragraphs if p.text_content().strip()
                )
                if len(content) > 100:
                    break

        # 作者
        author = ""
        search_text = content if content else tree.text_content()
        m = re.search(r"新华社记者\s*([^。\n]{1,30})", search_text)
        if m:
            author = ("新华社记者 " + m.group(1).strip()).strip()

        return {
            "title":       title,
            "source":      source,
            "author":      author,
            "pub_time":    pub_time,
            "content":     content,
            "url":         url,
            "fingerprint": url_fingerprint(url),
            "crawled_at":  datetime.now().isoformat(),
        }
    except (requests.RequestException, Exception) as e:
        logger.warning("抓取失败 {}: {}", url, e)
        return None


# ===== 过滤器 =====

def is_xinhua_article(article: dict) -> bool:
    """来源含新华社 且 作者含新华社记者"""
    source = article.get("source", "")
    author = article.get("author", "")
    content = article.get("content", "")
    return ("新华社" in source) and ("新华社记者" in author or "新华社记者" in content[:300])


def is_recent(article: dict, days: int) -> bool:
    if days <= 0:
        return True
    pub = article.get("pub_time", "")
    if not pub:
        return True
    try:
        pub_dt = datetime.strptime(pub[:10], "%Y-%m-%d")
        return pub_dt >= datetime.now() - timedelta(days=days)
    except ValueError:
        return True


# ===== 主流程 =====


def save_to_mongodb(results: list[dict], collection: str = "output/xinhua/") -> None:
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
            col.insert_many(docs)
        else:
            col.insert_many(results)
        logger.info("MongoDB: {} results saved to crawlab_test.{}", len(results), collection)
    except Exception as e:
        logger.warning("MongoDB save failed (file output unaffected): {}", e)

def run(
    keyword: str = "新华社记者",
    max_pages: int = 3,
    days_back: int = 1,
    headless: bool = True,
    output_dir: Optional[Path] = None,
) -> list[dict]:
    """运行中证网新华社记者文章爬虫。

    Args:
        keyword: 搜索关键词
        max_pages: 最大翻页数
        days_back: 抓取几天内的文章（0 为不限）
        headless: Playwright 无头模式
        output_dir: 输出目录，默认使用 settings.output_dir / "xinhua"

    Returns:
        抓取结果列表
    """
    logger.info("=" * 50)
    logger.info("中证网新华社记者文章爬虫启动")
    logger.info("关键词: {} | 翻页: {} | 天数: {}", keyword, max_pages, days_back)

    logger.info("--- 阶段 1: Playwright 搜索 ---")
    raw = discover_article_urls(keyword, max_pages, headless)

    if not raw:
        logger.warning("未搜索到任何文章")
        return []

    seen = set()
    unique = [a for a in raw if not (url_fingerprint(a["url"]) in seen or seen.add(url_fingerprint(a["url"])))]
    logger.info("去重后 {} 条", len(unique))

    logger.info("--- 阶段 2: 抓取详情页 ---")
    session = make_session()
    results = []

    for i, a in enumerate(unique):
        logger.info("[{}/{}] {}", i + 1, len(unique), a["title"][:60])
        detail = fetch_detail(session, a["url"])
        if detail and is_xinhua_article(detail) and is_recent(detail, days_back):
            results.append(detail)
            logger.info("  + 命中: {}", detail["author"])
        elif detail:
            logger.info("  - 来源={} 作者={}", detail.get("source"), detail.get("author"))

    # 输出
    out_dir = output_dir or (settings.output_dir / "xinhua")
    os.makedirs(out_dir, exist_ok=True)

    # 文本文件
    out_path = out_dir / f"xinhua_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(out_path, "w", encoding="utf-8") as f:
        for i, art in enumerate(results, 1):
            f.write(f"{'='*60}\n")
            f.write(f"【{i}】{art.get('title', '')}\n")
            f.write(f"来源: {art.get('source', '')}\n")
            f.write(f"作者: {art.get('author', '')}\n")
            f.write(f"时间: {art.get('pub_time', '')}\n")
            f.write(f"链接: {art.get('url', '')}\n")
            f.write(f"抓取: {art.get('crawled_at', '')}\n")
            f.write(f"{'-'*60}\n")
            f.write(f"{art.get('content', '')}\n\n")

        # JSON 结果文件（Crawlab 结果收集用）
    json_path = out_dir / f"xinhua_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)

    # JSON Lines 结果文件（Crawlab 逐行收集用）
    jl_path = out_dir / f"xinhua_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jl"
    with open(jl_path, "w", encoding="utf-8") as f:
        for art in results:
            f.write(json.dumps(art, ensure_ascii=False, default=str) + "\n")

    logger.info("=" * 50)
    logger.info("完成: {} 条 -> {}", len(results), out_path)
    logger.info("JSON: {} | JL: {}", json_path, jl_path)
    save_to_mongodb(results)
    return results


if __name__ == "__main__":
    run(
        keyword=settings.cs_search_kw,
        max_pages=settings.cs_max_pages,
        days_back=settings.cs_days_back,
        headless=settings.cs_headless,
    )
