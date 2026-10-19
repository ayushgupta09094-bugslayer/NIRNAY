from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_user
from app.models import UserRecord

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


def serialize(record: UserRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "title": record.title,
        "kind": record.kind,
        "data": record.data or {},
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "updated_at": record.updated_at.isoformat() if record.updated_at else None,
    }


@router.get("")
def list_records(
    user: dict[str, Any] = Depends(require_user),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    records = (
        db.query(UserRecord)
        .filter(UserRecord.owner_uid == user["uid"])
        .order_by(UserRecord.created_at.desc())
        .all()
    )
    return [serialize(record) for record in records]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_record(
    body: RecordCreate,
    user: dict[str, Any] = Depends(require_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    title = body.title.strip()
    if not title:
        raise HTTPException(status_code=422, detail="Record title cannot be blank.")
    record = UserRecord(
        owner_uid=user["uid"],
        title=title,
        kind=body.kind,
        data=body.data,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return serialize(record)


@router.patch("/{record_id}")
def update_record(
    record_id: str,
    body: RecordUpdate,
    user: dict[str, Any] = Depends(require_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    record = (
        db.query(UserRecord)
        .filter(UserRecord.id == record_id, UserRecord.owner_uid == user["uid"])
        .first()
    )
    if record is None:
        raise HTTPException(status_code=404, detail="Record not found.")

    updates = body.model_dump(exclude_unset=True, exclude_none=True)
    if "title" in updates:
        updates["title"] = updates["title"].strip()
        if not updates["title"]:
            raise HTTPException(status_code=422, detail="Record title cannot be blank.")
    for key, value in updates.items():
        setattr(record, key, value)

    if updates:
        db.commit()
        db.refresh(record)
    return serialize(record)


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_record(
    record_id: str,
    user: dict[str, Any] = Depends(require_user),
    db: Session = Depends(get_db),
) -> Response:
    record = (
        db.query(UserRecord)
        .filter(UserRecord.id == record_id, UserRecord.owner_uid == user["uid"])
        .first()
    )
    if record is None:
        raise HTTPException(status_code=404, detail="Record not found.")
    db.delete(record)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
