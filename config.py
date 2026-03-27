import os

from dotenv import load_dotenv
import google.genai as genai
from openai import OpenAI

# Load variables from .env into the environment (no-op if already set)
load_dotenv()

GEMINI_API_KEY     = os.getenv("GEMINI")
TAVILY_API_KEY     = os.getenv("TAVILY_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Validate required keys — fail fast at startup if any are missing
missing = [name for name, val in {
    "GEMINI": GEMINI_API_KEY,
    "TAVILY_API_KEY": TAVILY_API_KEY,
    "OPENROUTER_API_KEY": OPENROUTER_API_KEY,
}.items() if not val]

if missing:
    raise ValueError(
        f"[Config] ❌ Missing required environment variables: {', '.join(missing)}\n"
        "Please add them to your .env file."
    )

genai.configure(api_key=GEMINI_API_KEY)
# We use gemini-2.5-flash for speed and enforce valid JSON output
gemini_model = genai.GenerativeModel(
    "gemini-2.5-flash",
    generation_config={"response_mime_type": "application/json"},
)

openrouter_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)