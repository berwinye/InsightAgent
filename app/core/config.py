from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    MYSQL_HOST: str = "mysql"
    MYSQL_PORT: int = 3306
    MYSQL_DATABASE: str = "enterprise_api"
    MYSQL_APP_RW_USER: str = "app_rw"
    MYSQL_APP_RW_PASSWORD: str = ""
    MYSQL_APP_RO_USER: str = "app_ro"
    MYSQL_APP_RO_PASSWORD: str = ""

    QWEN_API_KEY: str = ""
    QWEN_MODEL: str = "qwen-plus"
    QWEN_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    AGENT_MAX_ITERATIONS: int = 8

    @property
    def RW_DATABASE_URL(self) -> str:
        return (
            f"mysql+pymysql://{self.MYSQL_APP_RW_USER}:{self.MYSQL_APP_RW_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
            f"?charset=utf8mb4"
        )

    @property
    def RO_DATABASE_URL(self) -> str:
        return (
            f"mysql+pymysql://{self.MYSQL_APP_RO_USER}:{self.MYSQL_APP_RO_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
            f"?charset=utf8mb4"
        )

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
