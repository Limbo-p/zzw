# cjscript

财经数据采集与处理脚本集。

## 项目结构

```
cjscript/
├── main.py                  # Crawlab 主入口
├── docker-compose.yml       # 本地 Crawlab 环境
├── pyproject.toml           # 项目配置
├── config/
│   └── settings.py          # 中心配置（env_prefix=CJ_）
├── src/cjscript/
│   ├── main.py              # CLI 调度器
│   └── spiders/
│       ├── xinhua.py        # 中证网新华社记者爬虫
│       └── ...
├── output/xinhua/           # 爬虫输出（.txt / .json / .jl）
└── tests/
```

## 快速开始

```bash
# 创建虚拟环境
python -m venv .venv

# 安装依赖
pip install -r requirements.txt

# Playwright 浏览器
playwright install chromium

# 运行爬虫
python main.py xinhua
# 或
python -m cjscript.spiders.xinhua
```

## Crawlab 部署

### 本地开发环境

```bash
docker compose up -d
# 浏览器打开 http://localhost:8080
```

### 爬虫配置

| 配置项 | 说明 |
|--------|------|
| 运行命令 | `python main.py xinhua` |
| 结果文件 | `output/xinhua/*.jl`（JSON Lines，逐行可解析） |

### 环境变量（可选，CJ_ 前缀）

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `CJ_CS_BASE_URL` | `https://www.cs.com.cn` | 中证网地址 |
| `CJ_CS_SEARCH_KW` | 新华社记者 | 搜索关键词 |
| `CJ_CS_MAX_PAGES` | 3 | 翻页上限 |
| `CJ_CS_DAYS_BACK` | 1 | 只抓最近 N 天 |
| `CJ_CS_HEADLESS` | true | 无头模式 |
| `CJ_REQUEST_TIMEOUT` | 30 | 请求超时（秒） |

在 Crawlab 的任务 → 环境变量面板填入同名变量即可覆盖。

### 结果收集

Crawlab 可配置结果收集路径为 `output/xinhua/` 下的 `.jl` 文件，
每行一个 JSON 对象，支持增量收集。

## 运行测试

```bash
pytest
```
