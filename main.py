from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from orchestrator import graph
import pytesseract
from PIL import Image
import io

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

app = FastAPI(title="VeriFlow API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ClaimRequest(BaseModel):
    claim: str


def format_response(state: dict) -> dict:
    results    = state.get("results", [])
    top        = results[0] if results else {}
    verdict    = top.get("verdict", "UNVERIFIED")
    confidence = top.get("confidence", 0)
    raw_text   = state.get("claim", "")

    evidence = [
        {
            "source": ev.get("title") or ev.get("source", "Unknown"),
            "quote":  ev.get("article_content", "")[:250],
            "url":    ev.get("url", ""),
        }
        for ev in state.get("evidence", [])
    ]

    timeline = [
        {"time": "30 days ago", "text": "Historical events matching the extracted entities."},
        {"time": "7 days ago",  "text": "Initial reports from trusted sources surfaced."},
        {"time": "Live",        "text": "Latest searches performed via Tavily API."}
    ]

    return {
        "verdict":    verdict,
        "confidence": confidence,
        "reasoning":  top.get("reasoning", ""),
        "evidence":   evidence,
        "triplets":   state.get("triplets", []),
        "linguistic": state.get("linguistic", {}),
        "timeline":   timeline,
        "sentence_analysis": [{
            "sentence": state.get("claim", ""),
            "label": verdict,
            "confidence": confidence,
            "reason": top.get("reasoning", "Analysis complete.")
        }],
        "raw_text": raw_text
    }


@app.post("/analyze")
async def analyze(req: ClaimRequest):
    if not req.claim.strip():
        raise HTTPException(status_code=400, detail="Claim cannot be empty.")
    try:
        result = await graph.ainvoke({
            "claim":    req.claim,
            "claims":   [],
            "evidence": [],
            "results":  [],
            "error":    None,
        })
        return format_response(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze-image")
async def analyze_image(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image.")
    
    try:
        # Read the file content
        contents = await file.read()
        img = Image.open(io.BytesIO(contents))
        
        # Extract text using Tesseract
        extracted_text = pytesseract.image_to_string(img)
        
        if not extracted_text.strip():
            raise HTTPException(status_code=400, detail="Could not extract any text from the image.")
            
        print(f"[OCR] Extracted text: {extracted_text[:100]}...")
        
        # Run the standard analysis on the extracted text
        result = await graph.ainvoke({
            "claim":    extracted_text,
            "claims":   [],
            "evidence": [],
            "results":  [],
            "error":    None,
        })
        return format_response(result)
        
    except Exception as e:
        print(f"[OCR] Error: {e}")
        raise HTTPException(status_code=500, detail=f"OCR Error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)