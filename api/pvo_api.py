from flask import Blueprint, request, jsonify
from flask_restful import Api, Resource
import google.generativeai as genai
import base64
import json
import os
import re

# ---------------------------------------------------------------------------
# Blueprint setup — mirrors the pattern in chat_api.py
# ---------------------------------------------------------------------------
pvo_api = Blueprint('pvo_api', __name__, url_prefix='/api/pvo')
api = Api(pvo_api)

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# ---------------------------------------------------------------------------
# Allowed MIME types for uploaded documents
# ---------------------------------------------------------------------------
ALLOWED_MIME_TYPES = {
    'image/jpeg', 'image/jpg', 'image/png',
    'image/gif', 'image/webp', 'image/bmp',
    'image/tiff',
}

# ---------------------------------------------------------------------------
# Prompt sent to Gemini Vision
# ---------------------------------------------------------------------------
EXTRACTION_PROMPT = """You are an OCR assistant. Extract ALL visible text and fields from this government-issued ID or document image.

Return ONLY a valid JSON object — no markdown fences, no extra explanation.

Use exactly these keys (use null for any field you cannot find):
{
  "first_name":         "<first name or null>",
  "last_name":          "<last name or null>",
  "address":            "<full street address line or null>",
  "street":             "<street number and name only, or null>",
  "city":               "<city or null>",
  "state":              "<2-letter state abbreviation or null>",
  "zip":                "<5-digit ZIP or null>",
  "home_phone":         "<home phone formatted (xxx) xxx-xxxx or null>",
  "cell_phone":         "<cell phone formatted (xxx) xxx-xxxx or null>",
  "email":              "<email address or null>",
  "branch":             "<one of: Army, Navy, Air Force, Marine Corps, Coast Guard, Space Force — or null>",
  "date_of_birth":      "<DOB MM/DD/YYYY or null>",
  "id_number":          "<DL or ID number or null>",
  "expiration_date":    "<expiration date or null>",
  "raw_visible_text":   "<ALL text visible on the document, transcribed verbatim, line by line>",
  "confidence_summary": "<one short sentence: what you found and how confident you are>"
}

Rules:
- Output valid JSON only. No markdown backticks, no prose.
- For state, always use the 2-letter abbreviation (e.g. CA, not California).
- For branch, only populate if the document explicitly mentions military service.
- raw_visible_text must include everything readable on the document.
"""


# ---------------------------------------------------------------------------
# Helper: strip markdown fences Gemini sometimes wraps JSON in
# ---------------------------------------------------------------------------
def clean_json_response(text: str) -> str:
    text = text.strip()
    # Remove ```json ... ``` or ``` ... ```
    text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s*```$', '', text)
    return text.strip()


# ---------------------------------------------------------------------------
# Resource: POST /api/pvo/extract-document
# ---------------------------------------------------------------------------
class ExtractDocumentAPI(Resource):

    def options(self):
        """Preflight CORS — headers added by main app."""
        return {}, 200

    def post(self):
        try:
            print("RAW DATA:", request.get_data())
            data = request.get_json(force=True, silent=True)
            print("PARSED:", data.keys() if data else "NO DATA")

            # ── Validate request ──────────────────────────────────────────
            if not data:
                return {"error": "Request body must be JSON."}, 400

            image_b64  = data.get('imageBase64', '').strip()
            mime_type  = data.get('mimeType', 'image/jpeg').strip().lower()
            # documentType is accepted but not required — kept for future use
            # doc_type = data.get('documentType', 'drivers_license')

            if not image_b64:
                return {"error": "imageBase64 is required."}, 400

            if mime_type not in ALLOWED_MIME_TYPES:
                return {
                    "error": f"Unsupported mimeType '{mime_type}'. "
                             f"Allowed: {', '.join(sorted(ALLOWED_MIME_TYPES))}"
                }, 400

            # ── Validate base64 payload ───────────────────────────────────
            try:
                image_bytes = base64.b64decode(image_b64, validate=True)
            except Exception:
                return {"error": "imageBase64 is not valid base64."}, 400

            if len(image_bytes) < 100:
                return {"error": "Image data appears too small or empty."}, 400

            # ── Gemini API key check ──────────────────────────────────────
            if not GEMINI_API_KEY:
                return {
                    "error": "Gemini API key not configured.",
                    "details": "Set the GEMINI_API_KEY environment variable."
                }, 500

            # ── Call Gemini Vision ────────────────────────────────────────
            model = genai.GenerativeModel('gemini-2.5-flash-lite')

            image_part = {
                "mime_type": mime_type,
                "data": image_bytes,
            }

            response = model.generate_content([EXTRACTION_PROMPT, image_part])
            raw_text = response.text or ''

            # ── Parse JSON from model response ────────────────────────────
            try:
                cleaned = clean_json_response(raw_text)
                extracted = json.loads(cleaned)
            except json.JSONDecodeError:
                # Return the raw text so the frontend can still do its own
                # regex-based parsing via parseDocumentText()
                return {
                    "success": True,
                    "extracted": {
                        "raw_visible_text": raw_text,
                        "confidence_summary": "Could not parse structured fields — raw text returned.",
                    }
                }, 200

            # ── Normalise nulls / strip whitespace ────────────────────────
            for key, value in extracted.items():
                if isinstance(value, str):
                    value = value.strip()
                    extracted[key] = value if value not in ('', 'null', 'NULL', 'None') else None

            return {
                "success": True,
                "extracted": extracted,
            }, 200

        except Exception as exc:
            return {
                "error": "Internal server error.",
                "details": str(exc),
            }, 500


# Register the resource
api.add_resource(ExtractDocumentAPI, '/extract-document')
