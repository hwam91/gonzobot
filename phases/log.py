"""
Phase 4: Logging and persistent state management.

Writes run logs to JSON files and maintains persistent state across runs.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)


def log_run(
    run_id: str,
    config: Dict,
    scan_results: List[Dict],
    transcripts: List[Dict],
    posts: List[Dict],
    publishing_summary: Dict,
    assessments: Dict = None
) -> str:
    """
    Log a complete run to JSON file.

    Args:
        run_id: Unique run identifier
        config: Configuration dict
        scan_results: Results from scan phase
        transcripts: Conversation transcripts from interrogate phase
        posts: Generated posts from generate phase
        publishing_summary: Publishing results summary
        assessments: Optional assessment results from response assessment

    Returns:
        Path to the log file
    """
    logger.info(f"Phase 4 (LOG): Writing run log for {run_id}")

    # Prepare log data
    log_data = {
        "run_id": run_id,
        "timestamp": datetime.now().isoformat(),
        "config_snapshot": {
            "format_mix": config.get("format_mix", {}),
            "active_experiment": config.get("active_experiment"),
            "interaction_limits": config.get("interaction_limits", {})
        },
        "scan_results": scan_results,
        "transcripts": transcripts,
        "assessments": assessments,
        "posts": posts,
        "publishing_summary": publishing_summary,
        "stats": {
            "num_scans": len(scan_results),
            "num_conversations": len(transcripts),
            "num_posts": len(posts),
            "posts_by_channel": _count_by_channel(posts),
            "posts_by_format": _count_by_format(posts)
        }
    }

    # Write to log file
    log_dir = Path(config.get("logging", {}).get("runs_dir", "logs/runs"))
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / f"{run_id}.json"
    with open(log_file, 'w') as f:
        json.dump(log_data, f, indent=2)

    logger.info(f"Run log written to {log_file}")
    return str(log_file)


def _count_by_channel(posts: List[Dict]) -> Dict[str, int]:
    """Count posts by channel."""
    counts = {}
    for post in posts:
        channel = post.get("channel", "unknown")
        counts[channel] = counts.get(channel, 0) + 1
    return counts


def _count_by_format(posts: List[Dict]) -> Dict[str, int]:
    """Count posts by format type."""
    counts = {}
    for post in posts:
        format_type = post.get("format_type", "unknown")
        counts[format_type] = counts.get(format_type, 0) + 1
    return counts


def load_recent_logs(config: Dict, num_recent: int = 7) -> List[Dict]:
    """
    Load recent run logs for context in future runs.

    Args:
        config: Configuration dict
        num_recent: Number of recent logs to load

    Returns:
        List of recent log data dicts
    """
    log_dir = Path(config.get("logging", {}).get("runs_dir", "logs/runs"))

    if not log_dir.exists():
        return []

    # Get all log files sorted by modification time (most recent first)
    log_files = sorted(log_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)

    recent_logs = []
    for log_file in log_files[:num_recent]:
        try:
            with open(log_file, 'r') as f:
                recent_logs.append(json.load(f))
        except Exception as e:
            logger.warning(f"Could not load log {log_file}: {e}")

    return recent_logs
