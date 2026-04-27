"""
backend/modules/llm_client.py
Centralised Groq LLM wrapper used by all analysis modules.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from groq import AsyncGroq

# Load .env from project root (two levels up from this file)
ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=ENV_PATH)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL   = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

client = AsyncGroq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None


def _clean(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _parse_json(text: str) -> dict:
    cleaned = _clean(text)
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
        return {"data": parsed}
    except json.JSONDecodeError:
        start = min((i for i in [cleaned.find("{"), cleaned.find("[")] if i != -1), default=-1)
        if start != -1:
            try:
                parsed, _ = json.JSONDecoder().raw_decode(cleaned[start:])
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass
        raise ValueError(f"LLM returned invalid JSON. Raw (500 chars):\n{cleaned[:500]}")


async def ask_llm(system_prompt: str, user_prompt: str,
                  temperature: float = 0.1, max_tokens: int = 1024) -> dict:
    """Send prompt → get JSON dict back."""
    if client is None:
        raise EnvironmentError("GROQ_API_KEY not set. Copy .env.example → .env and add your key.")
    response = await client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return _parse_json(response.choices[0].message.content)


async def ask_llm_text(system_prompt: str, user_prompt: str,
                       temperature: float = 0.5, max_tokens: int = 512) -> str:
    """Send prompt → get plain text back (for summaries / emails)."""
    if client is None:
        raise EnvironmentError("GROQ_API_KEY not set. Copy .env.example → .env and add your key.")
    response = await client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content.strip()


async def check_groq_health() -> dict:
    try:
        if client is None:
            return {"status": "error", "detail": "GROQ_API_KEY not set"}
        await client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": "Reply with just: ok"}],
            max_tokens=5,
        )
        return {"groq": "connected", "model": GROQ_MODEL, "status": "ok"}
    except Exception as exc:
        return {"groq": "unreachable", "model": GROQ_MODEL, "status": "error", "detail": str(exc)}
