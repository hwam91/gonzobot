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
# NOTE: These will need to be updated if the UI changes
SELECTORS = {
    "chat_input": "textarea[placeholder*='Ask'], textarea[placeholder*='question'], input[type='text']",
    "send_button": "button[type='submit'], button:has-text('Send')",
    "response_container": ".message, .response, [class*='assistant'], [class*='response']",
    "loading_indicator": ".loading, .spinner, [class*='loading']"
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

            # Try to find the input field
            input_field = None
            for selector in SELECTORS["chat_input"].split(", "):
                try:
                    input_field = await self.page.wait_for_selector(selector, timeout=5000)
                    if input_field:
                        break
                except:
                    continue

            if not input_field:
                raise RuntimeError("Could not find chat input field")

            await input_field.fill(message)
            await asyncio.sleep(0.5)

            # Try to find and click send button
            send_button = None
            for selector in SELECTORS["send_button"].split(", "):
                try:
                    send_button = await self.page.wait_for_selector(selector, timeout=5000)
                    if send_button:
                        break
                except:
                    continue

            if send_button:
                await send_button.click()
            else:
                # Fallback: press Enter
                await input_field.press("Enter")

            logger.info("Message sent, waiting for response...")

            # Wait for response to appear
            # Strategy: wait for loading indicator to appear then disappear,
            # or wait for new response container to appear
            await asyncio.sleep(2)

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
        # Wait for response container to appear
        await asyncio.sleep(3)

        # Try multiple selectors to find response
        response_selectors = [
            "[data-role='assistant']",
            ".assistant-message",
            "[class*='assistant']",
            ".message:last-child",
            "[class*='response']:last-of-type"
        ]

        response_element = None
        for selector in response_selectors:
            try:
                response_element = await self.page.query_selector(selector)
                if response_element:
                    break
            except:
                continue

        if not response_element:
            # Fallback: get all text from page and extract last message
            logger.warning("Could not find specific response element, using fallback")
            page_text = await self.page.inner_text("body")
            # Return last substantial block of text
            return page_text.strip()

        # Get text from response element
        response_text = await response_element.inner_text()

        # Wait a bit to ensure response is complete
        # Check if text is still changing
        await asyncio.sleep(2)
        new_text = await response_element.inner_text()

        if new_text != response_text:
            # Text is still updating, wait longer
            await asyncio.sleep(5)
            response_text = await response_element.inner_text()

        return response_text.strip()

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
