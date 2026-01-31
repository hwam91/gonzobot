"""
Browser automation service for interacting with Demeter AI assistant.
Uses Playwright to drive conversations at assistant.demeterdata.ag
"""

import asyncio
import logging
from typing import List, Dict, Optional
from playwright.async_api import async_playwright, Page, Browser, TimeoutError as PlaywrightTimeout

logger = logging.getLogger(__name__)

# DOM selectors for Demeter AI assistant
# Updated 2026-01-31 based on actual UI inspection
SELECTORS = {
    "chat_input": "textarea[placeholder='Reply...']",
    "send_button": "button[type='submit']",
    "loading_spinner": "svg",  # Spinner appears while loading
    "main_content": "main"  # Main content area contains messages
}


class DemeterAIBrowser:
    """Manages Playwright browser sessions with Demeter AI assistant."""

    def __init__(self, url: str, timeout_seconds: int = 120):
        self.url = url
        self.timeout = timeout_seconds * 1000  # Convert to milliseconds
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None

    async def __aenter__(self):
        """Context manager entry - launch browser."""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        self.page = await self.browser.new_page()
        await self.page.goto(self.url)
        logger.info(f"Browser launched and navigated to {self.url}")

        # Wait for page to be ready
        await asyncio.sleep(3)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close browser."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("Browser closed")

    async def send_message(self, message: str) -> str:
        """
        Send a message to the Demeter AI assistant and wait for response.

        Args:
            message: The question or message to send

        Returns:
            The assistant's response text

        Raises:
            TimeoutError: If response takes longer than configured timeout
            RuntimeError: If UI elements cannot be found
        """
        if not self.page:
            raise RuntimeError("Browser not initialized. Use as context manager.")

        try:
            # Find and fill the chat input
            logger.info(f"Sending message: {message[:100]}...")

            # Wait for and fill the input field
            input_field = await self.page.wait_for_selector(SELECTORS["chat_input"], timeout=10000)
            await input_field.fill(message)
            await asyncio.sleep(0.5)

            # Wait for the send button to be enabled (not disabled)
            send_button = await self.page.wait_for_selector(
                f"{SELECTORS['send_button']}:not([disabled])",
                timeout=10000,
                state="attached"
            )
            await send_button.click()

            logger.info("Message sent, waiting for response...")

            # Wait for response (with generous timeout)
            response_text = await self._wait_for_response()

            logger.info(f"Received response: {response_text[:100]}...")
            return response_text

        except PlaywrightTimeout as e:
            logger.error(f"Timeout waiting for response: {e}")
            raise TimeoutError(f"Demeter AI did not respond within {self.timeout/1000}s")
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            raise

    async def _wait_for_response(self) -> str:
        """
        Wait for the assistant's response to complete.

        Returns:
            The complete response text
        """
        # Wait for the response to start appearing
        await asyncio.sleep(5)

        # Get the main content area
        main_element = await self.page.query_selector(SELECTORS["main_content"])
        if not main_element:
            raise RuntimeError("Could not find main content area")

        # Monitor the text content until it stops changing (response complete)
        previous_text = ""
        stable_count = 0
        max_wait_iterations = 30  # 30 * 2 seconds = 60 seconds max

        for i in range(max_wait_iterations):
            current_text = await main_element.inner_text()

            if current_text == previous_text:
                stable_count += 1
                if stable_count >= 3:  # Text hasn't changed for 6 seconds
                    break
            else:
                stable_count = 0
                previous_text = current_text

            await asyncio.sleep(2)

        # Extract just the assistant's response (everything after the question)
        full_text = await main_element.inner_text()

        # The response is everything after the first occurrence of the question
        # Split on newlines and find where the response starts
        lines = full_text.split('\n')

        # Look for the response content (skip the question which appears at the top)
        # The response typically starts after the question line
        response_lines = []
        found_question = False

        for line in lines:
            if found_question and line.strip():
                response_lines.append(line)
            elif not found_question and len(line) > 50:  # Question is typically long
                found_question = True

        if response_lines:
            return '\n'.join(response_lines).strip()

        # Fallback: return all text from main
        logger.warning("Could not parse response cleanly, returning full text")
        return full_text.strip()

    async def start_new_conversation(self):
        """Start a new conversation (refresh page or click new chat button)."""
        logger.info("Starting new conversation")
        # Simple approach: reload the page
        await self.page.reload()
        await asyncio.sleep(3)


async def run_conversation(url: str, exchanges: List[Dict[str, str]], timeout: int = 120) -> List[Dict[str, str]]:
    """
    Run a complete conversation with the Demeter AI assistant.

    Args:
        url: URL of the Demeter AI assistant
        exchanges: List of exchanges, each with 'question' key (response will be added)
        timeout: Timeout in seconds for each response

    Returns:
        List of exchanges with both 'question' and 'response' keys
    """
    results = []

    async with DemeterAIBrowser(url, timeout) as browser:
        for i, exchange in enumerate(exchanges):
            question = exchange.get("question", "")
            if not question:
                logger.warning(f"Exchange {i} has no question, skipping")
                continue

            try:
                response = await browser.send_message(question)
                results.append({
                    "question": question,
                    "response": response
                })

                # Small delay between exchanges
                await asyncio.sleep(2)

            except Exception as e:
                logger.error(f"Failed to get response for exchange {i}: {e}")
                results.append({
                    "question": question,
                    "response": f"[ERROR: {str(e)}]"
                })

    return results
