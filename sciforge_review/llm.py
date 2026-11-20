"""Minimal OpenAI-compatible client for the yunshu gateway.

The gateway exposes the **Responses** API (``wire_api = "responses"``), not the
chat-completions API, so the call is ``POST {base_url}/responses``.

Credentials are read from, in order:

1. environment variables (``OPENAI_BASE_URL`` / ``OPENAI_API_KEY`` / ``OPENAI_MODEL``)
2. ``~/.config/yunshu/openai.env``
3. ``.env.local`` in the project root (gitignored)

The key is never printed, logged, or written into a receipt.  ``--check`` shows
only the base URL, model, HTTP status and a short error, never the key.
"""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

DEFAULT_BASE_URL = "https://gmn-gw.yunshu.best/v1"
DEFAULT_MODEL = "gpt-6.1-sol"
DEFAULT_ACTOR = "local-image-extension"


class LLMConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class LLMConfig:
    base_url: str
    api_key: str
    model: str
    actor: str = DEFAULT_ACTOR
    bearer_token: str | None = None

    def __repr__(self) -> str:  # never leak a credential through repr()
        return (
            f"LLMConfig(base_url={self.base_url!r}, model={self.model!r}, "
            "api_key='***', bearer_token='***')"
        )


def _parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        if value:
            values[key.strip()] = value
    return values


def load_config(env_path: Path | None = None, include_defaults: bool = True) -> LLMConfig:
    values: dict[str, str] = {}
    sources: list[Path] = []
    if include_defaults:
        sources.extend(
            [
                Path.home() / ".config" / "yunshu" / "openai.env",
                Path.cwd() / ".env.local",
            ]
        )
    if env_path:
        sources.append(Path(env_path))
    for path in sources:
        if path.is_file():
            values.update(_parse_env_file(path))

    base_url = os.environ.get("OPENAI_BASE_URL") or values.get("OPENAI_BASE_URL") or DEFAULT_BASE_URL
    model = os.environ.get("OPENAI_MODEL") or values.get("OPENAI_MODEL") or DEFAULT_MODEL
    api_key = os.environ.get("OPENAI_API_KEY") or values.get("OPENAI_API_KEY")
    bearer = os.environ.get("OPENAI_BEARER_TOKEN") or values.get("OPENAI_BEARER_TOKEN")
    actor = os.environ.get("OPENAI_ACTOR") or values.get("OPENAI_ACTOR") or DEFAULT_ACTOR

    if not api_key:
        raise LLMConfigError(
            "no API key: set OPENAI_API_KEY in ~/.config/yunshu/openai.env "
            "(or .env.local). Do not paste the key into chat."
        )
    return LLMConfig(
        base_url=base_url.rstrip("/"),
        api_key=api_key,
        model=model,
        actor=actor,
        bearer_token=bearer or api_key,
    )


def _headers(config: LLMConfig) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {config.bearer_token or config.api_key}",
        "Content-Type": "application/json",
        "x-openai-actor-authorization": config.actor,
    }


def _request(
    config: LLMConfig,
    method: str,
    path: str,
    payload: dict | None = None,
    timeout: float = 30.0,
) -> tuple[int, dict]:
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        config.base_url + path,
        data=data,
        method=method,
        headers=_headers(config),
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            parsed = {"raw": body[:500]}
        return exc.code, parsed


def list_models(config: LLMConfig, timeout: float = 20.0) -> tuple[int, dict]:
    return _request(config, "GET", "/models", timeout=timeout)


def _extract_text(data: dict) -> str:
    if isinstance(data.get("output_text"), str):
        return data["output_text"]
    parts: list[str] = []
    for item in data.get("output", []) or []:
        for content in item.get("content", []) or []:
            if content.get("type") == "output_text" and content.get("text"):
                parts.append(content["text"])
    return "\n".join(parts).strip()


def respond(
    config: LLMConfig,
    prompt: str,
    *,
    max_output_tokens: int = 512,
    timeout: float = 90.0,
) -> str:
    status, data = _request(
        config,
        "POST",
        "/responses",
        payload={
            "model": config.model,
            "input": prompt,
            "max_output_tokens": max_output_tokens,
        },
        timeout=timeout,
    )
    if status >= 400:
        raise RuntimeError(f"responses call failed: HTTP {status}: {str(data)[:300]}")
    text = _extract_text(data)
    if not text:
        raise RuntimeError("responses call returned no output_text")
    return text


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="check /models without printing the key")
    parser.add_argument("--prompt", help="send one prompt to /responses")
    args = parser.parse_args()

    try:
        config = load_config()
    except LLMConfigError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        raise SystemExit(2)

    if args.check:
        status, data = list_models(config)
        models = data.get("data") if isinstance(data.get("data"), list) else None
        print(
            json.dumps(
                {
                    "ok": 200 <= status < 300,
                    "base_url": config.base_url,
                    "model": config.model,
                    "status": status,
                    "models_count": len(models) if models is not None else None,
                    "error": None if status < 400 else str(data)[:300],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    if args.prompt:
        print(respond(config, args.prompt))
        return

    parser.print_help()


if __name__ == "__main__":
    main()
