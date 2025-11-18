# LLMClient.py
from dataclasses import dataclass
from typing import Optional, Dict, Any

import requests

try:
    from openai import OpenAI
except Exception:
    OpenAI = None


@dataclass
class LLMClient:
    """
    Generic LLM client for PBJ.

    provider:
      - "openai"     -> uses OpenAI Chat Completions API
      - "local_http" -> calls an OpenAI-compatible /v1/chat/completions endpoint
                        (e.g., llama_cpp.server, vLLM, etc.)
    """

    provider: str = "openai"
    api_key: Optional[str] = None
    model: str = "gpt-4o-mini"
    temperature: float = 0.7
    max_output_tokens: int = 2048

    # for local_http
    base_url: Optional[str] = None     # e.g. "http://localhost:8001/v1/chat/completions"
    extra_headers: Optional[Dict[str, str]] = None

    def run_prompt(self, prompt: str) -> str:
        if self.provider == "openai":
            return self._run_openai(prompt)
        elif self.provider == "local_http":
            return self._run_local_http(prompt)
        else:
            raise NotImplementedError(f"Provider '{self.provider}' not supported.")

    # ---------- OpenAI ----------
    def _run_openai(self, prompt: str) -> str:
        if OpenAI is None:
            raise RuntimeError("openai package not installed. Run `pip install openai`.")
        if not self.api_key:
            raise ValueError("Missing OpenAI API key.")

        client = OpenAI(api_key=self.api_key)
        resp = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature,
            max_tokens=self.max_output_tokens,
        )
        content = resp.choices[0].message.content
        return content.strip() if content else ""

    # ---------- Local HTTP (Llama3, Gemma, etc.) ----------
    def _run_local_http(self, prompt: str) -> str:
        """
        Calls a local OpenAI-compatible server:
        POST base_url
        {
          "model": "...",
          "messages": [{"role": "user", "content": prompt}],
          ...
        }
        """
        if not self.base_url:
            raise ValueError("base_url must be set for provider='local_http'.")

        headers: Dict[str, str] = {
            "Content-Type": "application/json",
        }
        if self.extra_headers:
            headers.update(self.extra_headers)

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
            "max_tokens": self.max_output_tokens,
        }

        resp = requests.post(self.base_url, json=payload, headers=headers, timeout=120)
        resp.raise_for_status()
        data = resp.json()

        # Assume OpenAI-style response
        content = data["choices"][0]["message"]["content"]
        return content.strip() if content else ""
