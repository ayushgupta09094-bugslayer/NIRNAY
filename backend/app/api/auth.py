from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.core.firestore_db import collection, document_data, iso
from app.core.security import require_user

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.get("/me")
def get_current_user(user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    uid = user.get("uid")
    if not uid:
        raise HTTPException(status_code=401, detail="Authenticated user has no UID.")

    profile_ref = collection("users").document(uid)
    now = datetime.now(timezone.utc)
    existing = document_data(profile_ref.get())
    role = user.get("role")
    profile = {
        "uid": uid,
        "email": user.get("email"),
        "display_name": user.get("name") or user.get("display_name"),
        "photo_url": user.get("picture"),
        "email_verified": bool(user.get("email_verified", False)),
        "last_login_at": now,
        "updated_at": now,
    }
    if existing is None:
        profile["created_at"] = now
        profile["role"] = role
    elif role is not None:
        profile["role"] = str(role)

    profile_ref.set(profile, merge=True)
    saved = document_data(profile_ref.get()) or profile
    return {
        "uid": uid,
        "email": saved.get("email"),
        "display_name": saved.get("display_name"),
        "email_verified": bool(saved.get("email_verified", False)),
        "role": saved.get("role"),
        "created_at": iso(saved.get("created_at")),
        "last_login_at": iso(saved.get("last_login_at")),
    }
