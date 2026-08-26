from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from services.enforcement_models import StructuredCase  # noqa: E402
from services.enforcement_service import analyze_enforcement_case  # noqa: E402

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


class NoPrecedents:
    @staticmethod
    def search_precedents(query, limit=3):
        return {"status": "no_results", "items": []}


@app.get("/")
@app.get("/api/enforcement/analyze")
async def health() -> dict:
    return {"service": "visable-enforcement-analyze", "status": "ok", "mode": "deterministic-fallback"}


@app.post("/")
@app.post("/api/enforcement/analyze")
async def analyze(request: Request) -> dict:
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="invalid JSON body") from exc

    try:
        case = StructuredCase.model_validate(payload.get("caseData") or {})
    except Exception as exc:
        raise HTTPException(status_code=422, detail="invalid structured enforcement case") from exc

    analysis = await analyze_enforcement_case(
        case,
        prediction_provider=None,
        precedent_adapter=NoPrecedents,
    )
    return analysis.public_dict()
