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
    """Backup session details."""
    id: str
    user_id: str
    provider: str
    device_name: Optional[str] = None
    encrypted_file_path: Optional[str] = None
    backup_status: str
    upload_progress: float = 0.0
    created_at: datetime
    updated_at: datetime


class BackupProfileLink(BaseModel):
    """Public profile link for sharing backup metadata."""
    id: str
    user_id: str
    profile_slug: str
    link_url: str
    is_public: bool
    created_at: datetime
    last_accessed_at: Optional[datetime] = None
