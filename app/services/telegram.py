import structlog
from io import BytesIO

from telegram import Bot
from telegram.error import TelegramError
from telegram.request import HTTPXRequest

from app.config.settings import Settings
from app.models.schemas import AnalysisResult

logger = structlog.get_logger(__name__)


class TelegramService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        request = HTTPXRequest(connect_timeout=10, read_timeout=30)
        self._bot = Bot(token=settings.TELEGRAM_TOKEN, request=request)
        self._chat_id = settings.TELEGRAM_CHAT_ID

    async def notify(
        self, name: str, analysis: AnalysisResult, screenshot: bytes
    ) -> None:
        caption = self._build_caption(name, analysis)
        photo = BytesIO(screenshot)
        photo.name = "chart.png"

        try:
            await self._bot.send_photo(
                chat_id=self._chat_id,
                photo=photo,
                caption=caption,
                parse_mode="HTML",
            )
            logger.info(
                "notification_sent",
                chart=name,
                score=analysis.score,
                direction=analysis.direction.value,
            )
        except TelegramError as e:
            logger.error(
                "telegram_send_failed",
                chart=name,
                error=str(e),
            )

    def _build_caption(self, name: str, analysis: AnalysisResult) -> str:
        prefix = (
            f"<b>{name}</b>\n\n"
            f"Score: <b>{analysis.score}/10</b>\n"
            f"Direction: <b>{analysis.direction.value}</b>\n\n"
        )

        suffix_parts = []
        if analysis.entry:
            suffix_parts.append(f"Entry: {analysis.entry}")
        if analysis.stop_loss:
            suffix_parts.append(f"Stop Loss: {analysis.stop_loss}")
        if analysis.take_profit:
            suffix_parts.append(f"Take Profit: {analysis.take_profit}")
        suffix = "\n".join(suffix_parts)
        if suffix:
            suffix = "\n" + suffix

        max_reason_len = 1024 - len(prefix) - len(suffix) - 1
        reason = analysis.reason

        if len(reason) > max_reason_len:
            reason = reason[: max_reason_len - 3] + "..."

        return f"{prefix}Reason: {reason}{suffix}"
