import pathlib

base = pathlib.Path(r"C:\Users\Eric\Documents\泛财经爬虫ai二创\cjscript\src\cjscript\spiders")
p = base / "xinhua.py"
old = p.read_text(encoding="utf-8")

# 1) Make save_to_mongodb accept collection param
old = old.replace(
    'def save_to_mongodb(results: list[dict]) -> None:',
    'def save_to_mongodb(results: list[dict], collection: str = "output/xinhua/") -> None:'
)
# 2) Update db access
old = old.replace(
    'col = db["output/xinhua/"]',
    'col = db[collection]'
)
# 3) Update log
old = old.replace(
    'logger.info("MongoDB: {} 条结果已写入 crawlab_test.output/xinhua/", len(results))',
    'logger.info("MongoDB: {} 条结果已写入 crawlab_test.{}", len(results), collection)'
)

p.write_text(old, encoding="utf-8")
print("xinhua.py OK")
