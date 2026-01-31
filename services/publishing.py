"""
Publishing service for pushing content to Typefully/Buffer.

For Phase 0, this is a STUB that prints output to console and saves to files.
Phase 2 will implement real Typefully API integration.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict

logger = logging.getLogger(__name__)


def publish(posts: List[Dict], config: Dict, run_id: str) -> Dict:
    """
    Publish posts to the configured service.

    STUB: For Phase 0, prints to console and saves to output/ directory.

    Args:
        posts: List of posts to publish, each with channel, copy, chart_path
        config: Configuration dict
        run_id: Unique run identifier

    Returns:
        Publishing summary with status for each post
    """
    logger.info(f"Phase 4 (PUBLISH - STUB): Processing {len(posts)} posts")

    output_dir = Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)

    results = []

    for i, post in enumerate(posts):
        logger.info(f"\n{'='*60}")
        logger.info(f"POST {i+1}/{len(posts)} - {post.get('channel', 'unknown').upper()}")
        logger.info(f"{'='*60}")
        logger.info(f"Format: {post.get('format_type', 'unknown')}")
        logger.info(f"\nCopy:\n{post.get('copy', '')}")

        if post.get('chart_path'):
            logger.info(f"\nChart: {post['chart_path']}")

        logger.info(f"{'='*60}\n")

        # Save post to JSON file
        post_file = output_dir / f"{run_id}_post_{i+1}.json"
        with open(post_file, 'w') as f:
            json.dump(post, f, indent=2)

        results.append({
            "post_index": i,
            "status": "saved_to_file",
            "file": str(post_file),
            "channel": post.get('channel'),
            "has_chart": bool(post.get('chart_path'))
        })

    summary = {
        "total_posts": len(posts),
        "successful": len(results),
        "failed": 0,
        "results": results
    }

    logger.info(f"Published {len(results)} posts (saved to output/ directory)")
    return summary
