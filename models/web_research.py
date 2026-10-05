"""
=============================================================
TNEA Career Insight Navigator — Server-Side Web Research Engine
=============================================================
Controlled web research engine that provides real-time external
information retrieval without exposing API keys to the client.

Features:
  1. DuckDuckGo Instant Answer & HTML text extraction (Zero-Key universal fallback)
  2. Wikipedia API search for deep encyclopedia concepts
  3. Optional Serper / Tavily / Google Custom Search if API keys configured
  4. Query sanitization, snippet extraction, source citations with titles and URLs
=============================================================
"""

import os
import re
import json
import logging
import urllib.request
import urllib.parse
from typing import Dict, List, Any, Optional

logger = logging.getLogger("web_research")
logger.setLevel(logging.INFO)

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def _clean_html_text(html_text: str) -> str:
    """Removes HTML tags and normalizes whitespace."""
    if not html_text:
        return ""
    text = re.sub(r"<script[^>]*>.*?</script>", " ", html_text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&[a-zA-Z0-9#]+;", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def search_wikipedia(query: str, limit: int = 3) -> List[Dict[str, Any]]:
    """
    Queries Wikipedia API for factual and educational summaries.
    """
    results = []
    try:
        url = (
            "https://en.wikipedia.org/w/api.php?"
            + urllib.parse.urlencode({
                "action": "query",
                "list": "search",
                "srsearch": query,
                "format": "json",
                "srlimit": limit
            })
        )
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=8) as response:
            data = json.loads(response.read().decode("utf-8"))
            search_items = data.get("query", {}).get("search", [])
            for item in search_items:
                title = item.get("title", "")
                snippet = _clean_html_text(item.get("snippet", ""))
                page_url = f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}"
                results.append({
                    "title": title,
                    "url": page_url,
                    "snippet": snippet,
                    "source": "Wikipedia"
                })
    except Exception as e:
        logger.warning(f"Wikipedia search error for '{query}': {e}")
    return results


def search_duckduckgo(query: str, limit: int = 4) -> List[Dict[str, Any]]:
    """
    Queries DuckDuckGo for real-time web search results (Instant Answers + HTML search).
    """
    results = []
    
    # 1. DuckDuckGo Instant Answer API
    try:
        ia_url = (
            "https://api.duckduckgo.com/?"
            + urllib.parse.urlencode({
                "q": query,
                "format": "json",
                "no_html": 1,
                "skip_disambig": 1
            })
        )
        req = urllib.request.Request(ia_url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=6) as response:
            ia_data = json.loads(response.read().decode("utf-8"))
            abstract = ia_data.get("AbstractText") or ia_data.get("Abstract")
            abstract_url = ia_data.get("AbstractURL")
            heading = ia_data.get("Heading")
            if abstract:
                results.append({
                    "title": heading or f"Overview: {query}",
                    "url": abstract_url or "https://duckduckgo.com/?q=" + urllib.parse.quote(query),
                    "snippet": abstract,
                    "source": "DuckDuckGo Instant Answer"
                })
            
            # Related topics
            for topic in ia_data.get("RelatedTopics", [])[:2]:
                if isinstance(topic, dict) and topic.get("Text"):
                    results.append({
                        "title": topic.get("Text")[:60] + "...",
                        "url": topic.get("FirstURL") or "https://duckduckgo.com",
                        "snippet": topic.get("Text"),
                        "source": "DuckDuckGo"
                    })
    except Exception as e:
        logger.debug(f"DuckDuckGo Instant Answer exception: {e}")

    # 2. DuckDuckGo HTML Lite / Text Search if more results needed
    if len(results) < limit:
        try:
            html_url = "https://html.duckduckgo.com/html/?" + urllib.parse.urlencode({"q": query})
            req = urllib.request.Request(
                html_url,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
                }
            )
            with urllib.request.urlopen(req, timeout=8) as response:
                html_content = response.read().decode("utf-8", errors="ignore")
                
                # Extract results using regex on DuckDuckGo HTML Lite structure
                link_matches = re.findall(
                    r'<a[^>]+class="result__url"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
                    html_content,
                    flags=re.IGNORECASE
                )
                title_matches = re.findall(
                    r'<a[^>]+class="result__a"[^>]*href="[^"]*"[^>]*>(.*?)</a>',
                    html_content,
                    flags=re.IGNORECASE
                )
                snippet_matches = re.findall(
                    r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>',
                    html_content,
                    flags=re.IGNORECASE
                )

                for i in range(min(len(title_matches), len(snippet_matches), limit - len(results))):
                    raw_title = _clean_html_text(title_matches[i])
                    raw_snippet = _clean_html_text(snippet_matches[i])
                    raw_url = link_matches[i][0] if i < len(link_matches) else "https://duckduckgo.com/?q=" + urllib.parse.quote(query)
                    
                    if raw_url.startswith("//duckduckgo.com/l/?uddg="):
                        # Extract decoded target URL
                        parsed = urllib.parse.parse_qs(urllib.parse.urlparse("https:" + raw_url).query)
                        raw_url = parsed.get("uddg", [raw_url])[0]

                    if raw_snippet and len(raw_snippet) > 20:
                        results.append({
                            "title": raw_title or f"Result {i+1}",
                            "url": raw_url,
                            "snippet": raw_snippet,
                            "source": "Web Search"
                        })
        except Exception as e:
            logger.debug(f"DuckDuckGo HTML search exception: {e}")

    return results[:limit]


def search_tavily(query: str, api_key: str, limit: int = 4) -> List[Dict[str, Any]]:
    """Optional Tavily search integration."""
    try:
        import requests
        resp = requests.post(
            "https://api.tavily.com/search",
            json={"api_key": api_key, "query": query, "max_results": limit},
            timeout=8
        )
        if resp.status_code == 200:
            data = resp.json()
            return [
                {
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "snippet": r.get("content", ""),
                    "source": "Tavily"
                }
                for r in data.get("results", [])
            ]
    except Exception as e:
        logger.warning(f"Tavily search error: {e}")
    return []


def perform_web_research(query: str, max_results: int = 4) -> Dict[str, Any]:
    """
    Main web research execution function.
    Combines configured search providers and zero-key fallbacks.
    """
    clean_query = str(query or "").strip()
    if not clean_query:
        return {"query": "", "results": [], "total_found": 0}

    logger.info(f"Performing Web Research for query: '{clean_query}'")

    results: List[Dict[str, Any]] = []

    # 1. Check for Tavily key
    tavily_key = os.environ.get("TAVILY_API_KEY")
    if tavily_key and str(tavily_key).strip():
        results = search_tavily(clean_query, tavily_key.strip(), max_results)

    # 2. DuckDuckGo search
    if len(results) < max_results:
        ddg_results = search_duckduckgo(clean_query, limit=max_results - len(results))
        results.extend(ddg_results)

    # 3. Wikipedia if encyclopedia concept or more context needed
    if len(results) < max_results:
        wiki_results = search_wikipedia(clean_query, limit=max_results - len(results))
        results.extend(wiki_results)

    # Deduplicate results by URL
    deduped = []
    seen_urls = set()
    for r in results:
        url = r.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            deduped.append(r)

    return {
        "query": clean_query,
        "total_found": len(deduped),
        "results": deduped[:max_results]
    }
