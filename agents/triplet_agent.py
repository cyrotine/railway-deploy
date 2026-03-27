import json
from config import gemini_model
from agents.gemini_util import _call_gemini_with_retry

async def triplet_agent(state: dict) -> dict:
    """
    Extracts subject-action-object triplets from the claim and evidence.
    """
    claim = state.get("claim", "")
    evidence = state.get("evidence", [])
    
    context_text = f"Claim: {claim}\n" + "\n".join([ev.get("article_content", "")[:200] for ev in evidence[:3]])
    
    print(f"[Triplet Agent] Extracting entities via Gemini...")
    
    prompt = f"""
    Transform the following text into knowledge graph triplets.
    Extract the core claims into "subject", "action", and "object" format.
    Return ONLY a raw JSON array of objects.
    
    Format:
    [
      {{"subject": "Entity 1", "action": "verb", "object": "Entity 2"}}
    ]
    
    Text: {context_text}
    """
    
    try:
        gemini_response = await _call_gemini_with_retry(gemini_model, prompt)
        cleaned = gemini_response.strip()
        if "```json" in cleaned:
             cleaned = cleaned.split("```json")[-1].split("```")[0].strip()
        elif "```" in cleaned:
             cleaned = cleaned.split("```")[-1].split("```")[0].strip()
            
        triplets = json.loads(cleaned)
        state["triplets"] = triplets
    except Exception as e:
        print(f"[Triplet Agent] Error: {e}")
        state["triplets"] = [{"subject": "Extraction", "action": "failed", "object": str(e)}]
        
    return state
