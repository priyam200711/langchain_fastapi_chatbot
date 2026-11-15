"""
Quick smoke-test for the new multi-provider web search service.
Run:  python test_search.py
"""
import sys
import logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")

# Make sure the app package resolves correctly
sys.path.insert(0, ".")

from app.search import (
    web_search_service,
    _ddg_html_search,
    _wikipedia_search,
    _ddg_instant_answer,
)

QUERIES = [
    "how many ICC tournaments has India won",
    "who invented the telephone",
    "latest Python version 2024",
]

SEPARAOR = "─" * 70


def test_provider(name, fn, query, **kwargs):
    print(f"\n{'=' * 70}")
    print(f"  Provider : {name}")
    print(f"  Query    : {query!r}")
    print(f"{'=' * 70}")
    try:
        results = fn(query, **kwargs) if kwargs else fn(query)
        if not results:
            print("  ⚠️  No results returned.")
        for i, r in enumerate(results, 1):
            print(f"\n  [{i}] {r.get('title','')}")
            print(f"      URL  : {r.get('href','')}")
            print(f"      Body : {r.get('body','')[:120]}…")
    except Exception as exc:
        print(f"  ❌ Error: {exc}")


def main():
    q = QUERIES[0]

    # Individual provider tests
    test_provider("DuckDuckGo HTML", _ddg_html_search, q, max_results=5)
    test_provider("Wikipedia API",   _wikipedia_search, q, max_results=5)
    test_provider("DDG Instant Answer", _ddg_instant_answer, q)

    # Full service (uses fallback chain)
    print(f"\n{'=' * 70}")
    print("  Full WebSearchService (fallback chain)")
    print(f"{'=' * 70}")
    for query in QUERIES:
        print(f"\n--- Query: {query!r}")
        results = web_search_service.search(query, max_results=5)
        if not results:
            print("  ⚠️  No results.")
            continue
        for i, r in enumerate(results, 1):
            print(f"  [{i}] {r['title']}")
            print(f"       {r['href']}")
            print(f"       {r['body'][:100]}…")
        print()
        # Also show the formatted context (what the LLM will see)
        ctx = web_search_service.format_search_context(results)
        print("  LLM context preview (first 400 chars):")
        print("  " + ctx[:400].replace("\n", "\n  "))


if __name__ == "__main__":
    main()
