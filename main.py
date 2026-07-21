"""
cjscript - Crawlab 主入口

用法:
  python main.py <爬虫名>

示例:
  python main.py xinhua
"""

import sys
import runpy


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else ""
    if not name:
        print("用法: python main.py <爬虫名>")
        print("可用爬虫: xinhua")
        sys.exit(1)

    if name == "xinhua":
        runpy.run_module("cjscript.spiders.xinhua", run_name="__main__")
    else:
        print(f"未知爬虫: {name}")
        sys.exit(1)
