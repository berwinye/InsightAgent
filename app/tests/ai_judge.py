"""
AI Judge: uses the same Qwen LLM to evaluate agent responses against evaluation criteria.

Each call sends the original question, the agent's final answer, process metrics,
and the full per-turn execution history (tool inputs + outputs in order) to Qwen,
asks it to reason step-by-step, then output "Yes" (criteria met) or "No" (not met)
as the very last line.

Usage::

    from app.tests.ai_judge import ai_judge, fetch_turns

    turns = fetch_turns(client, result.get("log_id"))
    reasoning, passed = ai_judge(
        question="What is total revenue by product line?",
        result=agent_response_dict,
        criteria="The answer must include specific revenue figures for each product line.",
        turns=turns,
    )
    print(f"  AI Judge: {reasoning}")
    assert passed, f"AI Judge ruled No:\\n{reasoning}"
"""
from __future__ import annotations

import json
from typing import TYPE_CHECKING

from openai import OpenAI

from app.core.config import settings

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


_JUDGE_SYSTEM_PROMPT = (
    "You are a strict, impartial test judge evaluating a data-analysis AI agent's response. "
    "You will be given: the original question, the agent's final answer, process metrics, "
    "and the full turn-by-turn execution history (what the LLM said and what each tool returned). "
    "Your task:\n"
    "1. Carefully inspect all evidence, including tool outputs and LLM reasoning at each step.\n"
    "2. Write 2-5 sentences of reasoning.\n"
    "3. On the very last line output ONLY the word Yes or No — nothing else on that line."
)

_JUDGE_USER_TEMPLATE = """\
## Original Question
{question}

## Agent Final Answer
{answer}

## Process Metrics
- Iterations used : {iterations}
- Tool trace      : {tool_trace}

## Turn-by-Turn Execution History (in order)
{turns_section}

## Evaluation Criteria
{criteria}

Analyse all evidence above, then output Yes or No on the last line.\
"""

_MAX_TOOL_OUTPUT_CHARS = 600


def _format_turns(turns: list[dict]) -> str:
    """Render turn list into a readable block for the judge prompt."""
    if not turns:
        return "(no turn history available)"

    parts: list[str] = []
    for t in turns:
        tool = t.get("tool_name", "?")
        iteration = t.get("iteration", "?")
        header = f"[Iteration {iteration} | Tool: {tool}]"

        llm_thought = (t.get("llm_content") or "").strip()
        tool_input_raw = t.get("tool_input") or ""
        tool_output_raw = t.get("tool_output") or ""

        lines: list[str] = [header]

        if llm_thought:
            lines.append(f"  LLM thought : {llm_thought[:300]}")

        if tool == "run_python_analysis":
            try:
                inp = json.loads(tool_input_raw)
                code = (inp.get("code") or "").strip()
                lines.append(f"  Code        :\n    " + "\n    ".join(code.splitlines()[:20]))
            except Exception:
                lines.append(f"  Input       : {tool_input_raw[:200]}")
            try:
                out = json.loads(tool_output_raw)
                status = out.get("status", "?")
                data_found = out.get("data_found")
                stdout = (out.get("stdout") or "").strip()
                note = out.get("note", "")
                error_type = out.get("error_type", "")
                message = out.get("message", "")
                summary = f"status={status}"
                if data_found is not None:
                    summary += f", data_found={data_found}"
                if error_type:
                    summary += f", error_type={error_type}"
                lines.append(f"  Result      : {summary}")
                if stdout:
                    lines.append(f"  Stdout      : {stdout[:_MAX_TOOL_OUTPUT_CHARS]}")
                if note:
                    lines.append(f"  Note        : {note}")
                if message:
                    lines.append(f"  Error msg   : {message[:300]}")
            except Exception:
                lines.append(f"  Output      : {tool_output_raw[:_MAX_TOOL_OUTPUT_CHARS]}")

        elif tool == "observe_schema":
            lines.append(f"  Output      : (schema — {len(tool_output_raw)} chars, truncated)")

        elif tool == "final_answer":
            answer_val = tool_input_raw or tool_output_raw
            lines.append(f"  Answer      : {answer_val[:400]}")

        else:
            if tool_output_raw:
                lines.append(f"  Output      : {tool_output_raw[:_MAX_TOOL_OUTPUT_CHARS]}")

        parts.append("\n".join(lines))

    return "\n\n".join(parts)


def fetch_turns(client: "TestClient", log_id: int | None) -> list[dict]:
    """Fetch per-turn execution details for an analysis run via the API."""
    if not log_id:
        return []
    resp = client.get(f"/analytics/logs/{log_id}/turns")
    if resp.status_code == 200:
        return resp.json()
    return []


def ai_judge(
    question: str,
    result: dict,
    criteria: str,
    turns: list[dict] | None = None,
) -> tuple[str, bool]:
    """
    Call the Qwen LLM to judge whether *result* satisfies *criteria*.

    Parameters
    ----------
    question  : The original natural-language question posed to the agent.
    result    : The full JSON dict returned by POST /analytics/analyze.
    criteria  : Plain-English description of what "passing" looks like.
    turns     : Per-turn history from GET /analytics/logs/{log_id}/turns (optional).

    Returns
    -------
    (reasoning, passed)
        reasoning – judge's explanation (everything except the final verdict line)
        passed    – True if the last non-empty line starts with "Yes" (case-insensitive)
    """
    llm = OpenAI(api_key=settings.QWEN_API_KEY, base_url=settings.QWEN_BASE_URL)

    turns_section = _format_turns(turns or [])

    prompt = _JUDGE_USER_TEMPLATE.format(
        question=question,
        answer=result.get("answer") or "(empty)",
        iterations=result.get("iterations", 0),
        tool_trace=" → ".join(result.get("tool_trace") or []),
        turns_section=turns_section,
        criteria=criteria,
    )

    response = llm.chat.completions.create(
        model=settings.QWEN_MODEL,
        messages=[
            {"role": "system", "content": _JUDGE_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0,
        max_tokens=600,
    )

    full_text = (response.choices[0].message.content or "").strip()
    lines = [ln.strip() for ln in full_text.splitlines() if ln.strip()]

    if not lines:
        return "(judge returned empty response)", False

    verdict_line = lines[-1].upper()
    passed = verdict_line.startswith("YES")
    reasoning = "\n".join(lines[:-1]) if len(lines) > 1 else "(no reasoning provided)"

    return reasoning, passed
