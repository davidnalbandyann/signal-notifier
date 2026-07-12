import asyncio
import base64
import re
import structlog
from pathlib import Path

import requests

from app.config.settings import Settings
from app.models.schemas import AnalysisResult, Direction

logger = structlog.get_logger(__name__)


class NvidiaService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._api_key = settings.NVIDIA_API_KEY
        self._model = settings.NVIDIA_MODEL
        self._invoke_url = "https://integrate.api.nvidia.com/v1/chat/completions"
        self._prompt_path = Path("prompts/strategy.md")

    def _load_prompt(self) -> str:
        return self._prompt_path.read_text(encoding="utf-8")

    async def analyze(self, screenshot_bytes: bytes) -> AnalysisResult:
        prompt = self._load_prompt()
        last_error = None

        for attempt in range(1, 4):
            try:
                response_text = await self._call_api(prompt, screenshot_bytes)
                return self._parse_response(response_text)
            except requests.RequestException as e:
                status = e.response.status_code if e.response is not None else None
                last_error = f"HTTP {status}: {e}" if status else str(e)
                logger.warning(
                    "nvidia_api_error",
                    attempt=attempt,
                    status=status,
                    error=str(e),
                )
                if status == 429:
                    wait = 2 ** attempt * 2
                    logger.info("rate_limit_backoff", seconds=wait)
                    await asyncio.sleep(wait)
                elif attempt < 3:
                    await asyncio.sleep(1)
                else:
                    return self._fallback_analysis(last_error)
            except Exception as e:
                last_error = str(e)
                logger.warning(
                    "analysis_error",
                    attempt=attempt,
                    error=str(e),
                )
                if attempt < 3:
                    await asyncio.sleep(1)
                else:
                    return self._fallback_analysis(last_error)

        return self._fallback_analysis(last_error)

    async def _call_api(self, prompt: str, screenshot_bytes: bytes) -> str:
        image_b64 = base64.b64encode(screenshot_bytes).decode()
        image_data_uri = f"data:image/png;base64,{image_b64}"

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self._model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_data_uri}},
                    ],
                }
            ],
            "max_tokens": 8192,
            "temperature": 1.00,
            "top_p": 0.95,
            "stream": False,
        }

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: requests.post(
                self._invoke_url,
                headers=headers,
                json=payload,
                timeout=60,
            ),
        )
        response.raise_for_status()
        data = response.json()

        choices = data.get("choices", [])
        if not choices:
            raise ValueError("No choices in API response")

        content = choices[0].get("message", {}).get("content", "")
        logger.info(
            "api_response_received",
            model=self._model,
            tokens=data.get("usage", {}),
        )
        return content

    def _parse_response(self, text: str) -> AnalysisResult:
        candidates = []

        for match in re.finditer(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL):
            candidates.append(match.group(1).strip())

        for match in re.finditer(r'\{[^{}]*?"score"\s*:\s*[\d.]+[^{}]*?\}', text, re.DOTALL):
            candidates.append(match.group(0).strip())

        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1]
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("\n", 1)[0]
        cleaned = cleaned.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:].strip()
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()
        candidates.append(cleaned)

        for c in candidates:
            if not c:
                continue
            try:
                result = AnalysisResult.model_validate_json(c)
                logger.info(
                    "analysis_complete",
                    score=result.score,
                    direction=result.direction.value,
                )
                return result
            except Exception:
                continue

        logger.error("json_parse_failed", raw=text[:500])
        return self._fallback_analysis(
            f"Could not find valid JSON in response. First 200 chars: {text[:200]}"
        )

    def _fallback_analysis(self, error: str | None = None) -> AnalysisResult:
        return AnalysisResult(
            score=0,
            direction=Direction.NEUTRAL,
            reason="Analysis failed due to an error",
            entry=None,
            stop_loss=None,
            take_profit=None,
            error=error,
        )
