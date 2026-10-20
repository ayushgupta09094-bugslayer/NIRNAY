from firebase_admin import messaging

from app.core.firebase import get_firebase_app
from app.core.firestore_db import owned_documents


def send_user_notification(
    uid: str,
    title: str,
    body: str,
    data: dict[str, str] | None = None,
) -> int:
    """Send a notification to the Firebase installations registered for a user."""
    sent = 0
    for installation in owned_documents("push_installations", uid):
        token = installation.get("fid")
        if not token:
            continue
        try:
            message = messaging.Message(
                token=token,
                notification=messaging.Notification(title=title, body=body),
                data=data or {},
            )
            messaging.send(message, app=get_firebase_app())
            sent += 1
        except Exception:
            # Continue sending to other registered installations if one fails.
            continue
    return sent
