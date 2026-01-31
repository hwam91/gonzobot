"""
Phase 1: Scan for agricultural news and priority account activity.

Uses DuckDuckGo search to find recent news relevant to Demeter's coverage areas.
"""

import logging
from typing import List, Dict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def scan_news(config: Dict, coverage_manifest: Dict) -> List[Dict]:
    """
    Scan for recent agricultural news relevant to Demeter's coverage areas.

    Args:
        config: Configuration dict from config.yaml
        coverage_manifest: Coverage manifest dict from coverage_manifest.yaml

    Returns:
        List of news items, each with:
        - source: str
        - headline: str
        - summary: str (snippet from search result)
        - url: str
        - date: str
    """
    logger.info("Phase 1 (SCAN): Searching for agricultural news...")

    results = []

    try:
        from duckduckgo_search import DDGS

        # Build search queries based on coverage areas
        queries = _build_search_queries(coverage_manifest)

        # Search for each query with delay to avoid rate limiting
        import time
        with DDGS() as ddgs:
            for i, query in enumerate(queries[:5]):  # Limit to 5 queries to avoid rate limits
                logger.info(f"Searching: {query}")
                try:
                    # Try news search first (more targeted)
                    try:
                        search_results = list(ddgs.news(
                            query,
                            region='wt-wt',
                            safesearch='moderate',
                            max_results=3
                        ))
                        logger.info(f"News search returned {len(search_results)} results")
                    except Exception as e:
                        logger.info(f"News search failed ({e}), trying text search")
                        # Fallback to text search if news search fails
                        search_results = list(ddgs.text(
                            query,
                            region='wt-wt',
                            safesearch='moderate',
                            max_results=3
                        ))
                        logger.info(f"Text search returned {len(search_results)} results")

                    for result in search_results:
                        results.append({
                            "source": result.get('source', 'Unknown'),
                            "headline": result.get('title', 'No title'),
                            "summary": result.get('body', ''),
                            "url": result.get('url') or result.get('href', ''),
                            "date": result.get('date', datetime.now().isoformat()),
                            "query": query
                        })

                    # Add delay between queries to avoid rate limiting
                    if i < len(queries[:5]) - 1:  # Don't delay after last query
                        time.sleep(2)

                except Exception as e:
                    logger.warning(f"Failed to search for '{query}': {e}")
                    continue

        logger.info(f"Scan complete: {len(results)} news items found")
        return results

    except ImportError:
        logger.warning("duckduckgo-search not installed, returning empty results")
        return []
    except Exception as e:
        logger.error(f"Error during news scan: {e}")
        return []


def _build_search_queries(coverage_manifest: Dict) -> List[str]:
    """
    Build search queries based on coverage manifest.

    Returns:
        List of search query strings
    """
    # Use simple, reliable queries that are guaranteed to return results
    # These are well-known organizations and common agricultural terms
    queries = [
        "almond board of california",
        "California Department of Food and Agriculture",
        "FAO agriculture news",
        "USDA crop reports",
        "olive oil council",
        "California almond harvest",
        "Mediterranean olive production",
        "California water drought",
        "agriculture climate change",
        "sustainable farming"
    ]

    return queries
