"""
Phase 1: Scan for agricultural news and priority account activity.

For Phase 0, this is a STUB that returns empty results.
Phase 1 will implement real web search using DuckDuckGo.
"""

import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


def scan_news(config: Dict, coverage_manifest: Dict) -> List[Dict]:
    """
    Scan for recent agricultural news relevant to Demeter's coverage areas.

    STUB: Returns empty list for Phase 0.

    Args:
        config: Configuration dict from config.yaml
        coverage_manifest: Coverage manifest dict from coverage_manifest.yaml

    Returns:
        List of news items, each with:
        - source: str
        - headline: str
        - summary: str
        - url: str
        - date: str
    """
    logger.info("Phase 1 (SCAN): Running stub - returning empty results")
    return []
