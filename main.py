"""
cjscript - Crawlab main entry

Usage:
  python main.py xinhua
"""

import sys
from pathlib import Path

# Add src/ to Python path so cjscript package can be imported.
# When running under Crawlab, main.py is copied to a task subdirectory,
# so we also check the parent directory (the spider workspace root).
_here = Path(__file__).resolve().parent
_src = _here / "src"
if not _src.is_dir():
    _src = _here.parent / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else ""
    if not name:
        print("Usage: python main.py <spider>")
        print("Available: xinhua")
        sys.exit(1)

    if name == "xinhua":
        from cjscript.spiders.xinhua import run
        from cjscript.config.settings import settings
        run(
            keyword=settings.cs_search_kw,
            max_pages=settings.cs_max_pages,
            days_back=settings.cs_days_back,
            headless=settings.cs_headless,
        )
    else:
        print(f"Unknown spider: {name}")
        sys.exit(1)


if __name__ == "__main__":
    main()
