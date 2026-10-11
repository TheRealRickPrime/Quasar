from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

router = APIRouter(prefix="/auth", tags=["auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


@router.post("/register")
async def register_user():
    return {"message": "Register endpoint scaffold"}


@router.post("/token")
async def login_for_access_token():
    return {"message": "Token endpoint scaffold"}


@router.get("/me")
async def read_current_user(token: str = Depends(oauth2_scheme)):
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return {"message": "Authenticated user scaffold", "token": token}
