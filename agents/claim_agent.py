import re
import json
from config import gemini_model

def llm_claim_extraction(text: str) -> list:
    prompt = f"""
You are an information extraction system.
Extract all independent factual claims from the text.
A factual claim is a statement that can be verified as true or false.
Rules:
- Split compound sentences into separate claims.
- Keep original meaning. No opinions or questions.
- Each claim must be a complete sentence.
- If no claims exist, return an empty list.
Return ONLY valid JSON array of strings. No markdown, no preamble.

Text: {text}
"""
    try:
        response = gemini_model.generate_content(prompt)
        raw = response.text.strip().strip("```json").strip("```").strip()
        return json.loads(raw)
    except Exception as e:
        print(f"[ClaimAgent] LLM fallback failed: {e}")
        return [text]


def claim_agent(state: dict) -> dict:
    text = state.get("claim", "")

    parts = re.split(r'\band\b|\bbut\b|\bwhile\b', text)
    claims = [p.strip() for p in parts if len(p.strip()) > 3]

    if len(claims) <= 1:
        claims = llm_claim_extraction(text)

    print(f"[ClaimAgent] 📋 Extracted {len(claims)} claim(s): {claims}")
    return {**state, "claims": claims}