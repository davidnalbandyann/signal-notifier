from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional


class Direction(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    NEUTRAL = "NEUTRAL"


class AnalysisResult(BaseModel):
    score: float = Field(..., ge=0, le=10, description="Setup quality score 0-10")
    direction: Direction
    reason: str
    entry: Optional[str] = None
    stop_loss: Optional[str] = None
    take_profit: Optional[str] = None
    error: Optional[str] = None


class ChartType(str, Enum):
    CRYPTO = "crypto"
    FOREX = "forex"
    STOCKS = "stocks"
    INDICES = "indices"
    COMMODITIES = "commodities"
    OTHER = "other"


class ChartConfig(BaseModel):
    name: str
    url: str
    symbol: Optional[str] = None
    timeframe: Optional[str] = "15m"
    type: Optional[str] = "crypto"


class URLConfig(BaseModel):
    charts: list[ChartConfig]


class CppStrategyCreate(BaseModel):
    name: str
    engine_type: str
    params: dict = {}


class AiStrategyCreate(BaseModel):
    name: str
    content: str


class ActiveStrategyCreate(BaseModel):
    name: str
    mode: str
    enabled: int = 1
    chart_id: int
    cpp_strategy_id: Optional[int] = None
    ai_strategy_id: Optional[int] = None
    min_score: Optional[float] = None
    cooldown_minutes: int = 15

