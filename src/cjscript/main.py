"""cjscript 主入口 - CLI 调度器."""

import sys

from loguru import logger

from cjscript.config.settings import settings
from cjscript.spiders.xinhua import run as run_xinhua

SPIDERS = {
    "xinhua": run_xinhua,
}


def main() -> int:
    """Dispatch to the requested spider."""
    args = sys.argv[1:]

    if not args:
        logger.info("可用爬虫: {}", ", ".join(SPIDERS))
        logger.info("用法: python -m cjscript.main <爬虫名>")
        return 0

    name = args[0]
    if name not in SPIDERS:
        logger.error("未知爬虫: {}，可用: {}", name, ", ".join(SPIDERS))
        return 1

    logger.info("cjscript - 启动爬虫: {}", name)
    runner = SPIDERS[name]
    results = runner(
        keyword=settings.cs_search_kw,
        max_pages=settings.cs_max_pages,
        days_back=settings.cs_days_back,
        headless=settings.cs_headless,
    )
    logger.info("cjscript - 爬虫 {} 完成: {} 条", name, len(results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
