from firebase_admin import messaging

from app.core.database import SessionLocal
from app.core.firebase import get_firebase_app
from app.models import PushInstallation


def send_user_notification(
    uid: str,
    title: str,
    body: str,
    data: dict[str, str] | None = None,
) -> int:
    """Send a notification to the Firebase installation IDs registered for a user."""
    db = SessionLocal()
    sent = 0
    try:
        installations = (
            db.query(PushInstallation)
            .filter(PushInstallation.owner_uid == uid)
            .all()
        )
        for installation in installations:
            fid = installation.fid
            if not fid:
                continue
            try:
                message = messaging.Message(
                    fid=fid,
                    notification=messaging.Notification(title=title, body=body),
                    data=data or {},
                )
                messaging.send(message, app=get_firebase_app())
                sent += 1
            except Exception:
                # Continue sending to other registered installations if one fails.
                continue
        return sent
    finally:
        db.close()
