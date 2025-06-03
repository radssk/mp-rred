
from __future__ import annotations
import re, json, time
import openai, streamlit as st
from typing import List, Dict, Any

from llm_tools.prompt import ERROR_SCHEMA, REQUEST_TIMEOUT, RETRY_SLEEP

def _parse_score(cell: str | Dict[str, Any]) -> int | None:
    if not cell:
        return None
    try:
        obj = cell if isinstance(cell, dict) else json.loads(cell)
        err = obj.get("error", "")
        return 1 if re.fullmatch(r"no[\s_]?errors?", err, flags=re.I) else 0
    except Exception:
        return None

def _validate_json_response(content: str) -> None:
    try:
        obj = json.loads(content)
    except Exception as e:
        raise ValueError(f"Invalid JSON format: {e}")
    if not (isinstance(obj, dict) and "error" in obj and "error_reason" in obj):
        raise ValueError("Response JSON missing required keys")

def _chat_completion(client, model: str, messages: List[Dict[str, Any]]) -> str:
    return client.chat.completions.create(
        model=model,
        messages=messages,
        response_format={"type": "json_schema", "json_schema": ERROR_SCHEMA},
        reasoning_effort="high",
        timeout=REQUEST_TIMEOUT,
    ).choices[0].message.content

def _make_client(api_key: str, use_chatgpt: bool, **kw):
    try:
        if use_chatgpt:
            return openai.OpenAI(api_key=api_key)
        else:
            return openai.AzureOpenAI(api_key=api_key, **kw)
    except Exception as e:
        openai.api_key = api_key
        if not use_chatgpt:
            if hasattr(openai, "api_type"):
                openai.api_type = kw.get("api_type", "azure")
            else:
                try:
                    setattr(openai, "api_type", "azure")
                except Exception:
                    pass
            if "api_base" in kw and hasattr(openai, "api_base"):
                openai.api_base = kw["api_base"]
            if "api_version" in kw and hasattr(openai, "api_version"):
                openai.api_version = kw["api_version"]

        class _ChatCompletions:
            @staticmethod
            def create(**kwargs):
                if hasattr(openai, "ChatCompletion"):
                    return openai.ChatCompletion.create(**kwargs)
                if hasattr(openai, "Completion"):
                    return openai.Completion.create(**kwargs)
                raise e

        class DummyClient:
            def __init__(self):
                dummy_chat = type("ChatDummy", (), {})()
                dummy_chat.completions = _ChatCompletions
                self.chat = dummy_chat
        return DummyClient()

def _retry_call(func, max_retries: int, use_exponential_backoff: bool = True, prefix: str = "Retry", idx: Any = None):
    last_exception = None
    for attempt in range(1, max_retries + 1):
        try:
            return func()
        except Exception as e:
            last_exception = e
            if idx is not None:
                st.warning(f"[{prefix} {attempt}/{max_retries}] idx={idx} failed: {e}")
            else:
                st.warning(f"[{prefix} {attempt}/{max_retries}] failed: {e}")
            if attempt < max_retries:
                if use_exponential_backoff:
                    time.sleep(2 ** attempt)
                else:
                    time.sleep(RETRY_SLEEP)
    if last_exception:
        raise last_exception
