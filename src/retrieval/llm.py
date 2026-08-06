from __future__ import annotations

from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

from core.config import Settings, normalized_provider, require_llm_credentials


def build_llm(settings: Settings, temperature: float = 0.0):
    """Dung chat model theo provider dang cau hinh trong `.env`.

    Moi provider deu duoc gioi han do dai output bang `settings.max_output_tokens`.
    Khong de trong: mot so gateway (OpenRouter) uoc luong chi phi theo
    max_completion_tokens cua model chu khong theo do dai thuc te, nen request
    khong dat gioi han se bi tu choi bang HTTP 402 du so du du de tra loi.
    Ten tham so khac nhau giua cac SDK nen phai truyen rieng cho tung provider.
    """
    provider = normalized_provider(settings)
    require_llm_credentials(settings)
    max_tokens = settings.max_output_tokens

    if provider == "gemini":
        return ChatGoogleGenerativeAI(
            model=settings.model_name,
            google_api_key=settings.google_api_key,
            temperature=temperature,
            max_output_tokens=max_tokens,
        )
    if provider == "openai":
        return ChatOpenAI(
            model=settings.model_name,
            api_key=settings.openai_api_key,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    if provider == "anthropic":
        return ChatAnthropic(
            model=settings.model_name,
            api_key=settings.anthropic_api_key,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    if provider == "openrouter":
        return ChatOpenAI(
            model=settings.model_name,
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    if provider == "ollama":
        return ChatOllama(
            model=settings.model_name,
            base_url=settings.ollama_base_url,
            temperature=temperature,
            num_predict=max_tokens,
        )
    if provider == "custom":
        return ChatOpenAI(
            model=settings.model_name,
            api_key=settings.custom_llm_api_key or "unused",
            base_url=settings.custom_llm_base_url,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    raise RuntimeError(f"Unsupported LLM provider: {settings.llm_provider}")
