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


class ChartConfig(BaseModel):
    name: str
    url: str


class URLConfig(BaseModel):
    charts: list[ChartConfig]
