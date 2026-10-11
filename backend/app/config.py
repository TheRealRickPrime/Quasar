from pydantic import BaseModel, ConfigDict


class Settings(BaseModel):
    app_name: str = "Quasar"
    app_version: str = "0.1.0"
    api_prefix: str = "/api/v1"
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db: str = "quasar"
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

    model_config = ConfigDict(extra="ignore")


settings = Settings()
