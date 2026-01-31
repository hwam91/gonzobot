"""
Claude API wrapper for Gonzo Bot.

Handles API calls to Anthropic's Claude for:
- Content generation (turning transcripts into posts)
- Question generation (Phase 1+)
- Response assessment (Phase 1+)
- Weekly synthesis (Phase 1+)
"""

import os
import logging
from typing import Dict, List, Optional
import anthropic

logger = logging.getLogger(__name__)


class ClaudeAPI:
    """Wrapper for Anthropic Claude API calls."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Claude API client.

        Args:
            api_key: Anthropic API key. If None, reads from ANTHROPIC_API_KEY env var
        """
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment or constructor")

        self.client = anthropic.Anthropic(api_key=self.api_key)

    def generate_content(
        self,
        transcript: Dict,
        config: Dict,
        prompt_template: str,
        model: str = "claude-sonnet-4-20250514"
    ) -> Dict:
        """
        Generate social media content from a conversation transcript.

        Args:
            transcript: Conversation transcript with exchanges
            config: Configuration dict
            prompt_template: Prompt template content
            model: Claude model to use

        Returns:
            Generated content structure with posts and chart specs
        """
        logger.info(f"Generating content with {model}")

        # Build the prompt
        prompt = self._build_content_prompt(transcript, config, prompt_template)

        try:
            response = self.client.messages.create(
                model=model,
                max_tokens=4096,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            # Extract the text content
            content_text = response.content[0].text

            # Parse the JSON response
            import json
            try:
                result = json.loads(content_text)
            except json.JSONDecodeError:
                # If response isn't pure JSON, try to extract JSON from markdown code blocks
                import re
                json_match = re.search(r'```json\s*(.*?)\s*```', content_text, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group(1))
                else:
                    # Fallback: create a simple post
                    logger.warning("Could not parse JSON from response, creating fallback")
                    result = {
                        "posts": [{
                            "channel": "linkedin",
                            "copy": content_text[:3000],
                            "format_type": "data_snippet"
                        }]
                    }

            logger.info(f"Generated {len(result.get('posts', []))} posts")
            return result

        except Exception as e:
            logger.error(f"Error calling Claude API: {e}")
            raise

    def _build_content_prompt(self, transcript: Dict, config: Dict, template: str) -> str:
        """
        Build the content generation prompt from template and context.

        Args:
            transcript: Conversation transcript
            config: Configuration dict
            template: Prompt template

        Returns:
            Complete prompt string
        """
        # Format the transcript for the prompt
        exchanges_text = "\n\n".join([
            f"Q: {ex['question']}\nA: {ex['response']}"
            for ex in transcript.get('exchanges', [])
        ])

        # Replace placeholders in template
        prompt = template.replace("{{TOPIC}}", transcript.get('topic', 'Unknown'))
        prompt = prompt.replace("{{TRANSCRIPT}}", exchanges_text)
        prompt = prompt.replace("{{BRAND_VOICE}}", self._get_brand_voice_rules())
        prompt = prompt.replace("{{CHANNEL_SPECS}}", self._format_channel_specs(config))

        return prompt

    def _get_brand_voice_rules(self) -> str:
        """Get brand voice rules as formatted text."""
        return """
DO:
- Lead with data, always
- State things plainly: "yields fell 12%" not "yields experienced a significant decline"
- Use comparisons: "roughly the output of the entire Australian almond industry"
- Acknowledge limits: "the data shows X, though we don't have visibility into Y"
- Credit sources including Demeter
- Treat agriculture as serious global infrastructure

DON'T:
- Editorialise in data posts. No "finally", "surprisingly", "worryingly". Present the data.
- Corporate language: "excited to share", "leverage", "synergy"
- Emojis (none, ever)
- Hashtags (none, ever)
- Press release voice: "Demeter, the leading agricultural data provider"
- Pretend certainty where there is none
- Name competitors
- "Disrupting" or "revolutionising"
- "Genuinely", "honestly", "frankly"
        """

    def _format_channel_specs(self, config: Dict) -> str:
        """Format channel specifications for prompt."""
        channels = config.get('channels', {})
        return f"""
Twitter: max {channels.get('twitter', {}).get('max_characters', 280)} characters
LinkedIn: max {channels.get('linkedin', {}).get('max_characters', 3000)} characters
        """
