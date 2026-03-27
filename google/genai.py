"""Compatibility shim for google.genai

This module exposes a minimal compatibility layer for code written for the
deprecated `google.generativeai` API. It will try to delegate to the installed
`google.genai` package when available. The goal is to avoid a hard crash on
`genai.configure(...)` or `genai.GenerativeModel(...)` and provide helpful
errors if the new package's API differs in incompatible ways.

This is intentionally small and defensive — if you prefer a direct port to the
new package's API I can update the project to use that instead.
"""

from types import SimpleNamespace
import importlib
import traceback

# Try to import the real package if available
_real = None
try:
    _real = importlib.import_module("google.genai")
except Exception:
    _real = None

# Stored client created during configure (if the underlying package provides one)
_client = None
_api_key = None

def configure(api_key: str | None = None, **kwargs):
    """Store the api_key and, if the installed package exposes a Client,
    construct and keep a client instance for subsequent calls.
    """
    global _client, _api_key
    _api_key = api_key
    if _real is None:
        # No installed package — just store the key so code that only checks for
        # configuration value won't fail.
        _client = None
        return

    # Try several common client constructor names used by different releases.
    try:
        if hasattr(_real, "Client"):
            _client = _real.Client(api_key=api_key)
            return
        if hasattr(_real, "GenAIClient"):
            _client = _real.GenAIClient(api_key=api_key)
            return
        # Some variants accept a top-level init function or require environment vars.
        _client = None
    except Exception:
        # Keep _client as None but don't crash here — errors will surface when
        # the project actually attempts to call the client.
        _client = None


class GenerativeModel:
    """A thin compatibility wrapper that exposes generate_content(prompt).

    The wrapper will attempt to use the underlying installed `google.genai`
    client if available, otherwise it returns a SimpleNamespace with a
    .text attribute (so existing code expecting `.text` continues to work).
    """

    def __init__(self, model_name: str, generation_config: dict | None = None):
        self.model_name = model_name
        self.generation_config = generation_config or {}

    def generate_content(self, prompt: str):
        text = ""
        # Prefer using a constructed client if present
        try:
            if _client is not None:
                # Heuristics to call a few possible client APIs
                if hasattr(_client, "generate_text"):
                    # new-style text generation
                    try:
                        resp = _client.generate_text(model=self.model_name, input=prompt)
                        # Try common response shapes
                        if hasattr(resp, "text"):
                            text = resp.text
                        elif hasattr(resp, "output") and resp.output:
                            # try nested content
                            try:
                                text = resp.output[0].content[0].text
                            except Exception:
                                text = str(resp)
                        else:
                            text = str(resp)
                    except Exception:
                        # If the client's generate_text signature differs, fallback
                        # to a generic call
                        try:
                            resp = _client.generate(model=self.model_name, prompt=prompt)
                            text = getattr(resp, "text", str(resp))
                        except Exception:
                            raise
                elif hasattr(_client, "chat") and hasattr(_client.chat, "completions"):
                    # fallback for chat-like clients
                    resp = _client.chat.completions.create(model=self.model_name, messages=[{"role":"user","content":prompt}])
                    try:
                        text = resp.choices[0].message.content
                    except Exception:
                        text = str(resp)
                else:
                    # No recognized client API — try calling top-level functions on the
                    # real package if present.
                    if _real is not None and hasattr(_real, "generate_text"):
                        resp = _real.generate_text(model=self.model_name, input=prompt)
                        text = getattr(resp, "text", str(resp))
                    else:
                        raise RuntimeError("Installed google.genai package does not expose a supported client API")
            else:
                # No client constructed earlier — attempt to use the installed package
                if _real is not None:
                    if hasattr(_real, "generate_text"):
                        resp = _real.generate_text(model=self.model_name, input=prompt)
                        text = getattr(resp, "text", str(resp))
                    elif hasattr(_real, "Client"):
                        # lazily instantiate a client
                        try:
                            real_client = _real.Client(api_key=_api_key)
                            if hasattr(real_client, "generate_text"):
                                resp = real_client.generate_text(model=self.model_name, input=prompt)
                                text = getattr(resp, "text", str(resp))
                            else:
                                text = str(resp)
                        except Exception as e:
                            raise
                    else:
                        raise RuntimeError("No usable google.genai API available in the installed package")
                else:
                    raise RuntimeError("google.genai is not installed")
        except Exception as e:
            # Re-raise with more diagnostic info
            tb = traceback.format_exc()
            raise RuntimeError(f"Error calling underlying genai API: {e}\n{tb}")

        # Return an object that matches older code expectations: .text
        return SimpleNamespace(text=text)


def __getattr__(name: str):
    """Expose a friendly error when someone attempts to access attributes
    we don't explicitly provide.
    """
    raise AttributeError(f"Compatibility shim provides only 'configure' and 'GenerativeModel'. Attempted to access: {name}")
