#!/usr/bin/env python3
"""
Gonzo Bot Orchestrator

Main entry point for the autonomous content engine.
Runs all phases in sequence:
1. Scan for news (stub in Phase 0)
2. Interrogate Demeter AI
3. Generate content with Claude API
4. Publish (stub in Phase 0 - saves to output/)
5. Log results

Usage:
    python orchestrator.py
"""

import sys
import logging
from datetime import datetime
from pathlib import Path
import yaml
from dotenv import load_dotenv

# Import phases
from phases.scan import scan_news
from phases.interrogate import interrogate
from phases.generate import generate
from phases.log import log_run

# Import services
from services.publishing import publish


def setup_logging():
    """Configure logging for the orchestrator."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )


def load_config(config_path: str = "config.yaml") -> dict:
    """Load configuration from YAML file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def load_coverage_manifest(manifest_path: str = "coverage_manifest.yaml") -> dict:
    """Load coverage manifest from YAML file."""
    with open(manifest_path, 'r') as f:
        return yaml.safe_load(f)


def main():
    """Main orchestrator function."""
    # Load environment variables from .env file
    load_dotenv()

    logger = logging.getLogger(__name__)

    logger.info("="*80)
    logger.info("GONZO BOT - Phase 1")
    logger.info("="*80)

    # Generate run ID
    run_id = datetime.now().strftime("%Y-%m-%d-%H%M")
    logger.info(f"Run ID: {run_id}")

    try:
        # Load configuration
        logger.info("\n[SETUP] Loading configuration...")
        config = load_config()
        coverage_manifest = load_coverage_manifest()
        logger.info("Configuration loaded successfully")

        # Load recent logs for context
        from phases.log import load_recent_logs
        recent_logs = load_recent_logs(config, num_recent=7)
        recent_topics = [
            t.get('topic', '')
            for log in recent_logs
            for t in log.get('transcripts', [])
            if t.get('topic')
        ]

        # PHASE 1: Scan for news
        logger.info("\n[PHASE 1] Scanning for news...")
        scan_results = scan_news(config, coverage_manifest)
        logger.info(f"Scan complete: {len(scan_results)} items found")

        # PHASE 1.5: Generate conversation plans with Claude API
        logger.info("\n[PHASE 1.5] Generating conversation plans...")
        from services.claude_api import ClaudeAPI
        api = ClaudeAPI()
        num_conversations = min(
            config.get('interaction_limits', {}).get('max_conversations_per_run', 5),
            config.get('output', {}).get('daily_minimum', {}).get('linkedin', 1) +
            config.get('output', {}).get('daily_minimum', {}).get('twitter', 2)
        )

        conversation_plans = api.generate_questions(
            config=config,
            coverage_manifest=coverage_manifest,
            scan_results=scan_results,
            recent_topics=recent_topics,
            num_conversations=num_conversations
        )
        logger.info(f"Generated {len(conversation_plans)} conversation plans")

        # PHASE 2: Interrogate Demeter AI
        logger.info("\n[PHASE 2] Interrogating Demeter AI...")
        transcripts = interrogate(config, conversation_plans)
        logger.info(f"Interrogation complete: {len(transcripts)} conversations")

        # Check if we got any valid responses
        if not transcripts or all(
            "FAILED" in t.get("conversation_id", "") or
            "[ERROR" in str(t.get("exchanges", [{}])[0].get("response", ""))
            for t in transcripts
        ):
            logger.warning("No valid transcripts obtained. Skipping content generation.")
            return

        # PHASE 2.5: Assess response quality
        logger.info("\n[PHASE 2.5] Assessing response quality...")
        assessments = api.assess_responses(transcripts)
        logger.info(f"Assessment complete: {assessments.get('summary', {}).get('high_quality', 0)} high-quality conversations")

        # PHASE 3: Generate content
        logger.info("\n[PHASE 3] Generating content...")
        posts = generate(config, transcripts, run_id, assessments)
        logger.info(f"Content generation complete: {len(posts)} posts")

        # PHASE 4a: Publish (stub - saves to output/)
        logger.info("\n[PHASE 4a] Publishing...")
        publishing_summary = publish(posts, config, run_id)
        logger.info(f"Publishing complete: {publishing_summary['successful']} posts")

        # PHASE 4b: Log
        logger.info("\n[PHASE 4b] Logging run...")
        log_file = log_run(run_id, config, scan_results, transcripts, posts, publishing_summary, assessments)
        logger.info(f"Log written to: {log_file}")

        # Summary
        logger.info("\n" + "="*80)
        logger.info("RUN COMPLETE")
        logger.info("="*80)
        logger.info(f"Run ID: {run_id}")
        logger.info(f"Conversations: {len(transcripts)}")
        logger.info(f"Posts generated: {len(posts)}")
        logger.info(f"Posts published: {publishing_summary['successful']}")
        logger.info(f"Output directory: output/")
        logger.info(f"Log file: {log_file}")
        logger.info("="*80)

    except KeyboardInterrupt:
        logger.info("\nRun interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\nRun failed with error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    setup_logging()
    main()
