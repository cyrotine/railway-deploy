"""
Local compatibility package to expose a `google` namespace for imports in this project.

This package contains a lightweight shim for `google.genai` so existing code
that calls `genai.configure(...)` and `genai.GenerativeModel(...)` continues to work
while delegating to the real `google.genai` package (if installed).

This shim is intentionally defensive: it tries to use the installed `google.genai`
but provides fallbacks that return readable errors if the newer API isn't available.
"""

from . import genai

__all__ = ["genai"]
