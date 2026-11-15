"""
Web search retrieval service — no API key required.

Provider chain (tried in order):
  1. DuckDuckGo HTML scraping (requests + lxml, no JS, no API key)
  2. Wikipedia Search API       (urllib only, zero extra deps)
  3. Empty list                 (graceful fallback — LLM uses own knowledge)
"""
import logging
import re
import json
import urllib.parse
import urllib.request
from typing import List, Dict, Optional

logger = logging.getLogger("web_search")

# ── optional fast-path with requests ──────────────────────────────────────────
try:
    import requests as _requests
    _REQUESTS_OK = True
except ImportError:
    _REQUESTS_OK = False
    logger.warning("requests not installed — DuckDuckGo HTML provider disabled.")

# ── optional lxml for HTML parsing ────────────────────────────────────────────
try:
    import lxml.html as _lxml_html
    _LXML_OK = True
except ImportError:
    _LXML_OK = False
    logger.warning("lxml not installed — DuckDuckGo HTML provider disabled.")


# ══════════════════════════════════════════════════════════════════════════════
#  Helpers
# ══════════════════════════════════════════════════════════════════════════════

def _strip_html(text: str) -> str:
    """Remove HTML tags and decode common HTML entities."""
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace(
        "&gt;", ">").replace("&quot;", '"').replace("&#39;", "'").replace("&nbsp;", " ")
    return text.strip()


# ══════════════════════════════════════════════════════════════════════════════
#  Provider 1 — DuckDuckGo HTML (no JS, POST to html.duckduckgo.com)
# ══════════════════════════════════════════════════════════════════════════════

def _ddg_html_search(query: str, max_results: int) -> List[Dict[str, str]]:
    """
    POST the full query to DuckDuckGo's plain-HTML endpoint and parse results
    with lxml xpath.  No API key, no JavaScript needed.
    """
    if not (_REQUESTS_OK and _LXML_OK):
        return []

    url = "https://html.duckduckgo.com/html/"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {"q": query, "b": "", "kl": "us-en"}

    try:
        resp = _requests.post(url, data=data, headers=headers, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        logger.warning(f"DuckDuckGo HTML request failed: {e}")
        return []

    try:
        tree = _lxml_html.fromstring(resp.text)
    except Exception as e:
        logger.warning(f"lxml parse failed: {e}")
        return []

    results: List[Dict[str, str]] = []

    # Each result lives inside  <div class="result ...">
    result_divs = tree.xpath('//div[contains(@class,"result") and not(contains(@class,"result--more"))]')

    for div in result_divs:
        if len(results) >= max_results:
            break

        # ── Title + link ──────────────────────────────────────────────────
        title_nodes = div.xpath('.//a[contains(@class,"result__a")]')
        if not title_nodes:
            continue
        title_node = title_nodes[0]
        title = _strip_html(title_node.text_content())
        raw_href = title_node.get("href", "")

        # DDG wraps links in a redirect — extract the real URL
        href = _extract_ddg_url(raw_href)
        if not href:
            continue

        # Skip DDG internal pages
        if "duckduckgo.com" in href and "/y.js" not in href:
            continue

        # ── Snippet ───────────────────────────────────────────────────────
        snippet_nodes = div.xpath('.//a[contains(@class,"result__snippet")]')
        if not snippet_nodes:
            snippet_nodes = div.xpath('.//*[contains(@class,"result__snippet")]')
        body = _strip_html(snippet_nodes[0].text_content()) if snippet_nodes else ""

        if title and href:
            results.append({"title": title, "href": href, "body": body})

    logger.info(f"DuckDuckGo HTML returned {len(results)} results for: {query!r}")
    return results


def _extract_ddg_url(raw: str) -> str:
    """
    DDG HTML wraps real URLs in a redirect like:
      //duckduckgo.com/l/?uddg=https%3A%2F%2F...
    Extract the actual destination URL.
    """
    if not raw:
        return ""
    # Relative DDG redirect
    if raw.startswith("//duckduckgo.com/l/"):
        parsed = urllib.parse.urlparse("https:" + raw)
        qs = urllib.parse.parse_qs(parsed.query)
        return qs.get("uddg", [raw])[0]
    if raw.startswith("/l/?"):
        parsed = urllib.parse.urlparse("https://duckduckgo.com" + raw)
        qs = urllib.parse.parse_qs(parsed.query)
        return qs.get("uddg", [raw])[0]
    return raw


# ══════════════════════════════════════════════════════════════════════════════
#  Provider 2 — Wikipedia Search API (stdlib only)
# ══════════════════════════════════════════════════════════════════════════════

def _wikipedia_search(query: str, max_results: int) -> List[Dict[str, str]]:
    """
    Use Wikipedia's public REST search API — no API key, pure urllib.
    Returns list of {title, href, body}.
    """
    encoded = urllib.parse.quote_plus(query)
    api_url = (
        f"https://en.wikipedia.org/w/api.php"
        f"?action=query&list=search&srsearch={encoded}"
        f"&srlimit={max_results}&format=json&utf8=1"
    )
    try:
        req = urllib.request.Request(
            api_url,
            headers={"User-Agent": "LangChainChatbot/1.0 (educational project)"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        logger.warning(f"Wikipedia search API failed: {e}")
        return []

    results: List[Dict[str, str]] = []
    for item in data.get("query", {}).get("search", []):
        title = item.get("title", "")
        snippet = _strip_html(item.get("snippet", ""))
        slug = title.replace(" ", "_")
        href = f"https://en.wikipedia.org/wiki/{urllib.parse.quote(slug)}"
        if title:
            results.append({"title": title, "href": href, "body": snippet})

    logger.info(f"Wikipedia returned {len(results)} results for: {query!r}")
    return results


# ══════════════════════════════════════════════════════════════════════════════
#  Provider 3 — DuckDuckGo Instant Answer API (bonus, usually sparse)
# ══════════════════════════════════════════════════════════════════════════════

def _ddg_instant_answer(query: str) -> List[Dict[str, str]]:
    """
    DuckDuckGo Instant Answer (zero-click) API — good for entities/facts.
    Returns 0–1 results.
    """
    encoded = urllib.parse.quote_plus(query)
    api_url = f"https://api.duckduckgo.com/?q={encoded}&format=json&no_html=1&skip_disambig=1"
    try:
        req = urllib.request.Request(
            api_url,
            headers={"User-Agent": "LangChainChatbot/1.0"},
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        logger.warning(f"DDG Instant Answer API failed: {e}")
        return []

    abstract = data.get("AbstractText", "").strip()
    source_url = data.get("AbstractURL", "").strip()
    source = data.get("AbstractSource", "DuckDuckGo").strip()

    if abstract and source_url:
        return [{"title": source, "href": source_url, "body": abstract}]
    return []


# ══════════════════════════════════════════════════════════════════════════════
#  Main Service
# ══════════════════════════════════════════════════════════════════════════════

class WebSearchService:
    """
    Retrieves live web search results using a multi-provider fallback chain.
    No API key required.
    """

    def __init__(self, max_results: int = 5):
        self.max_results = max_results

    def search(self, query: str, max_results: Optional[int] = None) -> List[Dict[str, str]]:
        """
        Search the web for `query` and return up to `max_results` hits.

        Return format:
          [ { "title": str, "href": str, "body": str }, ... ]
        """
        limit = max_results or self.max_results
        clean_query = query.strip()
        if not clean_query:
            return []

        logger.info(f"Web search requested: {clean_query!r}")

        # ── Provider 1: DuckDuckGo HTML ────────────────────────────────────
        results = _ddg_html_search(clean_query, limit)
        if results:
            return results[:limit]

        logger.info("DDG HTML gave no results, trying Wikipedia…")

        # ── Provider 2: Wikipedia Search API ──────────────────────────────
        results = _wikipedia_search(clean_query, limit)
        if results:
            # Supplement with DDG Instant Answer if Wikipedia found something
            instant = _ddg_instant_answer(clean_query)
            combined = instant + results
            return combined[:limit]

        logger.info("Wikipedia gave no results, trying DDG Instant Answer…")

        # ── Provider 3: DDG Instant Answer alone ──────────────────────────
        results = _ddg_instant_answer(clean_query)
        if results:
            return results[:limit]

        logger.warning(f"All search providers returned no results for: {clean_query!r}")
        return []

    # ── Formatting helpers (unchanged API so chatbot.py needs no edits) ───

    def format_search_context(self, search_results: List[Dict[str, str]]) -> str:
        """Format raw search results into an LLM-readable context block."""
        if not search_results:
            return "No relevant web search results found."

        lines = []
        for idx, res in enumerate(search_results, start=1):
            title = res.get("title", "Untitled")
            body  = res.get("body",  "")
            url   = res.get("href",  "")
            lines.append(
                f"[{idx}] Title: {title}\n"
                f"    Snippet: {body}\n"
                f"    Source: {url}"
            )
        return "\n\n".join(lines)

    def format_sources_markdown(self, search_results: List[Dict[str, str]]) -> str:
        """Generate a markdown footer with clickable source links."""
        if not search_results:
            return ""

        md = ["\n\n---\n**🌐 Sources & References:**\n"]
        for idx, res in enumerate(search_results, start=1):
            title = res.get("title", "Link")
            url   = res.get("href",  "#")
            md.append(f"{idx}. [{title}]({url})")
        return "\n".join(md)


# Singleton — imported by chatbot.py as:  from app.search import web_search_service
web_search_service = WebSearchService()
