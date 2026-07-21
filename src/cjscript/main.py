"""cjscript main entry - CLI dispatcher."""

import sys

from loguru import logger

from cjscript.config.settings import settings
from cjscript.spiders.xinhua import run as run_xinhua
from cjscript.spiders.sina import run as run_sina

SPIDERS = {
    "xinhua": run_xinhua,
    "sina": run_sina,
}


def main():
    args = sys.argv[1:]
    if not args:
        logger.info("Available spiders: {}", ", ".join(SPIDERS))
        logger.info("Usage: python -m cjscript.main <spider>")
        return 0

    name = args[0]
    if name not in SPIDERS:
        logger.error("Unknown spider: {} | available: {}", name, ", ".join(SPIDERS))
        return 1

    logger.info("cjscript - starting spider: {}", name)
    runner = SPIDERS[name]
    if name == "xinhua":
        results = runner(
            keyword=settings.cs_search_kw,
            max_pages=settings.cs_max_pages,
            days_back=settings.cs_days_back,
            headless=settings.cs_headless,
        )
    else:
        results = runner(max_articles=10)

    logger.info("cjscript - spider {} finished: {} results", name, len(results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
