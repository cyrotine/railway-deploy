import os

from dotenv import load_dotenv
import google.genai as genai
from openai import OpenAI
from types import SimpleNamespace

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

def _make_gemini_model():
    """Create a model-like object with a generate_content(prompt) -> .text

    This function attempts several common shapes of the new `google.genai`
    package so the rest of the codebase can continue to call
    `gemini_model.generate_content(prompt).text` regardless of the installed
    genai package version.
    """
    model_name = "gemini-2.5-flash"
    generation_config = {"response_mime_type": "application/json"}

    # If the old compatibility method exists, call it (safe no-op on newer libs)
    try:
        if hasattr(genai, "configure"):
            try:
                genai.configure(api_key=GEMINI_API_KEY)
            except Exception:
                # Non-fatal — continue to try other initializations
                pass

        # Prefer an exposed GenerativeModel if present
        if hasattr(genai, "GenerativeModel"):
            try:
                return genai.GenerativeModel(model_name, generation_config=generation_config)
            except Exception:
                # fall through
                pass

        # Try common client constructors
        client = None
        if hasattr(genai, "Client"):
            try:
                client = genai.Client(api_key=GEMINI_API_KEY)
            except Exception:
                client = None
        elif hasattr(genai, "GenAIClient"):
            try:
                client = genai.GenAIClient(api_key=GEMINI_API_KEY)
            except Exception:
                client = None

        if client is not None:
            # Wrap the client to match older generate_content(prompt).text API
            class _Wrapper:
                def __init__(self, client, model_name, generation_config):
                    self.client = client
                    self.model_name = model_name
                    self.generation_config = generation_config

                def generate_content(self, prompt: str):
                    # Try generate_text-style API
                    try:
                        if hasattr(self.client, "generate_text"):
                            resp = self.client.generate_text(model=self.model_name, input=prompt)
                            # Common shapes: resp.text or resp.output_text
                            if hasattr(resp, "text"):
                                return SimpleNamespace(text=resp.text)
                            if hasattr(resp, "output_text"):
                                return SimpleNamespace(text=resp.output_text)
                            return SimpleNamespace(text=str(resp))

                        # Try chat completions
                        if hasattr(self.client, "chat") and hasattr(self.client.chat, "completions"):
                            resp = self.client.chat.completions.create(model=self.model_name, messages=[{"role": "user", "content": prompt}])
                            try:
                                return SimpleNamespace(text=resp.choices[0].message.content)
                            except Exception:
                                return SimpleNamespace(text=str(resp))

                        # Fallback: try a generic generate or generate_text on the module
                        if hasattr(genai, "generate_text"):
                            resp = genai.generate_text(model=self.model_name, input=prompt)
                            return SimpleNamespace(text=getattr(resp, "text", str(resp)))

                        raise RuntimeError("No recognized generation API available on genai client")
                    except Exception as e:
                        # Re-raise with context for easier debugging in deployment logs
                        raise RuntimeError(f"Gemini generation error: {e}")

            return _Wrapper(client, model_name, generation_config)

    except Exception as e:
        print(f"[Config] genai setup warning: {e}")

    # Last-resort fallback that throws when used so errors are explicit
    class _Unavailable:
        def generate_content(self, prompt: str):
            raise RuntimeError("No usable google.genai API available in environment")

    return _Unavailable()


# Build gemini_model using the flexible initializer above
gemini_model = _make_gemini_model()

openrouter_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)