"""
Where an answer comes from.

Two providers, one interface. `replay` serves the reference outputs committed
alongside each tool; `claude` calls the model for real. Everything downstream --
contract check, review policy, audit line -- is identical either way, which is
the point: the pipeline you demo offline is the pipeline that runs in anger.

Be clear about what `replay` is and is not. The fixtures are hand-authored
reference outputs -- the answer key -- not recordings of model responses. Replay
mode proves the harness works and lets anyone run this with no credentials. It
does not tell you how good the model is. For that, run `--provider claude` and
then `opsq score`, which grades the live run against those same fixtures.
"""

from __future__ import annotations

import json
import time


class ProviderError(Exception):
    pass


class ReplayProvider:
    """Serves committed reference outputs. No network, no credentials, no cost."""

    name = "replay"

    def complete(self, tool, input_id: str, system: str, user_prompt: str) -> tuple[dict, dict]:
        path = tool.fixture(input_id)
        if not path.exists():
            raise ProviderError(
                f"no fixture for {input_id} in {tool.id}. Replay can only serve inputs "
                f"that have a committed reference output -- add {path.name} or use "
                f"--provider claude."
            )
        started = time.perf_counter()
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload, {
            "provider": "replay",
            "model": "n/a",
            "latency_ms": round((time.perf_counter() - started) * 1000, 1),
            "usage": None,
            "refused": False,
        }


class ClaudeProvider:
    """Live model run.

    The output schema is passed as `output_config.format`, so the model is
    constrained at generation time; the harness re-checks it afterwards anyway.

    On a policy refusal this returns `refused` rather than retrying on a
    different model. In a regulated case-handling context a refused case is a
    case a human should look at -- silently rerouting it to a fallback model
    would bury exactly the signal an operator needs. (The API does offer
    server-side fallbacks; it is a deliberate decision not to use them here, and
    it is recorded in GOVERNANCE.md.)
    """

    name = "claude"

    def __init__(self, model: str | None = None):
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover
            raise ProviderError(
                "live runs need the SDK: pip install anthropic  "
                "(the offline demo does not: use --provider replay)"
            ) from exc
        self._client = anthropic.Anthropic()
        self._override = model

    # Structured outputs accept a subset of JSON Schema. These keywords are
    # either meta-information about the file or constraints the API does not
    # enforce at generation time, and sending them is a 400.
    API_UNSUPPORTED = frozenset({
        "$schema", "maxItems", "minItems", "maxLength", "minLength",
        "minimum", "maximum", "format", "default", "examples",
    })

    @classmethod
    def _api_schema(cls, node):
        """Strip what the API will not accept, keeping the load-bearing parts:
        types, enums, required, closed objects, and descriptions.

        The schema on disk stays the full contract. The API gets the subset it
        can enforce while generating; the harness re-checks the rest locally on
        the way back. That is not belt and braces for its own sake -- it is the
        difference between "the platform validated it" and being able to show a
        governance team where the check happens.

        A length or count that the API cannot enforce is still enforced here, and
        a breach lands as `schema_violation` and goes to a human. Where such a
        limit matters to the output, the prompt states it in words as well.
        """
        if isinstance(node, dict):
            return {k: cls._api_schema(v) for k, v in node.items()
                    if k not in cls.API_UNSUPPORTED}
        if isinstance(node, list):
            return [cls._api_schema(v) for v in node]
        return node

    def complete(self, tool, input_id: str, system: str, user_prompt: str) -> tuple[dict, dict]:
        model = self._override or tool.meta["model"]
        started = time.perf_counter()
        response = self._client.messages.create(
            model=model,
            # Thinking tokens count towards max_tokens. A triage decision is
            # short, but the reasoning before it is not, and a truncated response
            # would surface here as a schema violation rather than as the
            # budgeting mistake it actually is.
            max_tokens=16000,
            system=system,
            messages=[{"role": "user", "content": user_prompt}],
            thinking={"type": "adaptive"},
            output_config={
                "effort": tool.meta.get("effort", "medium"),
                "format": {"type": "json_schema", "schema": self._api_schema(tool.schema)},
            },
        )
        latency = round((time.perf_counter() - started) * 1000, 1)
        if response.stop_reason == "max_tokens":
            raise ProviderError(
                f"{input_id}: response hit max_tokens and was cut off. Raise it, "
                f"or lower `effort` in {tool.id}/TOOL.md."
            )
        usage = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }

        if response.stop_reason == "refusal":
            detail = getattr(response, "stop_details", None)
            return {}, {
                "provider": "claude", "model": model, "latency_ms": latency,
                "usage": usage, "refused": True,
                "refusal_category": getattr(detail, "category", None),
            }

        text = next((b.text for b in response.content if b.type == "text"), None)
        if text is None:
            raise ProviderError(f"{input_id}: response contained no text block")
        return json.loads(text), {
            "provider": "claude", "model": model, "latency_ms": latency,
            "usage": usage, "refused": False,
        }


def get(name: str, model: str | None = None):
    if name == "replay":
        return ReplayProvider()
    if name == "claude":
        return ClaudeProvider(model)
    raise ProviderError(f"unknown provider {name!r} (expected: replay, claude)")
