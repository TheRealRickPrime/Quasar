from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from bson import ObjectId

from app.database import db
from app.models.backup import BackupProfileLink, BackupSessionCreateRequest, BackupSessionResponse
from app.models.provider import ProviderListResponse
from app.security import get_current_user

router = APIRouter(prefix="/backups", tags=["backups"])


@router.get("/providers", response_model=ProviderListResponse)
async def list_providers(current_user: dict = Depends(get_current_user)):
    """List available cloud providers."""
    return ProviderListResponse()


@router.get("/sessions", response_model=list[BackupSessionResponse])
async def list_backups(current_user: dict = Depends(get_current_user)):
    """Get all backup sessions for the current user."""
    sessions = await db.backup_sessions.find({"user_id": current_user["id"]}).to_list(length=100)
    return [
        BackupSessionResponse(
            id=str(item["_id"]),
            user_id=item["user_id"],
            provider=item["provider"],
            device_name=item.get("device_name"),
            encrypted_file_path=item.get("encrypted_file_path"),
            backup_status=item.get("backup_status", "queued"),
            upload_progress=item.get("upload_progress", 0.0),
            created_at=item.get("created_at", datetime.utcnow()),
            updated_at=item.get("updated_at", datetime.utcnow()),
        )
        for item in sessions
    ]


@router.post("/sessions", response_model=BackupSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_backup_session(
    payload: BackupSessionCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    """Create a new backup session."""
    session_document = {
        "user_id": current_user["id"],
        "provider": payload.provider,
        "device_name": payload.device_name or "Unnamed Device",
        "encrypted_file_path": payload.encrypted_file_path,
        "backup_status": "queued",
        "upload_progress": 0.0,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    insert_result = await db.backup_sessions.insert_one(session_document)
    created_session = await db.backup_sessions.find_one({"_id": insert_result.inserted_id})

    return BackupSessionResponse(
        id=str(created_session["_id"]),
        user_id=created_session["user_id"],
        provider=created_session["provider"],
        device_name=created_session.get("device_name"),
        encrypted_file_path=created_session.get("encrypted_file_path"),
        backup_status=created_session.get("backup_status"),
        upload_progress=created_session.get("upload_progress", 0.0),
        created_at=created_session["created_at"],
        updated_at=created_session["updated_at"],
    )


@router.get("/sessions/{session_id}", response_model=BackupSessionResponse)
async def get_backup_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get details of a specific backup session."""
    try:
        session = await db.backup_sessions.find_one({
            "_id": ObjectId(session_id),
            "user_id": current_user["id"],
        })
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session ID",
        )

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backup session not found",
        )

    return BackupSessionResponse(
        id=str(session["_id"]),
        user_id=session["user_id"],
        provider=session["provider"],
        device_name=session.get("device_name"),
        encrypted_file_path=session.get("encrypted_file_path"),
        backup_status=session.get("backup_status"),
        upload_progress=session.get("upload_progress", 0.0),
        created_at=session["created_at"],
        updated_at=session["updated_at"],
    )


@router.post("/profile-link", response_model=BackupProfileLink, status_code=status.HTTP_201_CREATED)
async def create_profile_link(current_user: dict = Depends(get_current_user)):
    """Create a public profile link for backup access."""
    profile_slug = f"{current_user['email'].split('@')[0]}-{current_user['id'][:8]}".lower()
    link_url = f"https://quasar.app/u/{profile_slug}"

    profile_document = {
        "user_id": current_user["id"],
        "profile_slug": profile_slug,
        "link_url": link_url,
        "is_public": False,
        "created_at": datetime.utcnow(),
        "last_accessed_at": None,
    }
    existing = await db.backup_profiles.find_one({"user_id": current_user["id"]})
    if existing:
        return BackupProfileLink(
            id=str(existing["_id"]),
            user_id=existing["user_id"],
            profile_slug=existing["profile_slug"],
            link_url=existing["link_url"],
            is_public=existing.get("is_public", False),
            created_at=existing["created_at"],
            last_accessed_at=existing.get("last_accessed_at"),
        )

    insert_result = await db.backup_profiles.insert_one(profile_document)
    created_profile = await db.backup_profiles.find_one({"_id": insert_result.inserted_id})

    return BackupProfileLink(
        id=str(created_profile["_id"]),
        user_id=created_profile["user_id"],
        profile_slug=created_profile["profile_slug"],
        link_url=created_profile["link_url"],
        is_public=created_profile.get("is_public", False),
        created_at=created_profile["created_at"],
        last_accessed_at=created_profile.get("last_accessed_at"),
    )


@router.get("/profile-link", response_model=BackupProfileLink)
async def get_profile_link(current_user: dict = Depends(get_current_user)):
    """Get the user's profile link."""
    profile = await db.backup_profiles.find_one({"user_id": current_user["id"]})
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile link not found. Create one first.",
        )

    return BackupProfileLink(
        id=str(profile["_id"]),
        user_id=profile["user_id"],
        profile_slug=profile["profile_slug"],
        link_url=profile["link_url"],
        is_public=profile.get("is_public", False),
        created_at=profile["created_at"],
        last_accessed_at=profile.get("last_accessed_at"),
    )
