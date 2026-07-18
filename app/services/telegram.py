import structlog
from io import BytesIO

from telegram import Bot
from telegram.error import TelegramError
from telegram.request import HTTPXRequest

from app.config.settings import Settings
from app.models.schemas import AnalysisResult
from app.utils import get_display_timezone

logger = structlog.get_logger(__name__)


class TelegramService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        request = HTTPXRequest(connect_timeout=10, read_timeout=30)
        self._bot = Bot(token=settings.TELEGRAM_TOKEN, request=request)
        self._chat_id = settings.TELEGRAM_CHAT_ID

    async def notify(
        self, name: str, analysis: AnalysisResult, screenshot: bytes | None,
        extra_caption: str | None = None, timeframe: str = "",
        analysis_id: int | None = None,
    ) -> str:
        caption = self._build_caption(name, analysis, extra_caption, timeframe, analysis_id)

        try:
            if screenshot:
                photo = BytesIO(screenshot)
                photo.name = "chart.png"
                await self._bot.send_photo(
                    chat_id=self._chat_id,
                    photo=photo,
                    caption=caption,
                    parse_mode="HTML",
                )
            else:
                await self._bot.send_message(
                    chat_id=self._chat_id,
                    text=caption,
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

        return caption

    def _build_caption(
        self, name: str, analysis: AnalysisResult, extra_caption: str | None,
        timeframe: str = "", analysis_id: int | None = None,
    ) -> str:
        import zoneinfo
        from datetime import datetime

        lines = []

        # Title line: name + timeframe
        title = f"<b>{name}</b>"
        if timeframe:
            title += f"  ·  {timeframe}"
        lines.append(title)

        # Timestamp
        tz_name = get_display_timezone()
        try:
            tz = zoneinfo.ZoneInfo(tz_name)
        except Exception:
            tz = None
        ts = datetime.now(tz).strftime("%Y-%m-%d %H:%M") if tz else datetime.now().strftime("%Y-%m-%d %H:%M")
        tz_abbr = datetime.now(tz).strftime("%Z") if tz else "UTC"
        lines.append(f"<i>{ts} {tz_abbr}</i>")

        # C++ extra caption (includes direction, entry, stats)
        if extra_caption:
            lines.append("")
            lines.append(extra_caption.rstrip("\n"))

        # Score + direction
        lines.append("")
        lines.append(f"Score: <b>{analysis.score}/10</b>  ·  Direction: <b>{analysis.direction.value}</b>")

        # Levels
        levels = []
        if analysis.entry:
            levels.append(f"Entry: {analysis.entry}")
        if analysis.stop_loss:
            levels.append(f"Stop Loss: {analysis.stop_loss}")
        if analysis.take_profit:
            levels.append(f"Take Profit: {analysis.take_profit}")
        if levels:
            lines.append("")
            lines.append(" | ".join(levels))

        # Reason
        lines.append("")
        max_reason = 1024 - sum(len(l) for l in lines) - 50
        reason = analysis.reason
        if len(reason) > max_reason:
            reason = reason[:max_reason - 3] + "..."
        lines.append(reason)

        # Dashboard link
        base_url = self.settings.DASHBOARD_BASE_URL.strip()
        if base_url and analysis_id:
            link = f"{base_url.rstrip('/')}/analysis/{analysis_id}"
            lines.append("")
            lines.append(f'<a href="{link}">Open in dashboard</a>')

        return "\n".join(lines)
