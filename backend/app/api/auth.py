from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_user
from app.models import UserProfile

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.get("/me")
def get_current_user(
    user: dict[str, Any] = Depends(require_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    uid = user.get("uid")
    if not uid:
        raise HTTPException(status_code=401, detail="Authenticated user has no UID.")

    profile = db.get(UserProfile, uid)
    now = datetime.now(timezone.utc)
    email = user.get("email")
    display_name = user.get("name") or user.get("display_name")
    photo_url = user.get("picture")
    role = user.get("role")

    if profile is None:
        profile = UserProfile(
            uid=uid,
            email=email,
            display_name=display_name,
            photo_url=photo_url,
            email_verified=bool(user.get("email_verified", False)),
            role=role,
            last_login_at=now,
        )
        db.add(profile)
    else:
        profile.email = email
        profile.display_name = display_name
        profile.photo_url = photo_url
        profile.email_verified = bool(user.get("email_verified", False))
        if role is not None:
            profile.role = str(role)
        profile.last_login_at = now

    db.commit()
    db.refresh(profile)
    return {
        "uid": profile.uid,
        "email": profile.email,
        "display_name": profile.display_name,
        "email_verified": profile.email_verified,
        "role": profile.role,
    }
