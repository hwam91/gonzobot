"""
Phase 2: Interrogate Demeter AI assistant via browser automation.

Runs pre-planned conversations with the Demeter AI assistant,
capturing question-response exchanges for later content generation.
"""

import asyncio
import logging
from typing import List, Dict
from datetime import datetime

from services.browser import run_conversation

logger = logging.getLogger(__name__)


def interrogate(config: Dict, conversation_plans: List[Dict]) -> List[Dict]:
    """
    Run conversations with Demeter AI assistant based on conversation plans.

    Args:
        config: Configuration dict from config.yaml
        conversation_plans: List of conversation plans, each with:
            - topic: str
            - opening_question: str
            - follow_ups: List[str] (for Phase 1+)

    Returns:
        List of conversation transcripts, each with:
        - conversation_id: str
        - topic: str
        - exchanges: List[Dict] with 'question' and 'response'
        - timestamp: str
    """
    logger.info(f"Phase 2 (INTERROGATE): Running {len(conversation_plans)} conversations")

    url = config["demeter_ai"]["url"]
    timeout = config["demeter_ai"]["response_timeout_seconds"]
    max_conversations = config["interaction_limits"]["max_conversations_per_run"]
    max_exchanges = config["interaction_limits"]["max_exchanges_per_conversation"]

    # Limit to max conversations per run
    plans_to_run = conversation_plans[:max_conversations]

    transcripts = []

    for i, plan in enumerate(plans_to_run):
        logger.info(f"Starting conversation {i+1}/{len(plans_to_run)}: {plan['topic']}")

        # Prepare exchanges for this conversation
        # Phase 0: just the opening question
        # Phase 1+: opening question + follow-ups
        exchanges = [{"question": plan["opening_question"]}]

        # Add follow-ups if present (for Phase 1+)
        if "follow_ups" in plan and plan["follow_ups"]:
            for follow_up in plan["follow_ups"][:max_exchanges-1]:
                exchanges.append({"question": follow_up})

        # Run the conversation
        try:
            completed_exchanges = asyncio.run(run_conversation(url, exchanges, timeout))

            transcript = {
                "conversation_id": f"conv_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{i}",
                "topic": plan["topic"],
                "exchanges": completed_exchanges,
                "timestamp": datetime.now().isoformat()
            }

            transcripts.append(transcript)
            logger.info(f"Completed conversation {i+1}: {len(completed_exchanges)} exchanges")

        except Exception as e:
            logger.error(f"Failed to complete conversation {i+1}: {e}")
            # Add failed conversation with error
            transcripts.append({
                "conversation_id": f"conv_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{i}_FAILED",
                "topic": plan["topic"],
                "exchanges": [{"question": plan["opening_question"], "response": f"[FAILED: {str(e)}]"}],
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            })

    logger.info(f"Phase 2 complete: {len(transcripts)} conversations completed")
    return transcripts
