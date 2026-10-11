from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class PlanLimits(BaseModel):
    """Usage limits for a subscription plan."""
    backups_per_month: int
    storage_gb: int
    cloud_providers: list[str]  # List of provider names allowed
    max_backup_size_gb: int
    concurrent_uploads: int


class SubscriptionPlan(BaseModel):
    """Subscription plan definition."""
    id: str  # free, pro, business
    name: str
    price_monthly_cents: int  # Price in cents; 0 for free
    price_yearly_cents: int
    limits: PlanLimits
    features: list[str]  # e.g., ["priority_support", "team_sharing", "advanced_restore"]


class SubscriptionStatus(BaseModel):
    """Active subscription for a user."""
    id: str = Field(default_factory=lambda: str(ObjectId()))
    user_id: str
    plan_id: str  # References SubscriptionPlan.id
    status: str  # active, canceled, past_due, trial
    current_period_start: datetime
    current_period_end: datetime
    stripe_subscription_id: Optional[str] = None  # Stripe subscription ID
    stripe_customer_id: Optional[str] = None  # Stripe customer ID
    cancel_at_period_end: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class UsageRecord(BaseModel):
    """Track usage against plan limits in the current billing period."""
    id: str = Field(default_factory=lambda: str(ObjectId()))
    user_id: str
    subscription_id: str
    billing_period_start: datetime
    billing_period_end: datetime
    backups_used: int = 0
    storage_used_gb: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Invoice(BaseModel):
    """Billing invoice for a subscription."""
    id: str = Field(default_factory=lambda: str(ObjectId()))
    user_id: str
    subscription_id: str
    stripe_invoice_id: Optional[str] = None
    amount_cents: int
    status: str  # draft, open, paid, void, uncollectible
    period_start: datetime
    period_end: datetime
    due_date: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


from bson import ObjectId

# Populate ObjectId references
SubscriptionStatus.update_forward_refs()
UsageRecord.update_forward_refs()
Invoice.update_forward_refs()
