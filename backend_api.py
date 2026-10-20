"""
FastAPI backend for the semantic resume ranker.

Run with:  uvicorn backend_api:app --reload

Configuration (all optional, via environment variables):
  MODEL_NAME       sentence-transformers model to load   (default: all-MiniLM-L6-v2)
  ALLOWED_ORIGINS  comma-separated CORS origins          (default: *)
  MAX_RESUMES      most resumes accepted per request     (default: 100)
  MAX_TEXT_CHARS   longest text accepted per document    (default: 100000)
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Tuple

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ValidationError
from starlette.responses import JSONResponse
from starlette.datastructures import UploadFile as StarletteUploadFile
from starlette.datastructures import MutableHeaders

from document_processing import DocumentValidationError, extract_resume_text, size_limit_label, validate_filename
from ranker import rank_resumes
from scoring import extract_skills

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger("resume-ranker")

MODEL_NAME = os.getenv("MODEL_NAME", "all-MiniLM-L6-v2")
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",") if o.strip()]
MAX_RESUMES = int(os.getenv("MAX_RESUMES", "100"))
MAX_TEXT_CHARS = int(os.getenv("MAX_TEXT_CHARS", "100000"))
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))
MAX_TOTAL_UPLOAD_BYTES = int(os.getenv("MAX_TOTAL_UPLOAD_BYTES", str(50 * 1024 * 1024)))

if MAX_UPLOAD_BYTES <= 0 or MAX_TOTAL_UPLOAD_BYTES <= 0:
    raise RuntimeError("MAX_UPLOAD_BYTES and MAX_TOTAL_UPLOAD_BYTES must be positive integers.")
MAX_REQUEST_BYTES = MAX_TOTAL_UPLOAD_BYTES + MAX_TEXT_CHARS + 2 * 1024 * 1024


class UploadRequestSizeLimitMiddleware:
    """Bound multipart body size before Starlette spools uploaded parts to temp files."""

    def __init__(self, app, max_body_bytes: int):
        self.app = app
        self.max_body_bytes = max_body_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope.get("path") != "/rank" or scope.get("method") != "POST":
            await self.app(scope, receive, send)
            return

        async def no_store_send(message):
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers["Cache-Control"] = "no-store"
                headers["Pragma"] = "no-cache"
            await send(message)

        headers = dict(scope.get("headers", []))
        content_type = headers.get(b"content-type", b"").split(b";", 1)[0].strip().lower()
        if content_type != b"multipart/form-data":
            await self.app(scope, receive, no_store_send)
            return
        content_length = headers.get(b"content-length")
        if content_length:
            try:
                if int(content_length) > self.max_body_bytes:
                    response = JSONResponse(status_code=413, content={"detail": "The upload batch exceeds the configured request-size limit."})
                    await response(scope, receive, no_store_send)
                    return
            except ValueError:
                response = JSONResponse(status_code=400, content={"detail": "The request has an invalid content length."})
                await response(scope, receive, no_store_send)
                return

        received_bytes = 0

        async def limited_receive():
            nonlocal received_bytes
            message = await receive()
            if message["type"] == "http.request":
                received_bytes += len(message.get("body", b""))
                if received_bytes > self.max_body_bytes:
                    raise HTTPException(status_code=413, detail="The upload batch exceeds the configured request-size limit.")
            return message

        await self.app(scope, limited_receive, no_store_send)


# ----------------------------- request / response ---------------------------- #
class ResumeData(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    text: str = Field(max_length=MAX_TEXT_CHARS)


class RankOptions(BaseModel):
    jd_text: str = Field(max_length=MAX_TEXT_CHARS)
    # 1.0 = rank on meaning only, 0.0 = rank on skill overlap only.
    semantic_weight: float = Field(default=0.6, ge=0.0, le=1.0)


class RankRequest(RankOptions):
    resumes: List[ResumeData] = Field(min_length=1, max_length=MAX_RESUMES)


class RankedResume(BaseModel):
    rank: int
    filename: str
    score: float                      # final blended score, 0..1
    semantic_score: float             # calibrated semantic coverage, 0..1
    skill_score: Optional[float]      # share of JD skills found; null if JD named none
    raw_similarity: float             # uncalibrated cosine similarity
    matched_skills: List[str]
    explicit_matched_skills: List[str]
    implied_matched_skills: List[str]
    missing_skills: List[str]


class SkippedResume(BaseModel):
    filename: str
    reason: str


class RankResponse(BaseModel):
    ranked_resumes: List[RankedResume]
    jd_skills: List[str]
    skipped: List[SkippedResume]
    effective_semantic_weight: float


# --------------------------------- app setup --------------------------------- #
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Imported here so that importing this module (e.g. in tests) doesn't pull
    # in torch / download a model.
    from sentence_transformers import SentenceTransformer

    log.info("Loading model %s ...", MODEL_NAME)
    app.state.model = SentenceTransformer(MODEL_NAME)
    log.info("Model loaded.")
    yield


app = FastAPI(
    title="Semantic Resume Ranker API",
    description="Ranks resumes against a job description using SBERT embeddings plus skill matching.",
    lifespan=lifespan,
)

app.add_middleware(UploadRequestSizeLimitMiddleware, max_body_bytes=MAX_REQUEST_BYTES)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,  # no cookies are used; also invalid together with "*"
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/health")
def health(request: Request):
    return {
        "status": "ok",
        "model_loaded": getattr(request.app.state, "model", None) is not None,
        "max_upload_bytes": MAX_UPLOAD_BYTES,
        "max_resumes": MAX_RESUMES,
    }


def _validation_message(exc: ValidationError) -> str:
    return "; ".join(
        f"{'/'.join(str(part) for part in error['loc']) or 'request'}: {error['msg']}"
        for error in exc.errors(include_input=False)
    )


def _raise_validation(exc: ValidationError) -> None:
    # Exclude rejected values: Pydantic may otherwise echo resume text in errors.
    raise HTTPException(status_code=422, detail=f"Invalid request: {_validation_message(exc)}") from exc


def _safe_rank_error(exc: ValueError) -> str:
    """Allow only known input errors through; model/library messages can include input data."""
    safe_messages = {
        "The job description is empty.",
        "None of the resumes contained readable text.",
    }
    if str(exc) in safe_messages:
        return str(exc)
    return "The supplied text could not be ranked. Check the job description and resume text, then try again."


def _check_legacy_filenames(payload: RankRequest) -> None:
    for resume in payload.resumes:
        try:
            validate_filename(resume.filename)
        except DocumentValidationError as exc:
            raise HTTPException(status_code=422, detail=f"{resume.filename[:80] or 'Resume'}: {exc}") from exc


def _empty_rank_response(jd_text: str, semantic_weight: float, skipped: List[Dict[str, str]]) -> Dict[str, Any]:
    jd_skills = extract_skills(jd_text)
    return {
        "ranked_resumes": [],
        "jd_skills": sorted(jd_skills),
        "skipped": skipped,
        "effective_semantic_weight": 1.0 if not jd_skills else semantic_weight,
    }


async def _rank_multipart(request: Request, model: Any) -> Dict[str, Any]:
    try:
        form = await request.form(max_files=MAX_RESUMES + 1, max_fields=2, max_part_size=MAX_TEXT_CHARS)
    except Exception as exc:
        log.warning("Multipart parser rejected an upload (%s)", type(exc).__name__)
        raise HTTPException(status_code=400, detail="The multipart upload is malformed. Please choose the files again.") from exc

    try:
        try:
            options = RankOptions.model_validate({
                "jd_text": form.get("jd_text", ""),
                "semantic_weight": form.get("semantic_weight", 0.6),
            })
        except ValidationError as exc:
            _raise_validation(exc)

        uploads = form.getlist("resumes")
        if not uploads:
            raise HTTPException(status_code=422, detail="Select at least one resume file.")
        if len(uploads) > MAX_RESUMES:
            raise HTTPException(status_code=422, detail=f"A maximum of {MAX_RESUMES} resumes can be screened at once.")
        if any(not isinstance(upload, StarletteUploadFile) for upload in uploads):
            raise HTTPException(status_code=422, detail="Each resume must be uploaded as a file.")

        valid: List[Tuple[str, str]] = []
        skipped: List[Dict[str, str]] = []
        total_bytes = 0
        for upload in uploads:
            filename = upload.filename or ""
            try:
                # Read at most limit+1 bytes, so an oversized part is not copied into application memory.
                data = await upload.read(MAX_UPLOAD_BYTES + 1)
                total_bytes += len(data)
                if len(data) > MAX_UPLOAD_BYTES:
                    raise DocumentValidationError(
                        f"This file exceeds the {size_limit_label(MAX_UPLOAD_BYTES)} upload limit."
                    )
                if total_bytes > MAX_TOTAL_UPLOAD_BYTES:
                    raise DocumentValidationError(
                        f"The upload batch exceeds the {size_limit_label(MAX_TOTAL_UPLOAD_BYTES)} total limit."
                    )
                text = extract_resume_text(filename, upload.content_type, data, MAX_UPLOAD_BYTES)
                if len(text) > MAX_TEXT_CHARS:
                    raise DocumentValidationError(f"Extracted text exceeds the {MAX_TEXT_CHARS:,} character processing limit.")
                valid.append((filename, text))
            except DocumentValidationError as exc:
                skipped.append({"filename": filename or "(unnamed file)", "reason": str(exc)})
            except Exception:
                # Do not return parser internals or document content to the caller.
                skipped.append({"filename": filename or "(unnamed file)", "reason": "The file could not be processed. Verify it is a valid PDF, DOCX, or TXT file."})

        log.info("Screening %d uploaded resume(s); %d file(s) could not be processed", len(valid), len(skipped))
        if not valid:
            return _empty_rank_response(options.jd_text, options.semantic_weight, skipped)

        try:
            result = rank_resumes(model, options.jd_text, valid, semantic_weight=options.semantic_weight)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=_safe_rank_error(exc)) from exc
        except Exception as exc:
            log.error("Multipart ranking failed (unexpected error type: %s)", type(exc).__name__)
            raise HTTPException(status_code=500, detail="Ranking could not be completed. Check the service configuration and try again.") from None
        result["skipped"] = skipped + result["skipped"]
        return result
    finally:
        # Starlette's multipart parser may spool larger parts to temporary files.
        # Closing the form closes every UploadFile and removes those spooled files.
        await form.close()


@app.post("/rank", response_model=RankResponse)
async def rank(request: Request):
    """Rank uploaded resumes (multipart) or accept the legacy extracted-text JSON contract."""
    model = getattr(request.app.state, "model", None)
    if model is None:
        raise HTTPException(status_code=503, detail="The model is still loading. Try again in a moment.")

    content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if content_type == "multipart/form-data":
        return await _rank_multipart(request, model)
    if content_type != "application/json" and not content_type.endswith("+json"):
        raise HTTPException(status_code=415, detail="Use multipart/form-data with resume files or the legacy application/json request.")

    try:
        try:
            payload = RankRequest.model_validate(await request.json())
        except ValidationError as exc:
            _raise_validation(exc)
        except Exception as exc:
            raise HTTPException(status_code=400, detail="The JSON request is malformed.") from exc
        _check_legacy_filenames(payload)
        log.info("Ranking %d text resume(s)", len(payload.resumes))
        return rank_resumes(
            model,
            payload.jd_text,
            [(resume.filename, resume.text) for resume in payload.resumes],
            semantic_weight=payload.semantic_weight,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=_safe_rank_error(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        log.error("Text ranking failed (unexpected error type: %s)", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Ranking could not be completed. Check the service configuration and try again.") from None


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend_api:app", host="127.0.0.1", port=8000)
