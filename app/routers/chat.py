import os
import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Literal

router = APIRouter(prefix="/chat", tags=["chat"])

OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
HERMES_MODEL = os.getenv("HERMES_MODEL", "nous-hermes2")


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class ChatRequest(BaseModel):
    model: Literal["claude", "hermes"]
    messages: list[ChatMessage]
    claude_model: str = "anthropic/claude-3.5-sonnet"


async def stream_claude(messages: list[dict], model: str):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/acton-golden/claude.yml",
    }
    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
    }
    async with httpx.AsyncClient(timeout=120) as client:
        async with client.stream(
            "POST",
            f"{OPENROUTER_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if line.startswith("data: ") and line != "data: [DONE]":
                    yield line + "\n\n"


async def stream_hermes(messages: list[dict]):
    payload = {
        "model": HERMES_MODEL,
        "messages": messages,
        "stream": True,
    }
    async with httpx.AsyncClient(timeout=120) as client:
        async with client.stream(
            "POST",
            f"{OLLAMA_BASE_URL}/api/chat",
            json=payload,
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if line:
                    yield f"data: {line}\n\n"


@router.post("/stream")
async def chat_stream(req: ChatRequest):
    messages = [m.model_dump() for m in req.messages]
    if req.model == "claude":
        if not OPENROUTER_API_KEY:
            raise HTTPException(503, "OPENROUTER_API_KEY not configured")
        return StreamingResponse(
            stream_claude(messages, req.claude_model),
            media_type="text/event-stream",
        )
    else:
        return StreamingResponse(
            stream_hermes(messages),
            media_type="text/event-stream",
        )
