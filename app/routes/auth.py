from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.auth import create_token
from app.config.settings import Settings

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
async def login(body: LoginRequest):
    settings = Settings()
    if body.username != settings.AUTH_USERNAME or body.password != settings.AUTH_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token(settings)
    return {"token": token, "expires_in": settings.JWT_EXPIRY_HOURS * 3600}
