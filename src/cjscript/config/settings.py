"""全局配置."""

from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """应用配置."""

    # 请求相关
    request_timeout: int = 30
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    )

    # 输出
    output_dir: Path = PROJECT_ROOT / "output"
    log_dir: Path = PROJECT_ROOT / "logs"

    # 重试
    max_retries: int = 3
    retry_delay: float = 1.0

    # 中证网爬虫配置 (cs.com.cn)
    cs_base_url: str = "https://www.cs.com.cn"
    cs_search_kw: str = "新华社记者"
    cs_max_pages: int = 3
    cs_days_back: int = 1
    cs_headless: bool = True

    # Playwright
    pw_delay_min: float = 1.0
    pw_delay_max: float = 3.0

    model_config = {"env_prefix": "CJ_", "env_file": ".env"}


settings = Settings()
