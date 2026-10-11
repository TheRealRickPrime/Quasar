from fastapi import APIRouter, Depends, HTTPException, status

router = APIRouter(prefix="/backups", tags=["backups"])


@router.get("/sessions")
async def list_backups():
    return {"items": []}


@router.post("/sessions")
async def create_backup_session():
    return {"message": "Backup session created scaffold"}


@router.get("/sessions/{session_id}")
async def get_backup_session(session_id: str):
    return {"session_id": session_id, "status": "queued"}
