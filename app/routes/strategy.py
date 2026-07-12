from pathlib import Path
from fastapi import APIRouter

router = APIRouter(prefix="/api/strategy", tags=["strategy"])

PROMPT_PATH = Path("prompts/strategy.md")


@router.get("")
async def get_strategy():
    if PROMPT_PATH.exists():
        return {"content": PROMPT_PATH.read_text(encoding="utf-8")}
    return {"content": ""}


@router.put("")
async def update_strategy(body: dict):
    content = body.get("content", "")
    PROMPT_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROMPT_PATH.write_text(content, encoding="utf-8")
    return {"ok": True}
