import re
import json
from config import gemini_model


def verification_agent(state: dict) -> dict:
    claims   = state.get("claims", [state.get("claim", "")])
    evidence = state.get("evidence", [])

    evidence_text = ""
    for i, ev in enumerate(evidence, 1):
        evidence_text += f"""
Evidence {i}
Title:   {ev['title']}
Source:  {ev['source']}
Content: {ev['article_content']}
"""

    results = []
    for claim in claims:
        prompt = f"""
You are a strict fact-checking system.
Verify the claim ONLY using the provided evidence.
Do NOT use prior knowledge.
If evidence is insufficient → return UNVERIFIED.

Claim:
{claim}

Evidence:
{evidence_text}

Return ONLY a JSON object (no markdown, no preamble):
{{
  "verdict": "TRUE | FALSE | MISLEADING | UNVERIFIED",
  "confidence": 0-100,
  "reasoning": "short explanation referencing the evidence"
}}
"""
        try:
            response = gemini_model.generate_content(prompt)
            raw = response.text.strip()
            raw = re.sub(r'^```[a-z]*\n?', '', raw).strip('`').strip()
            parsed = json.loads(raw)
        except Exception as e:
            print(f"[Verify] Parse error for '{claim}': {e}")
            parsed = {
                "verdict":    "UNVERIFIED",
                "confidence": 0,
                "reasoning":  f"Could not parse LLM response: {e}"
            }

        results.append({"claim": claim, **parsed})
        print(f"[Verify] 🏁 '{claim[:60]}' → {parsed.get('verdict')} ({parsed.get('confidence')}%)")

    return {**state, "results": results}