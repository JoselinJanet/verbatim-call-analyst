"""
Thin wrapper around llama-cpp-python for local Qwen inference.

The model is ONLY ever asked to return:
  - short free-text (an answer summary, a theme description), and/or
  - sentence IDs it selects as evidence.

It is never asked to reproduce quote text or timestamps itself -
those are always looked up in code from the parsed transcript
(see core/verifier.py). This is what keeps quotes verbatim.
"""
import json
import re
from pathlib import Path
from typing import Optional

from config import (
    LLM_REPO_ID, LLM_FILENAME, LLM_LOCAL_DIR, LLM_N_CTX,
    LLM_N_THREADS, LLM_TEMPERATURE, LLM_MAX_RETRIES,
)

_llm_instance = None


def get_llm():
    """Lazily download (if needed) and load the local GGUF model."""
    global _llm_instance
    if _llm_instance is not None:
        return _llm_instance

    from huggingface_hub import hf_hub_download
    from llama_cpp import Llama

    LLM_LOCAL_DIR.mkdir(parents=True, exist_ok=True)
    model_path = LLM_LOCAL_DIR / LLM_FILENAME
    if not model_path.exists():
        downloaded_path = hf_hub_download(
            repo_id=LLM_REPO_ID,
            filename=LLM_FILENAME,
            local_dir=str(LLM_LOCAL_DIR),
        )
        model_path = Path(downloaded_path)

    print(f"[llm] Loading model into memory: {model_path.name} (this can take 10s-2min on CPU)...")
    _llm_instance = Llama(
        model_path=str(model_path),
        n_ctx=LLM_N_CTX,
        n_threads=LLM_N_THREADS,
        verbose=False,
    )
    print("[llm] Model loaded. Ready for inference.")
    return _llm_instance


def _extract_json(raw: str) -> Optional[dict]:
    """Best-effort extraction of a JSON object from model output."""
    raw = raw.strip()
    raw = re.sub(r"^```json\s*|\s*```$", "", raw, flags=re.MULTILINE)
    raw = re.sub(r"^```\s*|\s*```$", "", raw, flags=re.MULTILINE)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    # fallback: grab the first {...} block
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    return None


def generate_json(
    system_prompt: str,
    user_prompt: str,
    max_retries: int = LLM_MAX_RETRIES,
    max_tokens: int = 800,
) -> Optional[dict]:
    """
    Calls the local LLM and parses a JSON object from its reply.
    Retries with an increasingly strict reminder if parsing fails.
    Returns None if all retries are exhausted (caller must handle this
    as a "generation failed" state rather than guessing).

    max_tokens matters more than it looks: if the model's JSON reply gets
    cut off mid-object because the cap was too low, json.loads() fails and
    this looks identical to "the model wrote bad JSON" - but it's actually
    "the model was never allowed to finish." Callers with larger expected
    outputs (e.g. synthesis, which returns multiple themes/disagreements
    with descriptions) should pass a higher max_tokens than a single
    short-answer call needs.
    """
    llm = get_llm()
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    for attempt in range(max_retries):
        response = llm.create_chat_completion(
            messages=messages,
            temperature=LLM_TEMPERATURE,
            max_tokens=max_tokens,
        )
        raw = response["choices"][0]["message"]["content"]
        finish_reason = response["choices"][0].get("finish_reason")
        parsed = _extract_json(raw)
        if parsed is not None:
            return parsed

        if finish_reason == "length":
            print(
                f"[llm] Attempt {attempt + 1}/{max_retries}: reply was CUT OFF at "
                f"max_tokens={max_tokens} before finishing (finish_reason=length). "
                f"Increase max_tokens for this call if this keeps happening."
            )
        else:
            print(f"[llm] Attempt {attempt + 1}/{max_retries}: model did not return valid JSON, retrying...")
            print(f"[llm] Raw output was: {raw[:300]!r}")

        # tighten the instruction and retry
        messages.append({"role": "assistant", "content": raw})
        messages.append({
            "role": "user",
            "content": "That was not valid JSON. Reply with ONLY a single valid JSON object, "
                        "no prose, no markdown fences.",
        })

    return None