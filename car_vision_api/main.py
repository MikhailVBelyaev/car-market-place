"""
Car Vision API
--------------
POST /analyze  — Upload a car photo (exterior or interior).
                 Returns condition, brand/model, color, body type, and a text summary.

Provider: OpenCode Go — https://opencode.ai/zen/go/v1/messages
API key:  set OPENCODE_GO_API_KEY in car_vision_api/.env

Condition scale (aligned with the main DB's condition field):
  ideal        — like new, zero visible defects
  good         — minor wear only (small scratches, light fading)
  normal       — moderate wear (several scratches, small dents)
  damaged      — visible significant damage (dents, cracks, rust)
  needs_repair — major damage, structural or mechanical issues visible
"""

import base64
import json
import logging
import os
import re

import anthropic
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="Car Vision API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Provider: Anthropic API (vision-capable)
# Model: claude-haiku-4-5-20251001 — cheapest Anthropic model with vision
# ---------------------------------------------------------------------------
DEFAULT_MODEL   = os.getenv("VISION_MODEL", "claude-haiku-4-5-20251001")
MAX_IMAGE_BYTES = 10 * 1024 * 1024
ALLOWED_MIME    = {"image/jpeg", "image/png", "image/webp", "image/gif"}

_client: anthropic.Anthropic | None = None


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        if not key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. "
                "Add it to car_vision_api/.env and restart the service."
            )
        _client = anthropic.Anthropic(api_key=key)
    return _client


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

class CarAnalysis(BaseModel):
    photo_type: str
    """exterior | interior | damage | unknown"""

    condition: str
    """ideal | good | normal | damaged | needs_repair | unknown"""

    condition_score: int
    """1 (needs_repair) … 5 (ideal)"""

    condition_details: str
    """1–2 sentence explanation of the condition rating"""

    brand: str | None
    model: str | None
    year_estimate: str | None
    """E.g. '2015–2019' or null"""

    color: str | None
    body_type: str | None
    """sedan | suv | hatchback | wagon | coupe | minivan | pickup | other | null"""

    damage_areas: list[str]
    """Visible damage locations. Empty list for clean cars."""

    summary: str
    """2–3 sentence overall assessment"""


CONDITION_SCORE = {
    "ideal": 5, "good": 4, "normal": 3,
    "damaged": 2, "needs_repair": 1, "unknown": 0,
}

ANALYSIS_PROMPT = """\
You are an expert automotive inspector with 20 years of experience.

Analyze the car photo and return ONLY a JSON object with these exact fields:

{
  "photo_type": "exterior" | "interior" | "damage" | "unknown",
  "condition": "ideal" | "good" | "normal" | "damaged" | "needs_repair",
  "condition_details": "<1-2 sentences explaining what determines the condition>",
  "brand": "<manufacturer, e.g. Toyota, or null>",
  "model": "<model name, e.g. Camry, or null>",
  "year_estimate": "<year range e.g. 2015-2019, or null>",
  "color": "<primary exterior color in English, or null for interior shots>",
  "body_type": "sedan" | "suv" | "hatchback" | "wagon" | "coupe" | "minivan" | "pickup" | "other" | null,
  "damage_areas": ["<list of visible damage locations>"],
  "summary": "<2-3 sentence overall assessment>"
}

Condition definitions:
- ideal: like new, no visible scratches, dents, rust, or wear
- good: minor wear — very light scratches, barely noticeable
- normal: moderate wear — several scratches, small dents, some fading
- damaged: significant damage — notable dents, deep scratches, cracked parts, rust
- needs_repair: major damage — structural issues, heavy rust, broken panels

Return ONLY the JSON object. No markdown, no extra text."""


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/healthz")
def health():
    key_set = bool(os.getenv("ANTHROPIC_API_KEY", "").strip())
    return {
        "status": "ok",
        "provider": "anthropic",
        "model": DEFAULT_MODEL,
        "api_key_configured": key_set,
    }


@app.post("/analyze", response_model=CarAnalysis)
async def analyze(file: UploadFile = File(..., description="Car photo (JPEG/PNG/WEBP)")):
    # --- Validate input ---
    content_type = (file.content_type or "image/jpeg").split(";")[0].strip()
    if content_type not in ALLOWED_MIME:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported type '{content_type}'. Use JPEG, PNG or WEBP.",
        )

    data = await file.read()
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image exceeds 10 MB limit")
    if len(data) < 100:
        raise HTTPException(status_code=400, detail="Image file appears to be empty")

    logger.info("Analyzing %s — %.1f KB, type=%s, model=%s",
                file.filename, len(data) / 1024, content_type, DEFAULT_MODEL)

    # --- Call OpenCode Go (Anthropic-compatible endpoint) ---
    image_b64 = base64.standard_b64encode(data).decode()
    try:
        client = get_client()
        response = client.messages.create(
            model=DEFAULT_MODEL,
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": content_type,
                                "data": image_b64,
                            },
                        },
                        {"type": "text", "text": ANALYSIS_PROMPT},
                    ],
                }
            ],
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except anthropic.AuthenticationError:
        raise HTTPException(status_code=500, detail="Invalid OPENCODE_GO_API_KEY")
    except anthropic.APIConnectionError as e:
        raise HTTPException(status_code=502, detail=f"OpenCode Go unreachable: {e}")
    except Exception as e:
        logger.exception("OpenCode Go API error")
        raise HTTPException(status_code=500, detail=str(e))

    # --- Parse JSON from model response ---
    raw = response.content[0].text.strip()
    logger.info("Raw response: %s", raw[:400])

    # Strip markdown code fences if the model added them
    json_match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not json_match:
        logger.error("No JSON in response: %s", raw)
        raise HTTPException(status_code=500, detail="Model returned non-JSON response")

    try:
        parsed = json.loads(json_match.group())
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"JSON parse error: {e}")

    condition = parsed.get("condition", "unknown")
    result = CarAnalysis(
        photo_type       = parsed.get("photo_type", "unknown"),
        condition        = condition,
        condition_score  = CONDITION_SCORE.get(condition, 0),
        condition_details= parsed.get("condition_details", ""),
        brand            = parsed.get("brand") or None,
        model            = parsed.get("model") or None,
        year_estimate    = parsed.get("year_estimate") or None,
        color            = parsed.get("color") or None,
        body_type        = parsed.get("body_type") or None,
        damage_areas     = parsed.get("damage_areas") or [],
        summary          = parsed.get("summary", ""),
    )
    logger.info("Result: condition=%s(%d) brand=%s model=%s",
                result.condition, result.condition_score, result.brand, result.model)
    return result
