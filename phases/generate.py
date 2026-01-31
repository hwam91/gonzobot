"""
Phase 3: Generate social media content from conversation transcripts.

Uses Claude API to turn Demeter AI conversation transcripts into
channel-ready posts with chart specifications.
"""

import logging
from typing import List, Dict
from pathlib import Path

from services.claude_api import ClaudeAPI
from services.charts import generate_chart

logger = logging.getLogger(__name__)


def generate(config: Dict, transcripts: List[Dict], run_id: str, assessments: Dict = None) -> List[Dict]:
    """
    Generate social media content from conversation transcripts.

    Args:
        config: Configuration dict from config.yaml
        transcripts: List of conversation transcripts from interrogate phase
        run_id: Unique run identifier for naming output files
        assessments: Optional assessment results from response assessment phase

    Returns:
        List of posts ready for publishing, each with:
        - channel: str
        - copy: str
        - format_type: str
        - chart_path: str (if chart was generated)
    """
    logger.info(f"Phase 3 (GENERATE): Generating content from {len(transcripts)} transcripts")

    # Load the content writer prompt
    prompt_path = Path(__file__).parent.parent / "prompts" / "content_writer.txt"
    try:
        with open(prompt_path, 'r') as f:
            prompt_template = f.read()
    except FileNotFoundError:
        logger.error(f"Prompt template not found at {prompt_path}")
        raise

    # Initialize Claude API
    api = ClaudeAPI()
    model = config.get("claude_api", {}).get("models", {}).get("content_writing", "claude-sonnet-4-20250514")

    # Filter transcripts based on assessments (if available)
    transcripts_to_process = transcripts
    if assessments and 'assessments' in assessments:
        # Only process high-quality conversations (overall_score >= 6)
        assessment_map = {a['conversation_id']: a for a in assessments['assessments']}
        transcripts_to_process = [
            t for t in transcripts
            if t.get('conversation_id') in assessment_map
            and assessment_map[t['conversation_id']].get('suitable_for_content', False)
        ]
        logger.info(f"Filtered to {len(transcripts_to_process)} high-quality transcripts based on assessments")

    all_posts = []

    # Process each transcript
    for i, transcript in enumerate(transcripts_to_process):
        logger.info(f"Generating content for transcript {i+1}/{len(transcripts)}: {transcript.get('topic', 'Unknown')}")

        try:
            # Call Claude API to generate content
            result = api.generate_content(
                transcript=transcript,
                config=config,
                prompt_template=prompt_template,
                model=model
            )

            # Process posts from the result
            posts = result.get("posts", [])

            for j, post in enumerate(posts):
                # Generate chart if spec is present
                if "chart" in post and post["chart"]:
                    logger.info(f"Generating chart for post {j+1}")
                    try:
                        chart_path = generate_chart(
                            chart_spec=post["chart"],
                            config=config,
                            output_name=f"{run_id}_{i}_{j}"
                        )
                        post["chart_path"] = chart_path
                        logger.info(f"Chart saved to {chart_path}")
                    except Exception as e:
                        logger.error(f"Failed to generate chart: {e}")
                        post["chart_path"] = None

                all_posts.append(post)

        except Exception as e:
            logger.error(f"Failed to generate content for transcript {i+1}: {e}")
            continue

    logger.info(f"Phase 3 complete: Generated {len(all_posts)} posts")
    return all_posts
