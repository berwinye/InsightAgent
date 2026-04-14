"""
AI Judge: uses the same Qwen LLM to evaluate agent responses against evaluation criteria.

Each call sends the original question, agent answer, and process data to Qwen,
asks it to reason step-by-step, then output "Yes" (criteria met) or "No" (not met)
as the very last line.

Usage::

    from app.tests.ai_judge import ai_judge

    reasoning, passed = ai_judge(
        question="What is total revenue by product line?",
        result=agent_response_dict,
        criteria="The answer must include specific revenue figures for each product line.",
    )
    print(f"  AI Judge: {reasoning}")
    assert passed, f"AI Judge ruled No:\\n{reasoning}"
"""
from openai import OpenAI

from app.core.config import settings


_JUDGE_SYSTEM_PROMPT = (
    "You are a strict, impartial test judge evaluating a data-analysis AI agent's response. "
    "You will be given the original question, the agent's final answer, key process metrics "
    "(iterations, tool trace, generated code), and a set of evaluation criteria. "
    "Your task:\n"
    "1. Carefully inspect the evidence.\n"
    "2. Write 2-4 sentences of reasoning.\n"
    "3. On the very last line output ONLY the word Yes or No — nothing else on that line."
)

_JUDGE_USER_TEMPLATE = """\
## Original Question
{question}

## Agent Answer
{answer}

## Process Data
- Iterations used : {iterations}
- Tool trace      : {tool_trace}
- Generated code  :
```python
{generated_code}
```

## Evaluation Criteria
{criteria}

State your reasoning, then output Yes or No on the last line.\
"""


def ai_judge(question: str, result: dict, criteria: str) -> tuple[str, bool]:
    """
    Call the Qwen LLM to judge whether *result* satisfies *criteria*.

    Parameters
    ----------
    question  : The original natural-language question posed to the agent.
    result    : The full JSON dict returned by POST /analytics/analyze.
    criteria  : Plain-English description of what "passing" looks like.

    Returns
    -------
    (reasoning, passed)
        reasoning – judge's explanation (everything except the final verdict line)
        passed    – True if the last non-empty line starts with "Yes" (case-insensitive)
    """
    client = OpenAI(api_key=settings.QWEN_API_KEY, base_url=settings.QWEN_BASE_URL)

    prompt = _JUDGE_USER_TEMPLATE.format(
        question=question,
        answer=result.get("answer") or "(empty)",
        iterations=result.get("iterations", 0),
        tool_trace=" → ".join(result.get("tool_trace") or []),
        generated_code=result.get("generated_code") or "(none)",
        criteria=criteria,
    )

    response = client.chat.completions.create(
        model=settings.QWEN_MODEL,
        messages=[
            {"role": "system", "content": _JUDGE_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0,
        max_tokens=512,
    )

    full_text = (response.choices[0].message.content or "").strip()
    lines = [ln.strip() for ln in full_text.splitlines() if ln.strip()]

    if not lines:
        return "(judge returned empty response)", False

    verdict_line = lines[-1].upper()
    passed = verdict_line.startswith("YES")
    reasoning = "\n".join(lines[:-1]) if len(lines) > 1 else "(no reasoning provided)"

    return reasoning, passed
