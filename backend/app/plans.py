"""Subscription plan definitions and helpers."""

from datetime import datetime, timedelta
from typing import Optional

from app.models.subscription import PlanLimits, SubscriptionPlan


# Define all available subscription plans
FREE_PLAN = SubscriptionPlan(
    id="free",
    name="Free",
    price_monthly_cents=0,
    price_yearly_cents=0,
    limits=PlanLimits(
        backups_per_month=15,
        storage_gb=5,
        cloud_providers=["s3", "google_drive", "onedrive", "dropbox"],
        max_backup_size_gb=1,
        concurrent_uploads=1,
    ),
    features=[
        "basic_backup",
        "web_dashboard",
        "15_backups_per_month",
        "all_cloud_providers",
    ],
)

PRO_PLAN = SubscriptionPlan(
    id="pro",
    name="Pro",
    price_monthly_cents=999,  # $9.99/month
    price_yearly_cents=9999,  # $99.99/year
    limits=PlanLimits(
        backups_per_month=100,
        storage_gb=100,
        cloud_providers=["s3", "google_drive", "onedrive", "dropbox", "icloud"],
        max_backup_size_gb=10,
        concurrent_uploads=3,
    ),
    features=[
        "unlimited_backups",
        "100gb_storage",
        "priority_support",
        "advanced_restore",
        "backup_scheduling",
        "all_cloud_providers",
    ],
)

BUSINESS_PLAN = SubscriptionPlan(
    id="business",
    name="Business",
    price_monthly_cents=2999,  # $29.99/month
    price_yearly_cents=29999,  # $299.99/year
    limits=PlanLimits(
        backups_per_month=500,
        storage_gb=500,
        cloud_providers=["s3", "google_drive", "onedrive", "dropbox", "icloud"],
        max_backup_size_gb=50,
        concurrent_uploads=10,
    ),
    features=[
        "unlimited_backups",
        "500gb_storage",
        "priority_support",
        "team_sharing",
        "advanced_restore",
        "backup_scheduling",
        "audit_logs",
        "all_cloud_providers",
    ],
)

# Plan registry for lookups
PLANS = {
    "free": FREE_PLAN,
    "pro": PRO_PLAN,
    "business": BUSINESS_PLAN,
}


def get_plan(plan_id: str) -> Optional[SubscriptionPlan]:
    """Retrieve a plan by ID."""
    return PLANS.get(plan_id)


def get_plan_limits(plan_id: str) -> Optional[PlanLimits]:
    """Retrieve usage limits for a plan."""
    plan = get_plan(plan_id)
    return plan.limits if plan else None


def can_create_backup(
    plan_id: str, backups_used: int, storage_used_gb: float, backup_size_gb: float
) -> tuple[bool, Optional[str]]:
    """
    Check if a user can create a backup given their plan and current usage.
    Returns (allowed, reason_if_denied).
    """
    plan = get_plan(plan_id)
    if not plan:
        return False, "Invalid plan"

    limits = plan.limits

    # Check backup count
    if backups_used >= limits.backups_per_month:
        return False, f"Backup limit ({limits.backups_per_month}/month) reached. Upgrade to Pro."

    # Check storage
    if storage_used_gb + backup_size_gb > limits.storage_gb:
        return (
            False,
            f"Storage limit ({limits.storage_gb}GB) would be exceeded. Delete old backups or upgrade.",
        )

    # Check individual backup size
    if backup_size_gb > limits.max_backup_size_gb:
        return (
            False,
            f"Backup size ({backup_size_gb}GB) exceeds plan limit ({limits.max_backup_size_gb}GB).",
        )

    return True, None


def is_provider_allowed(plan_id: str, provider: str) -> bool:
    """Check if a cloud provider is allowed on a given plan."""
    limits = get_plan_limits(plan_id)
    if not limits:
        return False
    return provider in limits.cloud_providers
