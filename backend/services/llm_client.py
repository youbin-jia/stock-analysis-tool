"""统一的 LLM 调用层

支持两类协议：
  - "openai" 兼容（Kimi / 月之暗面）：requests + /chat/completions
  - "anthropic"（Claude）：官方 anthropic SDK，零配置读 ANTHROPIC_AUTH_TOKEN / ANTHROPIC_BASE_URL

设计约束：
  * 所有 env 读取必须在**调用时**发生。uvicorn 以 reload=True 启动时只重载代码、
    不重读环境变量，import 时捕获会导致改了 env 却不生效。
  * 流式接口只 yield 纯文本增量，错误统一 raise LLMError，调用方只需一处 except。
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, Generator, List, Optional, Tuple

import requests


class LLMError(RuntimeError):
    """LLM 调用失败（网络、鉴权、上游状态码等），用于流式路径。"""


# ---------- 厂商注册表 ----------
# kind 决定调用协议分支；不含任何密钥字段，可安全序列化给前端。
PROVIDERS: Dict[str, Dict[str, Any]] = {
    "kimi": {
        "key": "kimi",
        "name": "Kimi（月之暗面）",
        "kind": "openai",
        "env_key": "KIMI_API_KEY",
        "base": "https://api.moonshot.cn/v1",
        "supports_temperature": True,
        "models": [
            {"id": "moonshot-v1-128k", "label": "moonshot-v1-128k（长文，推荐报告）"},
            {"id": "moonshot-v1-32k", "label": "moonshot-v1-32k（便宜）"},
            {"id": "moonshot-v1-8k", "label": "moonshot-v1-8k（短任务）"},
        ],
    },
    "anthropic": {
        "key": "anthropic",
        "name": "Claude（Anthropic）",
        "kind": "anthropic",
        "env_key": "ANTHROPIC_API_KEY",  # 实际判定见 _configured()
        "base": None,                     # SDK 自读 ANTHROPIC_BASE_URL
        "supports_temperature": False,    # opus-5 / sonnet-5 传 temperature 会 400
        # 注意：模型 id 取决于 ANTHROPIC_BASE_URL 指向的网关。
        # 内网 horizon 网关用自有 id（HORIZON-CO-5 等），官方 API 用 claude-opus-5 等。
        # ~/.claude/settings.json 里的 "[1m]" 后缀是 Claude Code 侧的上下文标注，网关不认（404）。
        # 模型列表随网关而变，见 _models()
        "models": None,
    },
}

DEFAULT_PROVIDER = "kimi"

# Claude 的 thinking 与正文共用 max_tokens，必须给足，且大 max_tokens 需强制流式。
MAX_TOKENS_ANTHROPIC = 64000

# 官方 Anthropic API 的模型 id
_ANTHROPIC_OFFICIAL_MODELS = [
    {"id": "claude-opus-5", "label": "Claude Opus 5（最强，默认）"},
    {"id": "claude-sonnet-5", "label": "Claude Sonnet 5（快且便宜）"},
]

# 内网 horizon 网关的模型 id（与官方不同名）。注意 ~/.claude/settings.json 里的
# "[1m]" 后缀是 Claude Code 侧的上下文标注，直接发给网关会 404。
_ANTHROPIC_HORIZON_MODELS = [
    {"id": "HORIZON-CO-5", "label": "HORIZON-CO-5（Opus，最强，默认）"},
    {"id": "HORIZON-CSN-4.6", "label": "HORIZON-CSN-4.6（Sonnet，均衡）"},
    {"id": "HORIZON-CHK-4.5", "label": "HORIZON-CHK-4.5（Haiku，最快）"},
]


def _models(pkey: str) -> List[Dict[str, str]]:
    """运行时解析模型列表 —— anthropic 的可用模型取决于 ANTHROPIC_BASE_URL 指向的网关。"""
    if pkey == "anthropic":
        base = (os.environ.get("ANTHROPIC_BASE_URL") or "").lower()
        if base and "anthropic.com" not in base:
            return _ANTHROPIC_HORIZON_MODELS
        return _ANTHROPIC_OFFICIAL_MODELS
    return PROVIDERS[pkey]["models"] or []


# ---------- 可用性与归一化 ----------

def _default_model(pkey: str) -> str:
    """运行时读取默认模型（不在 import 时捕获）。

    env 覆盖必须是本厂商 models 列表里的合法 id —— 否则忽略。
    （例如 ANTHROPIC_MODEL 常被设成 Claude Code 的别名 "opus"，那不是 API 可用的模型 id。）
    """
    fallback = _models(pkey)[0]["id"]
    env_name = {"kimi": "KIMI_REPORT_MODEL", "anthropic": "ANTHROPIC_MODEL"}.get(pkey)
    override = os.environ.get(env_name) if env_name else None
    if override and override in {m["id"] for m in _models(pkey)}:
        return override
    return fallback


def _configured(pkey: str) -> bool:
    """该厂商是否已配置凭据。"""
    if pkey not in PROVIDERS:
        return False
    if pkey == "anthropic":
        # SDK 凭据顺序是 ANTHROPIC_API_KEY → ANTHROPIC_AUTH_TOKEN，查一个不够
        return bool(
            os.environ.get("ANTHROPIC_API_KEY")
            or os.environ.get("ANTHROPIC_AUTH_TOKEN")
        )
    return bool(os.environ.get(PROVIDERS[pkey]["env_key"]))


def available_providers() -> List[Dict[str, Any]]:
    """已配置凭据的厂商列表（供 /presets），不含密钥。"""
    out: List[Dict[str, Any]] = []
    for pkey, p in PROVIDERS.items():
        if not _configured(pkey):
            continue
        out.append({
            "key": p["key"],
            "name": p["name"],
            "models": _models(pkey),
            "default_model": _default_model(pkey),
            "supports_temperature": p["supports_temperature"],
        })
    return out


def resolve(provider: Optional[str], model: Optional[str]) -> Tuple[str, str]:
    """归一化 (provider, model)，非法值回落而不报错。

    Raises:
        ValueError: 一个厂商都没配置。
    """
    usable = [k for k in PROVIDERS if _configured(k)]
    if not usable:
        raise ValueError("未配置任何 LLM 厂商的 API Key")

    if provider not in usable:
        provider = DEFAULT_PROVIDER if DEFAULT_PROVIDER in usable else usable[0]

    valid_ids = {m["id"] for m in _models(provider)}
    if not model or model not in valid_ids:
        model = _default_model(provider)
    return provider, model


def _split_system(messages: List[Dict[str, str]]) -> Tuple[str, List[Dict[str, str]]]:
    """Anthropic 的 system 是顶层参数，需从 messages 中拆出来。"""
    sys_parts = [m.get("content", "") for m in messages if m.get("role") == "system"]
    rest = [m for m in messages if m.get("role") != "system"]
    return "\n\n".join(p for p in sys_parts if p), rest


def _api_key(pkey: str) -> str:
    return os.environ.get(PROVIDERS[pkey]["env_key"], "")


# ---------- 非流式 ----------

def _openai_chat(
    messages: List[Dict[str, str]],
    provider: str,
    model: str,
    temperature: float,
    max_retries: int,
    timeout: int,
) -> Optional[str]:
    p = PROVIDERS[provider]
    headers = {
        "Authorization": f"Bearer {_api_key(provider)}",
        "Content-Type": "application/json",
    }
    payload: Dict[str, Any] = {"model": model, "messages": messages}
    if p["supports_temperature"]:
        payload["temperature"] = temperature

    for attempt in range(max_retries + 1):
        try:
            r = requests.post(
                f"{p['base']}/chat/completions",
                headers=headers, json=payload, timeout=timeout,
            )
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"]
            if r.status_code == 429:
                time.sleep(8 + attempt * 5)
                continue
            print(f"[llm] {provider} 错误 {r.status_code}: {r.text[:200]}")
            return None
        except Exception as e:
            print(f"[llm] {provider} 调用异常 第{attempt + 1}次: {e}")
            time.sleep(3 + attempt * 2)
    return None


def _anthropic_chat(
    messages: List[Dict[str, str]],
    model: str,
    timeout: int,
) -> Optional[str]:
    import anthropic

    client = anthropic.Anthropic(timeout=timeout)
    system, msgs = _split_system(messages)
    try:
        # 大 max_tokens 必须走流式，否则 SDK 直接拒绝；不传 temperature（opus-5 会 400）
        with client.messages.stream(
            model=model,
            max_tokens=MAX_TOKENS_ANTHROPIC,
            messages=msgs,
            **({"system": system} if system else {}),
        ) as s:
            final = s.get_final_message()
        # thinking block 也在 content 里，必须按 type 过滤
        return "".join(b.text for b in final.content if b.type == "text")
    except Exception as e:
        print(f"[llm] anthropic 调用异常: {e}")
        return None


def chat(
    messages: List[Dict[str, str]],
    provider: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.3,
    max_retries: int = 2,
    timeout: int = 60,
) -> Optional[str]:
    """非流式对话，失败返回 None。"""
    try:
        provider, model = resolve(provider, model)
    except ValueError as e:
        print(f"[llm] {e}")
        return None

    if PROVIDERS[provider]["kind"] == "anthropic":
        return _anthropic_chat(messages, model, timeout)
    return _openai_chat(messages, provider, model, temperature, max_retries, timeout)


# ---------- 流式 ----------

def _openai_stream(
    messages: List[Dict[str, str]],
    provider: str,
    model: str,
    temperature: float,
    timeout: int,
) -> Generator[str, None, None]:
    p = PROVIDERS[provider]
    headers = {
        "Authorization": f"Bearer {_api_key(provider)}",
        "Content-Type": "application/json",
    }
    payload: Dict[str, Any] = {"model": model, "messages": messages, "stream": True}
    if p["supports_temperature"]:
        payload["temperature"] = temperature

    try:
        with requests.post(
            f"{p['base']}/chat/completions",
            headers=headers, json=payload, stream=True, timeout=timeout,
        ) as r:
            if r.status_code != 200:
                raise LLMError(f"{provider} HTTP {r.status_code}: {r.text[:300]}")
            # 强制 UTF-8 解码，避免 requests 默认按 ISO-8859-1 解 SSE 字节流
            r.encoding = "utf-8"
            for raw in r.iter_lines(decode_unicode=True):
                if not raw or not raw.startswith("data: "):
                    continue
                data_str = raw[6:]
                if data_str.strip() == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                except json.JSONDecodeError:
                    continue
                delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content")
                if delta:
                    yield delta
    except requests.exceptions.RequestException as e:
        raise LLMError(f"{provider} 请求异常: {e}") from e


def _anthropic_stream(
    messages: List[Dict[str, str]],
    model: str,
    timeout: int,
) -> Generator[str, None, None]:
    import anthropic

    client = anthropic.Anthropic(timeout=timeout)
    system, msgs = _split_system(messages)
    try:
        with client.messages.stream(
            model=model,
            max_tokens=MAX_TOKENS_ANTHROPIC,
            messages=msgs,
            **({"system": system} if system else {}),
        ) as s:
            # text_stream 只吐正文增量，thinking block 自动跳过
            for text in s.text_stream:
                yield text
    except Exception as e:
        raise LLMError(f"anthropic 请求异常: {e}") from e


def stream_chat(
    messages: List[Dict[str, str]],
    provider: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.6,
    timeout: int = 300,
) -> Generator[str, None, None]:
    """流式对话，逐段 yield 纯文本增量。

    Raises:
        LLMError: 任何上游错误。
        ValueError: 一个厂商都没配置。
    """
    provider, model = resolve(provider, model)
    if PROVIDERS[provider]["kind"] == "anthropic":
        yield from _anthropic_stream(messages, model, timeout)
    else:
        yield from _openai_stream(messages, provider, model, temperature, timeout)
