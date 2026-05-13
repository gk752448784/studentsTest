from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ESSAY_", env_file=".env", extra="ignore")

    ocr_provider: str = Field(default="mock")
    grader_provider: str = Field(default="deterministic")
    llm_base_url: str = Field(default="")
    llm_api_key: str = Field(default="")
    llm_model: str = Field(default="gpt-4o-mini")
    xfyun_app_id: str = Field(default="")
    xfyun_api_key: str = Field(default="")
    xfyun_api_secret: str = Field(default="")
    xfyun_endpoint: str = Field(
        default="https://cbm01.cn-huabei-1.xf-yun.com/v1/private/se75ocrbm"
    )


async def get_settings() -> Settings:
    return Settings()
