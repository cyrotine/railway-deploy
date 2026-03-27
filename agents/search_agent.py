import asyncio
import aiohttp
import trafilatura
import re
import logging
from config import TAVILY_API_KEY

logging.getLogger("trafilatura").setLevel(logging.CRITICAL)


def is_junk_content(text: str) -> bool:
    if not text:
        return True
    junk_triggers = [
        "403 forbidden", "404 not found", "access denied",
        "enable javascript", "checking your browser",
        "bot detection", "cloudflare", "security check"
    ]
    lowered = text.lower().strip()
    return any(t in lowered for t in junk_triggers) or len(lowered) < 100


def extract_relevant_context(article_text: str, claim: str) -> str:
    if not article_text:
        return ""
    stopwords = {
        "is","are","am","the","a","an","in","on","at",
        "for","to","of","and","or","during","it","this","that"
    }
    clean = re.sub(r'[^\w\s]', '', claim)
    keywords = {w.lower() for w in clean.split() if w.lower() not in stopwords}

    sentences = re.split(r'(?<=[.!?])\s+|\n+', article_text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 15]

    scored = []
    for i, s in enumerate(sentences):
        words = set(re.findall(r'\w+', s.lower()))
        score = len(keywords & words)
        if score > 0:
            scored.append((score, i, s))

    if not scored:
        return article_text[:300] + "..."

    top = sorted(scored, key=lambda x: x[0], reverse=True)[:3]
    top.sort(key=lambda x: x[1])
    result = " ".join(s[2] for s in top)
    return result[:497] + "..." if len(result) > 500 else result


async def _extract_article(session: aiohttp.ClientSession, url: str) -> str:
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.8"
        }
        async with session.get(
            url, headers=headers,
            timeout=aiohttp.ClientTimeout(total=10)
        ) as r:
            html = await r.text()
            text = trafilatura.extract(html)
            return text or ""
    except Exception:
        return ""


async def _search_one_claim(session: aiohttp.ClientSession, claim: str) -> list:
    url = "https://api.tavily.com/search"
    payload = {
        "api_key": TAVILY_API_KEY,
        "query": claim,
        "search_depth": "basic",
        "max_results": 10
    }
    try:
        async with session.post(url, json=payload) as resp:
            if resp.status != 200:
                print(f"[Search] Tavily error {resp.status}")
                return []
            data = await resp.json()
            hits = data.get("results", [])

        tasks = [_extract_article(session, h["url"]) for h in hits]
        scraped = await asyncio.gather(*tasks)

        valid = []
        for i, raw in enumerate(scraped):
            if is_junk_content(raw):
                continue
            distilled = extract_relevant_context(raw, claim)
            if distilled.strip():
                valid.append({
                    "title":           hits[i].get("title"),
                    "source":          hits[i].get("url", "").split("/")[2],
                    "url":             hits[i].get("url"),
                    "article_content": distilled
                })
            if len(valid) == 4:
                break
        return valid
    except Exception as e:
        print(f"[Search] Error: {e}")
        return []


def search_agent(state: dict) -> dict:
    claims = state.get("claims", [state.get("claim", "")])

    async def run_all():
        async with aiohttp.ClientSession() as session:
            tasks = [_search_one_claim(session, c) for c in claims]
            return await asyncio.gather(*tasks)

    all_evidence = asyncio.run(run_all())
    flat_evidence = [ev for sublist in all_evidence for ev in sublist]

    print(f"[Search] 🔍 Found {len(flat_evidence)} total evidence item(s)")
    return {**state, "evidence": flat_evidence}