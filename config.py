import os

from dotenv import load_dotenv
from google import genai
from google.genai import types
from types import SimpleNamespace

# Load variables from .env into the environment (no-op if .env is missing,
# which is normal on Railway where env vars are injected directly)
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

# Validate required keys — fail fast at startup if any are missing
missing = [name for name, val in {
    "GEMINI": GEMINI_API_KEY,
    "TAVILY_API_KEY": TAVILY_API_KEY,
}.items() if not val]

if missing:
    raise ValueError(
        f"[Config] ❌ Missing required environment variables: {', '.join(missing)}\n"
        "Please set them in your .env file (local) or Railway Variables (production)."
    )


# ── Gemini model wrapper ────────────────────────────────────────────────────
# The `google-genai` SDK uses `genai.Client()` + `client.models.generate_content()`.
# This wrapper preserves the `.generate_content(prompt).text` interface so all
# existing agent code keeps working without changes.

_MODEL_NAME = "gemini-2.5-flash"
_gemini_client = genai.Client(api_key=GEMINI_API_KEY)


class _GeminiModelWrapper:
    """Thin adapter so callers can do  gemini_model.generate_content(prompt).text"""

    def generate_content(self, prompt: str):
        response = _gemini_client.models.generate_content(
            model=_MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
        return SimpleNamespace(text=response.text)


gemini_model = _GeminiModelWrapper()