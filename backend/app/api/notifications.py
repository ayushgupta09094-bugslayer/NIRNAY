import hashlib
import os
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.firestore_db import collection, document_data
from app.core.security import require_user
from app.services.notifications import send_user_notification

router = APIRouter(prefix="/api/v1/notifications", tags=["Notifications"])


class FIDRegistration(BaseModel):
    fid: str = Field(min_length=10, max_length=256)


def installation_key(uid: str, fid: str) -> str:
    return hashlib.sha256(f"{uid}:{fid}".encode()).hexdigest()


@router.post("/register")
def register_fid(body: FIDRegistration, user: dict[str, Any] = Depends(require_user)) -> dict[str, bool]:
    uid = user["uid"]
    key = installation_key(uid, body.fid)
    ref = collection("push_installations").document(key)
    existing = document_data(ref.get())
    now = datetime.now(timezone.utc)
    ref.set({
        "owner_uid": uid,
        "fid": body.fid,
        "updated_at": now,
        "created_at": existing.get("created_at", now) if existing else now,
    }, merge=True)
    return {"ok": True}


@router.delete("/register")
def unregister_fid(body: FIDRegistration, user: dict[str, Any] = Depends(require_user)) -> dict[str, bool]:
    key = installation_key(user["uid"], body.fid)
    ref = collection("push_installations").document(key)
    installation = document_data(ref.get())
    if installation is not None and installation.get("owner_uid") == user["uid"]:
        ref.delete()
    return {"ok": True}


@router.post("/test")
def test_notification(user: dict[str, Any] = Depends(require_user)):
    if os.getenv("ENABLE_TEST_NOTIFICATIONS", "false").lower() != "true":
        raise HTTPException(status_code=404, detail="Test notifications are disabled.")
    sent = send_user_notification(
        user["uid"],
        "NIRNAY notification test",
        "Your browser is connected to Firebase Cloud Messaging.",
        {"url": "/app", "type": "test"},
    )
    return {"ok": True, "sent": sent}
