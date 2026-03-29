from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    asr_provider: Literal["aliyun", "volcengine", "local_sensevoice"] = "aliyun"

    # 阿里云 DashScope
    aliyun_dashscope_api_key: str = ""

    # 火山引擎豆包 ASR
    volcengine_app_id: str = ""
    volcengine_access_token: str = ""
    volcengine_resource_id: str = "volc.bigasr.auc_turbo"

    # 本地 SenseVoice（离线，无需 API Key）
    local_asr_device: str = "cpu"          # cpu / cuda:0 / mps
    local_asr_language: str = "auto"       # auto / zh / en / ja / ko / yue

    # DeepSeek
    deepseek_api_key: str = ""

    # 临时文件目录
    temp_dir: Path = Path("temp")

    # 内容缓存
    cache_backend: Literal["memory", "upstash"] = "memory"
    cache_ttl_seconds: int = 2_592_000      # 30天；0 = 不设过期（不推荐）
    cache_store_transcript: bool = False    # 是否缓存原文（影响存储大小）

    # Upstash Redis REST（仅 cache_backend=upstash 时必填）
    upstash_redis_rest_url: str = ""
    upstash_redis_rest_token: str = ""


settings = Settings()
