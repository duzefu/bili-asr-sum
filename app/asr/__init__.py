from app.asr.base import ASRProvider
from app.asr.aliyun import AliyunASR
from app.asr.volcengine import VolcengineASR


def get_asr_provider(config) -> ASRProvider:
    if config.asr_provider == "aliyun":
        return AliyunASR(config.aliyun_dashscope_api_key)
    return VolcengineASR(
        config.volcengine_app_id,
        config.volcengine_access_token,
        config.volcengine_resource_id,
    )
