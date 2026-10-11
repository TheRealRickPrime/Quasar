from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CloudProviderConfig(BaseModel):
    """Cloud provider configuration."""
    provider_name: str
    display_name: str
    auth_type: str
    oauth_client_id: Optional[str] = None
    oauth_client_secret: Optional[str] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ProviderConnectionRequest(BaseModel):
    """Request to connect a user to a cloud provider."""
    provider: str
    auth_code: Optional[str] = None
    access_token: Optional[str] = None


class ProviderConnection(BaseModel):
    """User connection to a cloud provider."""
    id: str
    user_id: str
    provider: str
    external_account_id: Optional[str] = None
    is_connected: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ProviderListResponse(BaseModel):
    """List of available cloud providers."""
    providers: list[dict] = Field(default_factory=lambda: [
        {"name": "google_drive", "display_name": "Google Drive", "auth_type": "oauth"},
        {"name": "dropbox", "display_name": "Dropbox", "auth_type": "oauth"},
        {"name": "onedrive", "display_name": "OneDrive", "auth_type": "oauth"},
        {"name": "aws_s3", "display_name": "AWS S3", "auth_type": "credentials"},
    ])
