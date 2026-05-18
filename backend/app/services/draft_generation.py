"""
Marketing draft generation — supports Claude and Gemini.
Switched via LLM_PROVIDER env var ("claude" | "gemini").
"""
import structlog
from app.config import get_settings

log = structlog.get_logger()
settings = get_settings()

_SYSTEM_PROMPT = """You are a professional marketing copywriter.
Given a transcript of a product or event recording, produce a compelling marketing draft.

Structure it as:
1. Attention-grabbing headline
2. Executive summary (2–3 sentences)
3. Key highlights (bullet points)
4. Call to action

Return only the draft — no meta-commentary."""


def generate_draft(transcript: str, event_title: str) -> dict:
    """
    Generate a marketing draft from a transcript.
    Dispatches to the configured LLM provider.
    Returns dict: content, model, prompt_tokens, completion_tokens.
    """
    provider = settings.llm_provider.lower()
    if provider == "claude":
        return _generate_claude(transcript, event_title)
    if provider == "gemini":
        return _generate_gemini(transcript, event_title)
    raise ValueError(f"Unknown LLM_PROVIDER: {provider!r}. Use 'claude' or 'gemini'.")


# ---------------------------------------------------------------------------
# Claude
# ---------------------------------------------------------------------------

def _generate_claude(transcript: str, event_title: str) -> dict:
    import anthropic
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    user_message = f"Event: {event_title}\n\nTranscript:\n{transcript}"

    log.info("generating_draft", provider="claude", model=settings.anthropic_model)
    message = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=2048,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )
    content: str = message.content[0].text
    log.info("draft_generated", provider="claude", chars=len(content))
    return {
        "content": content,
        "model": message.model,
        "prompt_tokens": message.usage.input_tokens,
        "completion_tokens": message.usage.output_tokens,
    }


# ---------------------------------------------------------------------------
# Gemini
# ---------------------------------------------------------------------------

def _generate_gemini(transcript: str, event_title: str) -> dict:
    import google.generativeai as genai

    # Prefer an explicit API key; fall back to ADC (works on Cloud Run automatically).
    if settings.gemini_api_key:
        genai.configure(api_key=settings.gemini_api_key)

    model = genai.GenerativeModel(
        model_name=settings.gemini_model,
        system_instruction=_SYSTEM_PROMPT,
    )
    prompt = f"Event: {event_title}\n\nTranscript:\n{transcript}"

    log.info("generating_draft", provider="gemini", model=settings.gemini_model)
    response = model.generate_content(
        prompt,
        generation_config=genai.GenerationConfig(max_output_tokens=2048),
    )
    content: str = response.text
    usage = response.usage_metadata
    log.info("draft_generated", provider="gemini", chars=len(content))
    return {
        "content": content,
        "model": settings.gemini_model,
        "prompt_tokens": usage.prompt_token_count,
        "completion_tokens": usage.candidates_token_count,
    }
