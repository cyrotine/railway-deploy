import asyncio
import re

# Shared Semaphore to stop complete paralellism
api_semaphore = asyncio.Semaphore(1)

async def _call_gemini_with_retry(model, prompt, max_retries=4):
    """Helper to call Gemini with a semaphore and proper 429 delay handling."""
    for attempt in range(max_retries):
        try:
            async with api_semaphore:
                # Minimum spacing
                await asyncio.sleep(1.0)
                def _do_call():
                    return model.generate_content(prompt).text
                return await asyncio.to_thread(_do_call)
        except Exception as e:
            error_msg = str(e)
            
            # Check if Google's telling us exactly how long to wait
            delay_match = re.search(r'delay\s*\{\s*seconds:\s*(\d+)\s*\}', error_msg)
            
            if attempt == max_retries - 1:
                raise e
                
            if delay_match:
                wait_sec = int(delay_match.group(1)) + 1
                print(f"[Gemini] Quota hit (Wait requested: {wait_sec}s). Attempt {attempt+1}/{max_retries}")
                await asyncio.sleep(wait_sec)
            elif "429" in error_msg or "quota" in error_msg.lower():
                wait_sec = 10 * (attempt + 1)
                print(f"[Gemini] 429 hit. Sleeping {wait_sec}s. Attempt {attempt+1}/{max_retries}")
                await asyncio.sleep(wait_sec)
            else:
                # Hard error, not a quota issue
                raise e
