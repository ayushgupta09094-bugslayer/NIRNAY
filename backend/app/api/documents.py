import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from firebase_admin import storage

from app.core.firebase import get_firebase_app
from app.core.firestore_db import collection, document_data, iso, owned_documents
from app.core.security import require_user

router = APIRouter(prefix="/api/v1/documents", tags=["Documents"])
MAX_BYTES = 15 * 1024 * 1024
ALLOWED = {".pdf", ".png", ".jpg", ".jpeg", ".docx", ".xlsx", ".txt"}


def clean_filename(value: str | None) -> str:
    name = (value or "upload").replace(chr(92), "/").split("/")[-1]
    name = re.sub(r"[\r\n\x00]", "", name).strip()
    return (name or "upload")[:180]


def serialize(document: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": document["id"],
        "filename": document["filename"],
        "content_type": document["content_type"],
        "size_bytes": document["size_bytes"],
        "created_at": iso(document.get("created_at")),
    }


def get_bucket():
    try:
        return storage.bucket(
            name=os.getenv("FIREBASE_STORAGE_BUCKET") or None,
            app=get_firebase_app(),
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Firebase Storage is not configured. It may require enabling billing.") from exc


@router.get("")
def list_documents(user: dict[str, Any] = Depends(require_user)) -> list[dict[str, Any]]:
    return [serialize(item) for item in owned_documents("user_documents", user["uid"])]


@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    user: dict[str, Any] = Depends(require_user),
) -> dict[str, Any]:
    filename = clean_filename(file.filename)
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED:
        raise HTTPException(status_code=415, detail="Allowed file types: PDF, PNG/JPG, DOCX, XLSX, TXT.")

    content = await file.read(MAX_BYTES + 1)
    await file.close()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(content) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="Maximum upload size is 15 MiB.")

    mime = (file.content_type or "application/octet-stream").split(";", 1)[0]
    if mime == "application/octet-stream":
        mime = {
            ".pdf": "application/pdf",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".txt": "text/plain",
        }.get(ext, mime)

    uid = user["uid"]
    document_id = uuid.uuid4().hex
    object_path = f"users/{uid}/documents/{document_id}/{filename}"
    bucket = get_bucket()
    blob = bucket.blob(object_path)
    blob.metadata = {"ownerUid": uid, "documentId": document_id}
    blob.cache_control = "private, max-age=0, no-transform"

    try:
        blob.upload_from_string(content, content_type=mime)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="File could not be stored in Firebase Storage. Confirm Storage is enabled and billing requirements are satisfied.") from exc

    now = datetime.now(timezone.utc)
    metadata = {
        "owner_uid": uid,
        "filename": filename,
        "content_type": mime,
        "size_bytes": len(content),
        "object_path": object_path,
        "created_at": now,
    }
    try:
        collection("user_documents").document(document_id).set(metadata)
    except Exception as exc:
        try:
            blob.delete()
        except Exception:
            pass
        raise HTTPException(status_code=503, detail="File uploaded but its metadata could not be saved to Firestore.") from exc

    return serialize({"id": document_id, **metadata})


@router.get("/{document_id}/download")
def download_document(document_id: str, user: dict[str, Any] = Depends(require_user)) -> Response:
    document = document_data(collection("user_documents").document(document_id).get())
    if document is None or document.get("owner_uid") != user["uid"]:
        raise HTTPException(status_code=404, detail="Document not found.")

    expected_prefix = f"users/{user['uid']}/documents/"
    if not document.get("object_path", "").startswith(expected_prefix):
        raise HTTPException(status_code=403, detail="Document access denied.")

    try:
        data = get_bucket().blob(document["object_path"]).download_as_bytes()
    except Exception as exc:
        raise HTTPException(status_code=502, detail="File could not be retrieved from Storage.") from exc

    filename = clean_filename(document["filename"])
    ascii_name = filename.encode("ascii", errors="ignore").decode("ascii").replace('"', "") or "download"
    return Response(
        content=data,
        media_type=document["content_type"],
        headers={
            "Content-Disposition": f'attachment; filename="{ascii_name}"',
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: str, user: dict[str, Any] = Depends(require_user)) -> Response:
    ref = collection("user_documents").document(document_id)
    document = document_data(ref.get())
    if document is None or document.get("owner_uid") != user["uid"]:
        raise HTTPException(status_code=404, detail="Document not found.")

    expected_prefix = f"users/{user['uid']}/documents/"
    if not document.get("object_path", "").startswith(expected_prefix):
        raise HTTPException(status_code=403, detail="Document access denied.")

    try:
        get_bucket().blob(document["object_path"]).delete()
    except Exception as exc:
        raise HTTPException(status_code=502, detail="File could not be deleted from Storage.") from exc

    ref.delete()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
