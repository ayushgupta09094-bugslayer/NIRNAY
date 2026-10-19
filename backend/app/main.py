from dotenv import load_dotenv

# Load backend/.env before importing modules that read environment settings.
load_dotenv()

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.tenders import router as tender_router
from app.api.auth import router as auth_router
from app.api.records import router as records_router
from app.api.documents import router as documents_router
from app.api.notifications import router as notifications_router
from app.core.database import init_db

app = FastAPI(
    title="NIRNAY",
    description="Procurement Compliance & Verification System",
    version="0.3.0",
)
origins = [
    origin.strip()
    for origin in os.getenv(
        "FRONTEND_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(tender_router)
app.include_router(auth_router)
app.include_router(records_router)
app.include_router(documents_router)
app.include_router(notifications_router)


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/healthz", tags=["Health"])
def health():
    return {"project": "NIRNAY", "status": "ok"}


@app.get("/", tags=["Health"])
def root():
    return {"project": "NIRNAY", "status": "Backend is running"}
