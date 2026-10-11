from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class UserCreateRequest(BaseModel):
    email: str
    password: str
    full_name: Optional[str] = None


class UserLoginRequest(BaseModel):
    email: str
    password: str


class UserAuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str


class BackupSessionCreateRequest(BaseModel):
    provider: str
    device_name: Optional[str] = None
    encrypted_file_path: Optional[str] = None
    backup_status: str = "queued"


class BackupSessionResponse(BaseModel):
    id: str
    user_id: str
    provider: str
    device_name: Optional[str] = None
    encrypted_file_path: Optional[str] = None
    backup_status: str = "queued"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
