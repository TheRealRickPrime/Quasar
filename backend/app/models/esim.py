from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class ESimProvider(BaseModel):
    id: str
    name: str
    display_name: str
    description: str = ""
    api_base_url: Optional[str] = None
    supports_webhook: bool = True
    is_active: bool = True
    coverage_countries: list[str] = Field(default_factory=list)


class ESimPlan(BaseModel):
    id: str
    provider: str
    provider_name: str
    country_code: str
    destination: str
    name: str
    data_gb: int
    validity_days: int
    price_cents: int
    currency: str = "USD"
    instant_activation: bool = True
    description: str = ""
    compatible_with: list[str] = Field(default_factory=lambda: ["iPhone", "Android", "Pixel"])


class ESimOrder(BaseModel):
    id: str = Field(default_factory=lambda: f"esim_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}")
    user_id: str
    provider: str
    plan_id: str
    destination: str
    status: Literal["pending", "queued", "activated", "failed", "expired"] = "pending"
    qr_code_data: Optional[str] = None
    activation_code: Optional[str] = None
    price_cents: int
    paid_cents: int
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None


class ESimUsage(BaseModel):
    order_id: str
    provider: str
    country_code: str
    data_used_mb: int = 0
    data_total_mb: int = 0
    usage_percent: float = 0.0
    status: str = "active"
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class ESimOrderRequest(BaseModel):
    provider: str
    plan_id: str
    destination: str
    country_code: Optional[str] = None


class ESimWebhookEvent(BaseModel):
    event_type: str
    order_id: str
    provider: str
    status: Optional[str] = None
    usage_percent: Optional[float] = None
