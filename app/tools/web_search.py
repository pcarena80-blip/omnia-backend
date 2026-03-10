"""
Web Search Tool
Searches the internet using Tavily API (optimized for AI agents).
Fallback to basic DuckDuckGo scraping if Tavily unavailable.
"""
import logging
from typing import Optional
import httpx
from app.config import settings

logger = logging.getLogger(__name__)


async def web_search(
    query: str,
    max_results: int = 5,
    search_depth: str = "basic",
) -> dict:
    """
    Search the web for information.

    Args:
        query: Search query string
        max_results: Maximum number of results to return
        search_depth: "basic" or "advanced" (advanced includes page content)

    Returns:
        dict with 'results' list containing title, url, content for each result
    """
    if settings.tavily_api_key:
        return await _search_tavily(query, max_results, search_depth)
    else:
        return await _search_duckduckgo(query, max_results)


async def _search_tavily(
    query: str, max_results: int, search_depth: str
) -> dict:
    """Search using Tavily API."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": settings.tavily_api_key,
                    "query": query,
                    "max_results": max_results,
                    "search_depth": search_depth,
                    "include_answer": True,
                },
                timeout=15.0,
            )
            response.raise_for_status()
            data = response.json()

            return {
                "answer": data.get("answer", ""),
                "results": [
                    {
                        "title": r.get("title", ""),
                        "url": r.get("url", ""),
                        "content": r.get("content", ""),
                        "score": r.get("score", 0),
                    }
                    for r in data.get("results", [])
                ],
            }
    except Exception as e:
        logger.error(f"Tavily search error: {e}")
        return {"answer": "", "results": [], "error": str(e)}


async def _search_duckduckgo(query: str, max_results: int) -> dict:
    """Fallback search using DuckDuckGo (no API key needed)."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.duckduckgo.com/",
                params={"q": query, "format": "json", "no_html": 1},
                timeout=10.0,
            )
            data = response.json()

            results = []
            # Abstract (instant answer)
            if data.get("Abstract"):
                results.append({
                    "title": data.get("Heading", ""),
                    "url": data.get("AbstractURL", ""),
                    "content": data.get("Abstract", ""),
                    "score": 1.0,
                })

            # Related topics
            for topic in data.get("RelatedTopics", [])[:max_results]:
                if isinstance(topic, dict) and "Text" in topic:
                    results.append({
                        "title": topic.get("Text", "")[:80],
                        "url": topic.get("FirstURL", ""),
                        "content": topic.get("Text", ""),
                        "score": 0.5,
                    })

            return {"answer": data.get("Abstract", ""), "results": results}
    except Exception as e:
        logger.error(f"DuckDuckGo search error: {e}")
        return {"answer": "", "results": [], "error": str(e)}
