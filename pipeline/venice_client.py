"""
venice_client.py — Thin wrapper around the Venice AI API (OpenAI-compatible).
"""
import base64
import os
import json
import http.client
import re
import urllib.parse
from typing import Optional

VENICE_API_KEY = os.environ["VENICE_AI_API_KEY"]
VENICE_HOST = "api.venice.ai"
VENICE_BASE_PATH = "/api/v1"
# Default model — override via VENICE_MODEL env var
DEFAULT_MODEL = os.environ.get("VENICE_MODEL", "mistral-small-3-2-24b-instruct")


def chat(
    messages: list[dict],
    model: Optional[str] = None,
    temperature: float = 0.3,
    max_tokens: int = 1024,
    disable_thinking: bool = False,
) -> str:
    """
    Call Venice AI chat completions and return the assistant reply as a string.
    Raises RuntimeError on non-200 responses.
    """
    body_dict: dict = {
        "model": model or DEFAULT_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if disable_thinking:
        body_dict["venice_parameters"] = {"disable_thinking": True}
    payload = json.dumps(body_dict).encode("utf-8")

    conn = http.client.HTTPSConnection(VENICE_HOST)
    conn.request(
        "POST",
        f"{VENICE_BASE_PATH}/chat/completions",
        body=payload,
        headers={
            "Authorization": f"Bearer {VENICE_API_KEY}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    resp = conn.getresponse()
    body = resp.read().decode("utf-8")
    conn.close()

    if resp.status != 200:
        raise RuntimeError(
            f"Venice AI API error {resp.status}: {body[:400]}"
        )

    data = json.loads(body)
    return data["choices"][0]["message"]["content"].strip()


def json_chat(
    messages: list[dict],
    model: Optional[str] = None,
    temperature: float = 0.1,
    max_tokens: int = 2048,
) -> dict | list:
    """
    Like chat(), but expects a JSON response and parses it.
    Raises ValueError if the response is not valid JSON.
    """
    content = chat(messages, model=model, temperature=temperature, max_tokens=max_tokens, disable_thinking=True)
    # Strip <think>…</think> reasoning blocks (safety fallback)
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
    # Strip markdown code fences if present
    fence = re.search(r"```(?:json)?\s*\n(.*?)```", content, re.DOTALL)
    if fence:
        content = fence.group(1).strip()
    # Last resort: extract first JSON array or object
    if content and content[0] not in ("[", "{"):
        m = re.search(r"(\[.*\]|\{.*\})", content, re.DOTALL)
        if m:
            content = m.group(1)
    # Use raw_decode to ignore trailing text after valid JSON
    decoder = json.JSONDecoder()
    result, _ = decoder.raw_decode(content)
    return result


def generate_image(
    prompt: str,
    model: str = "chroma",
    negative_prompt: str = "",
) -> bytes:
    """
    Call Venice AI image generation and return raw image bytes.
    Raises RuntimeError on non-200 responses.
    """
    body: dict = {
        "model": model,
        "prompt": prompt,
    }
    if negative_prompt:
        body["negative_prompt"] = negative_prompt
    payload = json.dumps(body).encode("utf-8")

    conn = http.client.HTTPSConnection(VENICE_HOST)
    conn.request(
        "POST",
        f"{VENICE_BASE_PATH}/image/generate",
        body=payload,
        headers={
            "Authorization": f"Bearer {VENICE_API_KEY}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    resp = conn.getresponse()
    body = resp.read()
    conn.close()

    if resp.status != 200:
        raise RuntimeError(
            f"Venice AI image API error {resp.status}: {body.decode('utf-8', errors='replace')[:400]}"
        )

    data = json.loads(body.decode("utf-8"))
    # Venice native API returns {"images": ["<b64string>", ...]}
    b64 = data["images"][0]
    return base64.b64decode(b64)
