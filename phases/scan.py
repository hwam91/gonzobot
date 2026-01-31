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

        # Search for each query
        with DDGS() as ddgs:
            for query in queries[:5]:  # Limit to 5 queries to avoid rate limits
                logger.info(f"Searching: {query}")
                try:
                    # Search news from past week
                    search_results = list(ddgs.text(
                        query,
                        region='wt-wt',
                        safesearch='moderate',
                        max_results=3
                    ))

                    for result in search_results:
                        results.append({
                            "source": result.get('source', 'Unknown'),
                            "headline": result.get('title', 'No title'),
                            "summary": result.get('body', ''),
                            "url": result.get('href', ''),
                            "date": datetime.now().isoformat(),
                            "query": query
                        })

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
    queries = []

    # Get tier 1 regions (strongest coverage)
    tier_1 = coverage_manifest.get('geographic_coverage', {}).get('tier_1_strong', {})
    regions = tier_1.get('regions', [])

    # Build queries for each region + key crops
    for region in regions[:3]:  # Top 3 regions
        region_name = region.get('name', '')
        crops = region.get('crops_mapped', [])

        if region_name and crops:
            # Query format: "Region crop news"
            for crop in crops[:2]:  # Top 2 crops per region
                queries.append(f"{region_name} {crop} production news")

    # Add general agricultural queries
    queries.extend([
        "almond production 2025",
        "olive oil production trends",
        "California water agriculture",
        "climate change agriculture",
        "irrigation technology news"
    ])

    return queries
