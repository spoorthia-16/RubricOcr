import os
import time
import json
import uuid
import logging
import requests
from typing import List, Dict, Any, Optional

try:
    from .config import (
        AZURE_OPENAI_API_KEY,
        AZURE_OPENAI_ENDPOINT,
        AZURE_OPENAI_DEPLOYMENT,
        AZURE_OPENAI_API_VERSION,
        ENABLE_LLM_CORRECTION,
        TEMPERATURE,
        MAX_TOKENS,
        TOP_P,
    )
except ImportError:
    from config import (
        AZURE_OPENAI_API_KEY,
        AZURE_OPENAI_ENDPOINT,
        AZURE_OPENAI_DEPLOYMENT,
        AZURE_OPENAI_API_VERSION,
        ENABLE_LLM_CORRECTION,
        TEMPERATURE,
        MAX_TOKENS,
        TOP_P,
    )

# Setup Logging
log_dir = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(log_dir, "llm_client.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("LLMClient")

debug_dir = os.path.join(os.path.dirname(__file__), "..", "..", "debug", "llm")
os.makedirs(debug_dir, exist_ok=True)


class BaseTransport:
    """Abstract transport layer to allow swapping providers."""

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        raise NotImplementedError("Transport must implement chat()")


class AzureOpenAITransport(BaseTransport):
    """
    Azure OpenAI Transport supporting official OpenAI Python SDK & HTTP REST fallback.
    Target Endpoint: {endpoint}/openai/deployments/{deployment}/chat/completions?api-version={api_version}
    Header: api-key: {key}
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None,
        deployment: Optional[str] = None,
        api_version: Optional[str] = None,
    ):
        self.api_key = api_key or AZURE_OPENAI_API_KEY
        self.endpoint = (endpoint or AZURE_OPENAI_ENDPOINT).rstrip("/")
        self.deployment = deployment or AZURE_OPENAI_DEPLOYMENT
        self.api_version = api_version or AZURE_OPENAI_API_VERSION

        # Attempt to initialize AzureOpenAI SDK client if available
        self.sdk_client = None
        try:
            from openai import AzureOpenAI

            if self.api_key:
                self.sdk_client = AzureOpenAI(
                    api_key=self.api_key,
                    api_version=self.api_version,
                    azure_endpoint=self.endpoint,
                )
        except Exception as e:
            logger.debug(f"AzureOpenAI SDK client initialization notice: {e}")

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        temp = kwargs.get("temperature", TEMPERATURE)
        max_tok = kwargs.get("max_tokens", MAX_TOKENS)
        top_p = kwargs.get("top_p", TOP_P)

        # 1. Try SDK Client if initialized
        if self.sdk_client:
            try:
                response = self.sdk_client.chat.completions.create(
                    model=self.deployment,
                    messages=messages,
                    temperature=temp,
                    max_tokens=max_tok,
                    top_p=top_p,
                )

                choices_list = []
                for choice in response.choices:
                    choices_list.append(
                        {"message": {"content": choice.message.content or ""}}
                    )

                usage_dict = {
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0,
                }

                return {"choices": choices_list, "usage": usage_dict}
            except Exception as sdk_err:
                logger.warning(
                    f"Azure SDK call error: {sdk_err}. Trying REST API fallback..."
                )

        # 2. Direct HTTP REST API Fallback
        url = f"{self.endpoint}/openai/deployments/{self.deployment}/chat/completions?api-version={self.api_version}"
        headers = {
            "Content-Type": "application/json",
            "api-key": self.api_key,
        }
        payload = {
            "messages": messages,
            "temperature": temp,
            "max_tokens": max_tok,
            "top_p": top_p,
        }

        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        if resp.status_code != 200:
            raise Exception(f"Azure OpenAI HTTP {resp.status_code}: {resp.text}")

        return resp.json()


class LLMClient:
    """Generic LLM Client handling retries, timeouts, logging, and performance metrics for Azure OpenAI."""

    def __init__(self, transport: Optional[BaseTransport] = None):
        if transport is None:
            self.transport = AzureOpenAITransport()
        else:
            self.transport = transport

        # Print/Log Startup Information
        startup_msg = (
            f"LLM Provider      : Azure OpenAI\n"
            f"Endpoint          : {AZURE_OPENAI_ENDPOINT}\n"
            f"Deployment        : {AZURE_OPENAI_DEPLOYMENT}\n"
            f"LLM Enabled       : {ENABLE_LLM_CORRECTION}"
        )
        print(f"\n{startup_msg}\n")
        logger.info(startup_msg.replace("\n", " | "))

    def _save_debug(self, prefix: str, data: Any) -> None:
        """Saves exact request/response to disk for debugging."""
        request_id = str(uuid.uuid4())[:8]
        filename = os.path.join(debug_dir, f"{prefix}_{request_id}.json")
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save debug file {filename}: {e}")

    def chat_with_metadata(
        self, messages: List[Dict[str, str]], temperature: float = TEMPERATURE
    ) -> Dict[str, Any]:
        """
        Sends messages to Azure OpenAI and returns response content along with metadata
        (latency, tokens, retry counts, transport flags).
        """
        self._save_debug("request", messages)

        start_time = time.time()
        max_retries = 3
        retry_count = 0
        transport_meta = {"timeout": False, "rate_limit": False, "error": None}

        for attempt in range(max_retries):
            try:
                logger.info(f"Sending request to Azure OpenAI (Attempt {attempt + 1})")

                response = self.transport.chat(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=MAX_TOKENS,
                    top_p=TOP_P,
                )

                latency = time.time() - start_time
                usage = response.get("usage", {})
                prompt_tokens = usage.get("prompt_tokens", 0)
                completion_tokens = usage.get("completion_tokens", 0)
                total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)

                content = ""
                if "choices" in response and len(response["choices"]) > 0:
                    content = response["choices"][0]["message"]["content"]

                logger.info(
                    f"LLM Success | Latency: {latency:.2f}s | "
                    f"Tokens: Prompt={prompt_tokens} Completion={completion_tokens} Total={total_tokens}"
                )

                self._save_debug("response", response)

                return {
                    "content": content,
                    "latency": round(latency, 4),
                    "retry_count": retry_count,
                    "tokens": {
                        "input_tokens": prompt_tokens,
                        "output_tokens": completion_tokens,
                        "total_tokens": total_tokens,
                    },
                    "transport_meta": transport_meta,
                    "model": AZURE_OPENAI_DEPLOYMENT,
                }
            except TimeoutError as te:
                transport_meta["timeout"] = True
                logger.warning(f"LLM API Timeout on attempt {attempt + 1}: {str(te)}")
                if attempt == max_retries - 1:
                    return {
                        "content": "",
                        "latency": round(time.time() - start_time, 4),
                        "retry_count": retry_count,
                        "tokens": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
                        "transport_meta": transport_meta,
                        "model": AZURE_OPENAI_DEPLOYMENT,
                    }
                retry_count += 1
                time.sleep(2 ** attempt)
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "rate_limit" in err_str.lower():
                    transport_meta["rate_limit"] = True
                logger.warning(f"LLM API Error on attempt {attempt + 1}: {err_str}")
                if attempt == max_retries - 1:
                    transport_meta["error"] = err_str
                    return {
                        "content": "",
                        "latency": round(time.time() - start_time, 4),
                        "retry_count": retry_count,
                        "tokens": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
                        "transport_meta": transport_meta,
                        "model": AZURE_OPENAI_DEPLOYMENT,
                    }
                retry_count += 1
                time.sleep(2 ** attempt)

        return {
            "content": "",
            "latency": round(time.time() - start_time, 4),
            "retry_count": retry_count,
            "tokens": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
            "transport_meta": transport_meta,
            "model": AZURE_OPENAI_DEPLOYMENT,
        }

    def chat(self, messages: List[Dict[str, str]], temperature: float = TEMPERATURE) -> str:
        """Sends messages to Azure OpenAI and returns raw response content string."""
        res = self.chat_with_metadata(messages, temperature=temperature)
        return res["content"]
