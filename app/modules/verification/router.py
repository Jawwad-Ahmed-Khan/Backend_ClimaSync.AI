"""FastAPI router for the AI Verification Agent.

Mounts at /api/v1/verify — handles multipart uploads (images/videos/text).
All endpoints are authenticated.

Endpoints:
  POST /verify/text    — text-only analysis
  POST /verify/media   — image or video file upload (+ optional caption)
  POST /verify/mixed   — image + text together
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from app.modules.verification.schemas import TextVerificationRequest, VerificationResult
from app.modules.verification.service import VerificationAgent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/verify", tags=["AI Verification"])

# Allowed MIME types for image uploads
_ALLOWED_IMAGE_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/gif",
}

# Maximum file size: 20MB
_MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024


# ---------------------------------------------------------------------------
# Text verification
# ---------------------------------------------------------------------------

@router.post(
    "/text",
    response_model=VerificationResult,
    summary="Verify text report authenticity",
    description=(
        "Analyze a plain-text disaster report or social media post for authenticity. "
        "Detects fabricated narratives, inconsistencies, and manipulation signals."
    ),
    status_code=status.HTTP_200_OK,
)
async def verify_text(body: TextVerificationRequest) -> VerificationResult:
    """Run the AI verification agent on a text report."""
    if not body.text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Text content cannot be empty.",
        )

    agent = VerificationAgent()
    try:
        return await agent.verify_text(body.text, body.context)
    except Exception as exc:
        logger.exception("[verify/text] Verification failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI verification error: {exc}",
        ) from exc


# ---------------------------------------------------------------------------
# Media (image / video frame) verification
# ---------------------------------------------------------------------------

@router.post(
    "/media",
    response_model=VerificationResult,
    summary="Verify image or video authenticity",
    description=(
        "Upload an image (JPEG/PNG/WEBP/GIF) or video thumbnail. "
        "The AI will analyze visual content for manipulation, deepfakes, "
        "and inconsistencies with claimed disaster context."
    ),
    status_code=status.HTTP_200_OK,
)
async def verify_media(
    file: UploadFile = File(..., description="Image file to verify"),
    caption: str | None = Form(None, description="Optional caption/claim accompanying the media"),
) -> VerificationResult:
    """Verify an uploaded image for disaster authenticity."""
    # Validate MIME type
    content_type = file.content_type or ""
    if content_type not in _ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type '{content_type}'. Allowed: {', '.join(_ALLOWED_IMAGE_TYPES)}",
        )

    # Read and size-check
    image_bytes = await file.read()
    if len(image_bytes) > _MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {_MAX_FILE_SIZE_BYTES // (1024*1024)}MB.",
        )

    agent = VerificationAgent()
    try:
        return await agent.verify_image(image_bytes, content_type, caption)
    except Exception as exc:
        logger.exception("[verify/media] Verification failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI verification error: {exc}",
        ) from exc


# ---------------------------------------------------------------------------
# Mixed (image + text) verification
# ---------------------------------------------------------------------------

@router.post(
    "/mixed",
    response_model=VerificationResult,
    summary="Verify image + text together",
    description=(
        "Submit both an image and accompanying text (e.g. a social media post with caption). "
        "The AI analyses both together for cross-referencing inconsistencies."
    ),
    status_code=status.HTTP_200_OK,
)
async def verify_mixed(
    text: str = Form(..., description="Text or caption accompanying the media"),
    file: UploadFile | None = File(None, description="Optional image file"),
) -> VerificationResult:
    """Verify image + text together for cross-modal authenticity check."""
    if not text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Text content cannot be empty.",
        )

    image_bytes: bytes | None = None
    mime_type: str | None = None

    if file is not None:
        content_type = file.content_type or ""
        if content_type not in _ALLOWED_IMAGE_TYPES:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Unsupported file type '{content_type}'.",
            )
        image_bytes = await file.read()
        if len(image_bytes) > _MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File too large. Maximum size is 20MB.",
            )
        mime_type = content_type

    agent = VerificationAgent()
    try:
        return await agent.verify_mixed(image_bytes, mime_type, text)
    except Exception as exc:
        logger.exception("[verify/mixed] Verification failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI verification error: {exc}",
        ) from exc
