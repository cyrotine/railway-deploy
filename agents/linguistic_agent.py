import json
from config import gemini_model
from agents.gemini_util import _call_gemini_with_retry

async def linguistic_agent(state: dict) -> dict:
    """
    Analyzes the claim's linguistic properties (emotion, manipulation, bias, tone).
    """
    claim = state.get("claim", "")
    print(f"[Linguistic Agent] Analyzing claim via Gemini...")

    prompt = f"""
    You are an expert linguistic analyst specializing in media bias and misinformation detection.
    Analyze the following claim for its linguistic properties.

    CLAIM: "{claim}"

    Respond STRICTLY in the following JSON format (no markdown, no explanation):
    {{
        "emotion_score": <float 0.0-1.0>,
        "manipulation_score": <float 0.0-1.0>,
        "bias_score": <float 0.0-1.0>,
        "tone": "<Neutral|Sensationalist|Alarmist|Opinionated>",
        "key_flags": ["flag 1", "flag 2"]
    }}
    """

    try:
        gemini_response = await _call_gemini_with_retry(gemini_model, prompt)
        cleaned = gemini_response.strip()
        if "```json" in cleaned:
             cleaned = cleaned.split("```json")[-1].split("```")[0].strip()
        elif "```" in cleaned:
             cleaned = cleaned.split("```")[-1].split("```")[0].strip()
            
        result = json.loads(cleaned)
        state["linguistic"] = {
            "emotion_score": round(float(result.get("emotion_score", 0.5)), 2),
            "manipulation_score": round(float(result.get("manipulation_score", 0.5)), 2),
            "bias_score": round(float(result.get("bias_score", 0.5)), 2),
            "tone": result.get("tone", "Neutral"),
            "key_flags": result.get("key_flags", [])
        }
    except Exception as e:
        print(f"[Linguistic Agent] Error: {e}")
        state["linguistic"] = {"tone": "Unknown", "key_flags": [f"Error: {e}"]}

    return state
