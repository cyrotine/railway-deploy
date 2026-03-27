import re
import unicodedata

# ── Blocklists ───────────────────────────────────────────────────────────────

# Prompt injection patterns (LLM jailbreak attempts)
PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions",
    r"disregard\s+(all\s+)?(previous|prior|above)\s+instructions",
    r"forget\s+(all\s+)?(previous|prior|above)\s+instructions",
    r"you\s+are\s+now\s+.{0,30}(dan|jailbreak|evil|unrestricted)",
    r"act\s+as\s+(if\s+you\s+are\s+)?a(n)?\s+.{0,30}(unrestricted|unfiltered|evil|jailbreak)",
    r"pretend\s+(you\s+are|to\s+be)\s+.{0,30}(unrestricted|unfiltered|evil)",
    r"new\s+instructions\s*:",
    r"system\s*:\s*you\s+are",
    r"<\s*system\s*>",
    r"\[\s*system\s*\]",
    r"##\s*instruction",
    r"your\s+new\s+(role|persona|task)\s+is",
    r"override\s+(safety|filter|previous)",
]

# SQL injection patterns
SQL_INJECTION_PATTERNS = [
    r"(\b(select|insert|update|delete|drop|truncate|alter|create|replace)\b.{0,20}\b(from|into|table|database)\b)",
    r"(union\s+(all\s+)?select)",
    r"(--\s|\s--$|;--)",
    r"(\bor\b\s+\d+\s*=\s*\d+)",
    r"(\band\b\s+\d+\s*=\s*\d+)",
    r"(xp_cmdshell|exec\s*\(|execute\s*\()",
    r"(information_schema|sys\.tables|sysobjects)",
]

# XSS / script injection patterns
XSS_PATTERNS = [
    r"<\s*script.*?>",
    r"javascript\s*:",
    r"on\w+\s*=\s*[\"']",          # onclick=, onload=, onerror= etc.
    r"<\s*iframe.*?>",
    r"<\s*img[^>]+src\s*=",
    r"<\s*svg.*?on\w+",
    r"expression\s*\(",             # CSS expression()
    r"vbscript\s*:",
    r"data\s*:\s*text/html",
]

# Path traversal / command injection
PATH_CMD_PATTERNS = [
    r"(\.\./|\.\.\\){2,}",         # ../../
    r"(\/etc\/passwd|\/etc\/shadow|\/proc\/self)",
    r"(%2e%2e%2f|%2e%2e\/|\.\.%2f)", # URL-encoded traversal
    r"(\||\$\(|`).{0,50}(ls|cat|rm|wget|curl|bash|sh|python|perl|ruby)",
    r"(;\s*(ls|cat|rm|wget|curl|bash|whoami|id)\b)",
    r"&&\s*(ls|cat|rm|wget|curl|bash|whoami)",
]

# SSRF / URL injection
SSRF_PATTERNS = [
    r"(https?|ftp|file|gopher|dict|ldap)\s*://\s*(localhost|127\.|0\.0\.0\.0|169\.254|::1|internal|10\.\d|192\.168|172\.(1[6-9]|2\d|3[01]))",
    r"@(localhost|127\.0\.0\.1)",
]

ALL_ATTACK_PATTERNS = (
    PROMPT_INJECTION_PATTERNS
    + SQL_INJECTION_PATTERNS
    + XSS_PATTERNS
    + PATH_CMD_PATTERNS
    + SSRF_PATTERNS
)

# Pre-compile all patterns for performance
COMPILED_PATTERNS = [
    re.compile(p, re.IGNORECASE | re.DOTALL)
    for p in ALL_ATTACK_PATTERNS
]


# ── Helpers ──────────────────────────────────────────────────────────────────

def _normalize(text: str) -> str:
    """
    Normalize unicode to catch homoglyph attacks
    (e.g. ｉgnore → ignore, ＳＥＬＥＣＴs → SELECT).
    """
    return unicodedata.normalize("NFKC", text)


def _strip_html(text: str) -> str:
    """Remove all HTML/XML tags."""
    return re.sub(r"<[^>]*?>", "", text)


def _strip_null_bytes(text: str) -> str:
    """Remove null bytes and other control characters."""
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)


def _collapse_whitespace(text: str) -> str:
    """Collapse multiple spaces/newlines into a single space."""
    return re.sub(r"\s+", " ", text).strip()


def _detect_attack(text: str) -> str | None:
    """
    Returns the name of the first attack pattern matched,
    or None if the input is clean.
    """
    for pattern in COMPILED_PATTERNS:
        if pattern.search(text):
            return pattern.pattern
    return None


def _allow_safe_chars(text: str) -> str:
    """
    Keep only characters that are legitimate in a factual claim:
    letters, digits, whitespace, and common punctuation.
    Strips everything else.
    """
    return re.sub(r"[^\w\s?.!,'\"()\-:]", "", text)


# ── Main agent ───────────────────────────────────────────────────────────────

def sanitization_agent(state: dict) -> dict:
    raw: str = state.get("claim", "")

    # 1. Normalize unicode (homoglyph / fullwidth char attacks)
    query = _normalize(raw)

    # 2. Strip null bytes and invisible control characters
    query = _strip_null_bytes(query)

    # 3. Strip all HTML tags
    query = _strip_html(query)

    # 4. Collapse whitespace for consistent pattern matching
    query = _collapse_whitespace(query)

    # 5. Attack detection on the cleaned (but not yet char-stripped) text
    #    We detect BEFORE stripping chars so obfuscated payloads are caught.
    matched = _detect_attack(query)
    if matched:
        print(f"[Sanitize] 🚨 Attack pattern detected — blocking request.")
        return {**state, "error": "BLOCKED: Malicious input detected."}

    # 6. Allow only safe characters
    query = _allow_safe_chars(query)

    # 7. Final whitespace collapse after char stripping
    query = _collapse_whitespace(query)

    # 8. Length checks
    if len(query) < 5:
        return {**state, "error": "Query too short after sanitization."}
    if len(query) > 1000:
        query = query[:1000]

    print(f"[Sanitize] ✅ Clean claim: {query}")
    return {**state, "claim": query}