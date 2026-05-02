import json
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

try:
    import requests
except ImportError:
    raise ImportError("requests is required. Install it with: pip install requests")

from logger import get_logger
from config import get_config


@dataclass
class AIResponse:
    success: bool
    content: Optional[str] = None
    error: Optional[str] = None
    usage: Optional[Dict[str, int]] = None
    model: Optional[str] = None


class AIClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 2000,
        timeout: int = 60
    ):
        self.logger = get_logger(__name__)
        config = get_config()

        self.api_key = api_key or config.api_key
        self.base_url = base_url or config.base_url
        self.model = model or config.model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout

        if not self.api_key:
            raise AIClientError("API key is required")

    def call(self, prompt: str, system_prompt: Optional[str] = None) -> AIResponse:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        return self._send_request(messages)

    def _send_request(self, messages: List[Dict[str, str]]) -> AIResponse:
        url = f"{self.base_url.rstrip('/')}/chat/completions"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }

        self.logger.debug(f"Sending request to {url}")
        self.logger.debug(f"Model: {self.model}, Temperature: {self.temperature}")

        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=self.timeout
            )

            if response.status_code == 429:
                self.logger.warning("Rate limit hit, waiting before retry...")
                time.sleep(5)
                return self._send_request(messages)

            if response.status_code == 401:
                return AIResponse(
                    success=False,
                    error=f"Authentication failed: Invalid API key or unauthorized access"
                )

            if response.status_code != 200:
                return AIResponse(
                    success=False,
                    error=f"API request failed with status {response.status_code}: {response.text}"
                )

            result = response.json()

            if 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0]['message']['content']
                usage = result.get('usage', {})
                model = result.get('model', self.model)

                self.logger.info(f"Successfully received response, usage: {usage}")
                return AIResponse(
                    success=True,
                    content=content,
                    usage=usage,
                    model=model
                )
            else:
                return AIResponse(
                    success=False,
                    error="Invalid response format from API"
                )

        except requests.exceptions.Timeout:
            return AIResponse(
                success=False,
                error=f"Request timed out after {self.timeout} seconds"
            )
        except requests.exceptions.ConnectionError as e:
            return AIResponse(
                success=False,
                error=f"Connection error: {str(e)}"
            )
        except requests.exceptions.RequestException as e:
            return AIResponse(
                success=False,
                error=f"Request error: {str(e)}"
            )
        except json.JSONDecodeError as e:
            return AIResponse(
                success=False,
                error=f"Failed to parse response: {str(e)}"
            )

    def test_connection(self) -> bool:
        test_response = self.call(
            prompt="Reply with 'OK' if you can understand this message.",
            system_prompt="You are a helpful assistant."
        )
        if test_response.success:
            self.logger.info("API connection test successful")
            return True
        else:
            self.logger.error(f"API connection test failed: {test_response.error}")
            return False


class AIClientError(Exception):
    pass


def create_ai_client(
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None
) -> AIClient:
    return AIClient(
        api_key=api_key,
        base_url=base_url,
        model=model
    )