import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field

from app.core.firestore_db import collection, document_data, iso, owned_documents
from app.core.security import require_user

router = APIRouter(prefix="/api/v1/records", tags=["User Records"])
RecordKind = Literal["saved_tender", "verification_note", "other"]


class RecordCreate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    kind: RecordKind = "other"
    data: dict[str, Any] = Field(default_factory=dict)


class RecordUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    kind: RecordKind | None = None
    data: dict[str, Any] | None = None


def serialize(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": record["id"],
        "title": record.get("title", ""),
        "kind": record.get("kind", "other"),
        "data": record.get("data") or {},
        "created_at": iso(record.get("created_at")),
        "updated_at": iso(record.get("updated_at")),
    }


@router.get("")
def list_records(user: dict[str, Any] = Depends(require_user)) -> list[dict[str, Any]]:
    return [serialize(item) for item in owned_documents("user_records", user["uid"])]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_record(body: RecordCreate, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    title = body.title.strip()
    if not title:
        raise HTTPException(status_code=422, detail="Record title cannot be blank.")
    record_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc)
    record = {
        "owner_uid": user["uid"],
        "title": title,
        "kind": body.kind,
        "data": body.data,
        "created_at": now,
        "updated_at": now,
    }
    collection("user_records").document(record_id).set(record)
    return serialize({"id": record_id, **record})


@router.patch("/{record_id}")
def update_record(
    record_id: str,
    body: RecordUpdate,
    user: dict[str, Any] = Depends(require_user),
) -> dict[str, Any]:
    ref = collection("user_records").document(record_id)
    record = document_data(ref.get())
    if record is None or record.get("owner_uid") != user["uid"]:
        raise HTTPException(status_code=404, detail="Record not found.")

    updates = body.model_dump(exclude_unset=True, exclude_none=True)
    if "title" in updates:
        updates["title"] = updates["title"].strip()
        if not updates["title"]:
            raise HTTPException(status_code=422, detail="Record title cannot be blank.")
    if updates:
        updates["updated_at"] = datetime.now(timezone.utc)
        ref.update(updates)
        record.update(updates)
    return serialize(record)


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_record(record_id: str, user: dict[str, Any] = Depends(require_user)) -> Response:
    ref = collection("user_records").document(record_id)
    record = document_data(ref.get())
    if record is None or record.get("owner_uid") != user["uid"]:
        raise HTTPException(status_code=404, detail="Record not found.")
    ref.delete()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
