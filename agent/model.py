import json
import os
import time
import httpx
from core.settings import ROOT, config
from core.telemetry import span


async def generate(node, data, trace_id, schema=None):
    """Explicit deterministic test mode is never counted as an open-model experiment."""
    if os.getenv("GIGBID_MODEL_MODE", "ollama") == "test":
        return {
            "output": {},
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "seconds": 0,
            "usd": 0,
            "model": "deterministic-test-double",
        }
    cfg = config()["models"]
    profile = cfg["profiles"][cfg["profile"]]
    if profile.get("enabled") is False:
        raise RuntimeError("Selected model profile is disabled")
    model = profile[cfg["nodes"].get(node, "router")]
    prompt = (ROOT / f"agent/prompts/{node}.v1.md").read_text(encoding="utf-8")
    schemas = {
        "writer": {
            "type": "object",
            "properties": {"plan": {"type": "string", "maxLength": 700}},
            "required": ["plan"],
            "additionalProperties": False,
        },
        "analyst": {
            "type": "object",
            "properties": {"hidden_needs": {"type": "array", "items": {"type": "string"}, "maxItems": 4}},
            "required": ["hidden_needs"],
            "additionalProperties": False,
        },
        "critic": {
            "type": "object",
            "properties": {
                "issues": {"type": "array", "items": {"type": "string"}, "maxItems": 3},
                "suggestions": {"type": "array", "items": {"type": "string"}, "maxItems": 3},
            },
            "required": ["issues", "suggestions"],
            "additionalProperties": False,
        },
        "liaison": {
            "type": "object",
            "properties": {"plan": {"type": "string"}},
            "required": ["plan"],
            "additionalProperties": False,
        },
    }
    payload = {
        "model": model,
        "stream": False,
        "messages": [
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": "<untrusted_data>\n" + json.dumps(data, ensure_ascii=False) + "\n</untrusted_data>",
            },
        ],
        "format": schema or schemas.get(node, "json"),
        "options": {"temperature": 0, "seed": 4016, "num_ctx": 4096, "num_predict": 450},
        "keep_alive": "10m",
    }
    start = time.perf_counter()
    with span("llm." + node, trace_id, model=model) as llm_span:
        async with httpx.AsyncClient(timeout=180) as client:
            response = await client.post(os.getenv("OLLAMA_URL", "http://127.0.0.1:11434") + "/api/chat", json=payload)
            response.raise_for_status()
            result = response.json()
            llm_span.set_attribute("gen_ai.usage.input_tokens", result.get("prompt_eval_count", 0))
            llm_span.set_attribute("gen_ai.usage.output_tokens", result.get("eval_count", 0))
            llm_span.set_attribute("gigbid.api_cost_usd", 0)
    try:
        output = json.loads(result["message"]["content"])
    except (json.JSONDecodeError, KeyError) as e:
        raise ValueError(f"{model} returned invalid structured output for {node}") from e
    return {
        "output": output,
        "prompt_tokens": result.get("prompt_eval_count", 0),
        "completion_tokens": result.get("eval_count", 0),
        "seconds": time.perf_counter() - start,
        "usd": 0,
        "model": model,
        "eval_duration_ns": result.get("eval_duration", 0),
    }
