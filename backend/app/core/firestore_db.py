from functools import lru_cache

from firebase_admin import firestore

from app.core.firebase import get_firebase_app


@lru_cache(maxsize=1)
def get_firestore():
    """Return the default Cloud Firestore database for this Firebase project."""
    return firestore.client(app=get_firebase_app())


def collection(name: str):
    return get_firestore().collection(name)


def document_data(snapshot) -> dict | None:
    """Return a Firestore document's data plus its ID, or None if missing."""
    if not snapshot.exists:
        return None
    data = snapshot.to_dict() or {}
    data["id"] = snapshot.id
    return data


def iso(value) -> str | None:
    """Serialize Firestore datetime values for the existing REST API contract."""
    return value.isoformat() if value is not None and hasattr(value, "isoformat") else value


def owned_documents(collection_name: str, uid: str) -> list[dict]:
    """Return only documents owned by uid, newest first."""
    items = []
    for snapshot in collection(collection_name).where("owner_uid", "==", uid).stream():
        item = document_data(snapshot)
        if item is not None:
            items.append(item)
    items.sort(key=lambda item: item.get("created_at") or "", reverse=True)
    return items
