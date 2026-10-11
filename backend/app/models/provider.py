from pydantic import BaseModel


class Provider(BaseModel):
    """Cloud provider definition."""
    id: str  # s3, google_drive, onedrive, icloud, dropbox
    name: str
    description: str
    icon_url: Optional[str] = None


class ProviderListResponse(BaseModel):
    """List of available cloud providers."""
    providers: list[Provider]


from typing import Optional
