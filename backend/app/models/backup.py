from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class BackupSessionCreateRequest(BaseModel):
    """Request to create a new backup session."""
    provider: str
    device_name: Optional[str] = None
    encrypted_file_path: Optional[str] = None
    backup_status: str = "queued"


class BackupSessionResponse(BaseModel):
    """Response model for backup session details."""
    id: str
    user_id: str
    provider: str
    device_name: Optional[str] = None
    encrypted_file_path: Optional[str] = None
    backup_status: str = "queued"
    upload_progress: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class BackupProfileLink(BaseModel):
    """User profile link for backup status and access."""
    id: str
    user_id: str
    profile_slug: str
    link_url: str
    is_public: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_accessed_at: Optional[datetime] = None
