from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    asr_provider: Literal["aliyun", "volcengine"] = "aliyun"

    # 阿里云 DashScope
    aliyun_dashscope_api_key: str = ""

    # 火山引擎豆包 ASR
    volcengine_app_id: str = ""
    volcengine_access_token: str = ""
    volcengine_resource_id: str = "volc.bigasr.auc_turbo"

    # DeepSeek
    deepseek_api_key: str = ""

    # 临时文件目录
    temp_dir: Path = Path("temp")


settings = Settings()
