from app.asr.base import ASRProvider
from app.asr.aliyun import AliyunASR
from app.asr.volcengine import VolcengineASR

# 模块级单例，由 lifespan 初始化，避免每次请求重新加载模型
asr_provider: ASRProvider | None = None


def get_asr_provider(config) -> ASRProvider:
    if config.asr_provider == "aliyun":
        return AliyunASR(config.aliyun_dashscope_api_key)
    if config.asr_provider == "local_sensevoice":
        from app.asr.local_sensevoice import LocalSenseVoiceASR
        return LocalSenseVoiceASR(
            device=config.local_asr_device,
            language=config.local_asr_language,
        )
    return VolcengineASR(
        config.volcengine_app_id,
        config.volcengine_access_token,
        config.volcengine_resource_id,
    )
