from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class UserInDB(BaseModel):
    """MongoDB user document model."""
    id: str = Field(alias="_id")
    email: EmailStr
    full_name: Optional[str] = None
    hashed_password: str
    is_active: bool = True
    subscription_plan_id: str = "free"  # Current plan: free, pro, business
    subscription_status: str = "active"  # active, canceled, past_due, trial
    subscription_id: Optional[str] = None  # Reference to SubscriptionStatus doc
    stripe_customer_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True


class UserCreateRequest(BaseModel):
    """Request to create a new user account."""
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class UserResponse(BaseModel):
    """Public user profile response."""
    id: str
    email: str
    full_name: Optional[str] = None
    subscription_plan_id: str
    subscription_status: str
    created_at: datetime


class TokenResponse(BaseModel):
    """Response containing access token and user info."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
