"""
LLM Agent self-loop for natural language data analysis.

Workflow:
  1. Receive user's natural language question.
  2. Call observe_schema to obtain DB context.
  3. Ask Qwen to generate Python analysis code.
  4. Call run_python_analysis.
  5. Feed result / error back to Qwen for refinement.
  6. Repeat up to MAX_ITERATIONS.
  7. Return final_answer when agent calls the stop function.
"""
import json
import logging
from typing import Any, Optional

from openai import (
    OpenAI,
    APIConnectionError,
    APITimeoutError,
    RateLimitError,
    AuthenticationError,
    BadRequestError,
    InternalServerError,
    APIStatusError,
    APIError,
)
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.analysis_logs import AnalysisLog
from app.models.agent_turn import AgentTurn
from app.services.skills.observe_schema import observe_schema
from app.services.skills.run_python_analysis import run_python_analysis

_MAX_OUTPUT_CHARS = 12_000

logger = logging.getLogger(__name__)

MAX_ITERATIONS = settings.AGENT_MAX_ITERATIONS

SYSTEM_PROMPT = """You are an expert data analyst working with a MySQL database called enterprise_api.
The database contains the classic models sales dataset with tables:
employees, offices, customers, orders, orderdetails, products, productlines, payments,
saved_queries, analysis_logs.

You have access to three tools:
1. observe_schema  – get the full database schema (tables, columns, PKs, FKs).
2. run_python_analysis – execute Python code in a sandbox. The sandbox provides:
   - read_sql(sql, params=(), max_rows=50000) -> pandas.DataFrame
   - pandas (as pd), numpy (as np), math, statistics, datetime, re
   - Results MUST be output via print(). The final result variable is optional.
   - Only SELECT / WITH SQL is permitted.
3. final_answer – call this to return your conclusive answer to the user.

Strategy:
- Always call observe_schema first to understand available tables.
- Write clean, focused Python code that uses read_sql() and prints the result.
- If run_python_analysis returns an error, read it carefully, fix the code, and retry.
- If run_python_analysis returns data_found=false, the query succeeded with 0 rows — state that as your finding and call final_answer.
- When the analysis is complete and you have a clear answer, call final_answer.
- You MUST call final_answer within {max_iter} iterations.
- Do not invent data; derive all figures from query results.
""".format(max_iter=MAX_ITERATIONS)

TOOLS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "observe_schema",
            "description": "Retrieve the full database schema including all tables, columns, primary keys and foreign keys.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_python_analysis",
            "description": (
                "Execute Python analysis code in a sandboxed environment. "
                "The sandbox provides read_sql(), pandas, numpy, math, statistics. "
                "All output must be produced via print(). Returns stdout or a structured error."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Valid Python source code to execute.",
                    }
                },
                "required": ["code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "final_answer",
            "description": "Stop the analysis loop and return the final answer to the user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "answer": {
                        "type": "string",
                        "description": "The complete, well-formatted answer to the user's question.",
                    }
                },
                "required": ["answer"],
            },
        },
    },
]


def _dispatch_tool(name: str, args: dict[str, Any]) -> str:
    if name == "observe_schema":
        schema = observe_schema()
        return json.dumps(schema, ensure_ascii=False)
    elif name == "run_python_analysis":
        result = run_python_analysis(args.get("code", ""))
        return json.dumps(result, ensure_ascii=False)
    elif name == "final_answer":
        return args.get("answer", "")
    else:
        return json.dumps({"error": f"Unknown tool: {name}"})


def _save_turn(
    db: Optional[Session],
    log_id: int,
    iteration: int,
    tool_name: str,
    llm_content: Optional[str],
    tool_input: Optional[str],
    tool_output: Optional[str],
) -> None:
    if db is None:
        return
    turn = AgentTurn(
        log_id=log_id,
        iteration=iteration,
        tool_name=tool_name,
        llm_content=llm_content[:_MAX_OUTPUT_CHARS] if llm_content else None,
        tool_input=tool_input[:_MAX_OUTPUT_CHARS] if tool_input else None,
        tool_output=tool_output[:_MAX_OUTPUT_CHARS] if tool_output else None,
    )
    db.add(turn)
    db.commit()


def analyze_question(question: str, db: Optional[Session] = None) -> dict[str, Any]:
    """Run the agent self-loop, persist every turn, and return the final answer."""
    client = OpenAI(
        api_key=settings.QWEN_API_KEY,
        base_url=settings.QWEN_BASE_URL,
    )

    log_id: Optional[int] = None
    if db is not None:
        log = AnalysisLog(query_text=question, status="running")
        db.add(log)
        db.commit()
        db.refresh(log)
        log_id = log.id

    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]

    last_code: str | None = None
    final_ans: str | None = None
    prev_error: str | None = None
    repeated_error_count = 0
    tool_trace: list[str] = []

    for iteration in range(1, MAX_ITERATIONS + 1):
        logger.info("Agent iteration %d/%d", iteration, MAX_ITERATIONS)

        force_final = iteration >= MAX_ITERATIONS - 1
        tool_choice: Any = (
            {"type": "function", "function": {"name": "final_answer"}}
            if force_final
            else "auto"
        )
        if force_final:
            logger.info("Forcing final_answer on iteration %d", iteration)

        try:
            response = client.chat.completions.create(
                model=settings.QWEN_MODEL,
                messages=messages,
                tools=TOOLS,
                tool_choice=tool_choice,
            )
        except APIConnectionError as exc:
            final_ans = f"LLM error: Network connection failed. Check network settings. Detail: {exc}"
            logger.error("LLM APIConnectionError: %s", exc)
            break
        except APITimeoutError as exc:
            final_ans = f"LLM error: Request timed out. Detail: {exc}"
            logger.error("LLM APITimeoutError: %s", exc)
            break
        except RateLimitError as exc:
            final_ans = f"LLM error: Rate limit exceeded (429). Detail: {exc}"
            logger.error("LLM RateLimitError: %s", exc)
            break
        except AuthenticationError as exc:
            final_ans = f"LLM error: Authentication failed. Check QWEN_API_KEY. Detail: {exc}"
            logger.error("LLM AuthenticationError: %s", exc)
            break
        except BadRequestError as exc:
            final_ans = f"LLM error: Bad request (400), possibly context too long. Detail: {exc}"
            logger.error("LLM BadRequestError: %s", exc)
            break
        except InternalServerError as exc:
            final_ans = f"LLM error: LLM service internal error (500). Detail: {exc}"
            logger.error("LLM InternalServerError: %s", exc)
            break
        except APIStatusError as exc:
            final_ans = f"LLM error: API returned HTTP {exc.status_code}. Detail: {exc.message}"
            logger.error("LLM APIStatusError %s: %s", exc.status_code, exc.message)
            break
        except APIError as exc:
            final_ans = f"LLM error: {exc}"
            logger.error("LLM APIError: %s", exc)
            break
        except Exception as exc:
            final_ans = f"Unknown error: {type(exc).__name__}: {exc}"
            logger.error("Unexpected error during LLM call: %s", exc, exc_info=True)
            break

        message = response.choices[0].message
        llm_content = message.content

        assistant_msg: dict = {"role": "assistant", "content": llm_content}
        if message.tool_calls:
            assistant_msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in message.tool_calls
            ]
        messages.append(assistant_msg)

        if not message.tool_calls:
            final_ans = llm_content or "Analysis complete."
            logger.info("Agent finished without explicit final_answer call.")
            if log_id:
                _save_turn(db, log_id, iteration, "direct_answer", llm_content, None, None)
            break

        tool_results = []
        for tc in message.tool_calls:
            fn_name = tc.function.name
            try:
                fn_args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                fn_args = {}

            logger.info("Agent calling tool: %s", fn_name)
            tool_trace.append(fn_name)

            if fn_name == "final_answer":
                final_ans = fn_args.get("answer", "")
                if log_id:
                    _save_turn(db, log_id, iteration, "final_answer", llm_content, final_ans, None)
                tool_results.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": "Final answer recorded.",
                    }
                )
                break

            if fn_name == "run_python_analysis":
                last_code = fn_args.get("code", "")

            tool_input_str = json.dumps(fn_args, ensure_ascii=False) if fn_args else None
            tool_output = _dispatch_tool(fn_name, fn_args)

            if log_id:
                _save_turn(db, log_id, iteration, fn_name, llm_content, tool_input_str, tool_output)

            if fn_name == "run_python_analysis":
                try:
                    parsed = json.loads(tool_output)
                    current_error = None if parsed.get("status") == "success" else str(parsed)
                except Exception:
                    current_error = tool_output

                if current_error:
                    if current_error == prev_error:
                        repeated_error_count += 1
                    else:
                        repeated_error_count = 0
                    prev_error = current_error

                    if repeated_error_count >= 2:
                        final_ans = (
                            "The analysis could not be completed: the same error occurred "
                            f"repeatedly.\n\nLast error:\n{current_error}"
                        )
                        break
                else:
                    prev_error = None
                    repeated_error_count = 0

            tool_results.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": tool_output,
                }
            )

        messages.extend(tool_results)

        if final_ans is not None:
            break

    if final_ans is None:
        final_ans = "Maximum iterations reached without a conclusive answer."

    if db is not None and log_id:
        log = db.query(AnalysisLog).filter(AnalysisLog.id == log_id).first()
        if log:
            log.status = "done"
            log.iterations = iteration
            log.final_answer = final_ans[:4000]
            db.commit()

    return {
        "answer": final_ans,
        "iterations": iteration,
        "generated_code": last_code,
        "tool_trace": tool_trace,
        "log_id": log_id,
    }
