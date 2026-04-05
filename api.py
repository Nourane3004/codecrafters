import sys
import os

# Add project root and Agents/ to path so all imports resolve
_ROOT = os.path.dirname(os.path.abspath(__file__))
_AGENTS = os.path.join(_ROOT, "Agents")
for _p in (_ROOT, _AGENTS):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
from typing import Optional
from Agents.orchestrator import analyse_content

app = FastAPI(title="MENACRAFT Pipeline API")


@app.post("/analyse")
async def analyse(
    input_type: str = Form(...),       # "document" | "image" | "url" | "video"
    source_ref: str = Form("upload"),
    url: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
):
    file_bytes = await file.read() if file else None
    result = await analyse_content(
        source_ref=source_ref,
        input_type=input_type,
        file_bytes=file_bytes,
        url=url,
    )
    return JSONResponse({
        "action":                result.action,
        "label":                 result.label,
        "risk_score":            result.risk_score,
        "risk_band":             result.risk_band,
        "confidence":            result.confidence,
        "explanation":           result.explanation,
        "requires_human_review": result.requires_human_review,
        "audit_trail":           result.audit_trail,
    })


@app.get("/health")
def health():
    return {"status": "ok"}