from pydantic import BaseModel, ConfigDict


class Settings(BaseModel):
    # App config
    app_name: str = "Quasar"
    app_version: str = "0.1.0"
    api_prefix: str = "/api/v1"
    
    # Database config
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db: str = "quasar"
    
    # Authentication config
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24
    
    # Stripe config
    stripe_api_key: str = "sk_test_placeholder"
    stripe_webhook_secret: str = "whsec_test_placeholder"
    stripe_publishable_key: str = "pk_test_placeholder"
    
    # Subscription config
    free_trial_days: int = 14
    trial_plan_id: str = "free"
    default_plan_id: str = "free"

    model_config = ConfigDict(extra="ignore")


settings = Settings()
