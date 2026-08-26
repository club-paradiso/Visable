from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from services.enforcement_service import extract_structured_case  # noqa: E402

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


@app.get("/")
@app.get("/api/enforcement/extract")
async def health() -> dict:
    return {"service": "visable-enforcement-extract", "status": "ok", "mode": "deterministic-fallback"}


@app.post("/")
@app.post("/api/enforcement/extract")
async def extract(request: Request) -> dict:
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="invalid JSON body") from exc

    text = str(payload.get("text") or "").strip()
    if not text:
        raise HTTPException(status_code=422, detail="case text is required")

    assessment_date = None
    raw_date = payload.get("assessmentDate")
    if raw_date:
        try:
            assessment_date = date.fromisoformat(str(raw_date))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="invalid assessmentDate") from exc

    case = await extract_structured_case(text, provider=None, assessment_date=assessment_date)
    return {"case": case.public_dict()}
