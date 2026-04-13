"""
Multi-step agent reasoning tests.

These tests verify that the Qwen agent genuinely performs multi-turn exploration:
  observe_schema → run_python_analysis → run_python_analysis (drill) → ... → final_answer

A single-step or two-step response would fail the iteration and tool-count assertions.
"""
import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _analyze(client: TestClient, question: str) -> dict:
    resp = client.post("/analytics/analyze", json={"question": question})
    assert resp.status_code == 200
    return resp.json()


# ---------------------------------------------------------------------------
# Test 1: Schema → single analysis → answer  (baseline, ≥ 3 steps)
# ---------------------------------------------------------------------------

def test_simple_question_uses_at_least_3_steps(client: TestClient):
    """Even a simple question must: observe_schema → run_python_analysis → final_answer."""
    result = _analyze(client, "各产品线的总销售额是多少？")
    trace = result["tool_trace"]

    assert "observe_schema" in trace, "Agent must call observe_schema"
    assert "run_python_analysis" in trace, "Agent must run code"
    assert "final_answer" in trace, "Agent must call final_answer"
    assert result["iterations"] >= 3


# ---------------------------------------------------------------------------
# Test 2: Complex drill-down forces ≥ 2 rounds of run_python_analysis
# ---------------------------------------------------------------------------

def test_drilldown_uses_multiple_code_executions(client: TestClient):
    """
    Uses a result-dependent question:
      Step 1 – find the exact product code of the best-selling product
      Step 2 – (using that product code) look up its full order history year by year
    The agent cannot write step-2 code without first knowing the step-1 result,
    so it must call run_python_analysis at least twice.
    """
    result = _analyze(
        client,
        "请分两步执行："
        "第一步，找出历史总销量（数量）最高的单个产品的productCode；"
        "第二步，用第一步得到的productCode，查询该产品每年的销售数量和销售额变化。",
    )
    trace = result["tool_trace"]

    code_runs = trace.count("run_python_analysis")
    assert code_runs >= 2, (
        f"Expected ≥ 2 run_python_analysis calls for a result-dependent drill-down, "
        f"got {code_runs}. Trace: {trace}"
    )
    assert result["iterations"] >= 4


# ---------------------------------------------------------------------------
# Test 3: Tool call ORDER — schema must come before any code execution
# ---------------------------------------------------------------------------

def test_schema_observed_before_code(client: TestClient):
    """Agent should always call observe_schema BEFORE the first run_python_analysis."""
    result = _analyze(client, "哪个客户的总付款金额最高？")
    trace = result["tool_trace"]

    assert "observe_schema" in trace
    assert "run_python_analysis" in trace

    first_schema = trace.index("observe_schema")
    first_code = trace.index("run_python_analysis")
    assert first_schema < first_code, (
        f"observe_schema ({first_schema}) must come before "
        f"run_python_analysis ({first_code}). Trace: {trace}"
    )


# ---------------------------------------------------------------------------
# Test 4: Iterative refinement — question requiring 3 separate data lookups
# ---------------------------------------------------------------------------

def test_three_stage_investigation(client: TestClient):
    """
    Forces a three-stage workflow:
      Stage 1 – find the worst-performing sales rep
      Stage 2 – inspect that rep's customer list
      Stage 3 – inspect the order history of those customers
    Expects ≥ 3 code runs and ≥ 5 total iterations.
    """
    result = _analyze(
        client,
        "请分三步分析：第一步找出总销售额最低的销售代表；"
        "第二步列出该销售代表负责的所有客户；"
        "第三步查看这些客户近两年的订单记录，判断客户是否流失。",
    )
    trace = result["tool_trace"]

    code_runs = trace.count("run_python_analysis")
    assert code_runs >= 3, (
        f"Expected ≥ 3 code executions for a three-stage question, "
        f"got {code_runs}. Trace: {trace}"
    )
    assert result["answer"], "Agent must produce a non-empty final answer"


# ---------------------------------------------------------------------------
# Test 5: Anomaly-then-explain pattern
# ---------------------------------------------------------------------------

def test_anomaly_detect_then_explain(client: TestClient):
    """
    Forces a genuine two-phase investigation:
      Phase 1 – find the single product with the worst stock-to-sales ratio
                 (need its productCode before phase 2 can proceed)
      Phase 2 – using that productCode, retrieve full order history and
                 compute month-by-month demand to confirm zero-sales status.
    """
    result = _analyze(
        client,
        "请按以下两个步骤分析："
        "第一步，计算每个产品的库存量除以历史总销量之比，找出比值最大（即库存最积压）的产品productCode；"
        "第二步，用第一步得到的productCode查询该产品所有历史订单明细，"
        "确认它的实际销售情况，并给出库存风险结论。",
    )
    trace = result["tool_trace"]

    assert "observe_schema" in trace
    code_runs = trace.count("run_python_analysis")
    assert code_runs >= 2, (
        f"Result-dependent anomaly investigation needs ≥ 2 code runs, "
        f"got {code_runs}. Trace: {trace}"
    )
    assert result["answer"], "Agent must produce a non-empty answer"


# ---------------------------------------------------------------------------
# Test 6: Verify tool_trace is returned in API response
# ---------------------------------------------------------------------------

def test_tool_trace_in_response(client: TestClient):
    """tool_trace field must be present and non-empty in every /analytics/analyze response."""
    result = _analyze(client, "总订单数是多少？")
    assert "tool_trace" in result
    assert isinstance(result["tool_trace"], list)
    assert len(result["tool_trace"]) >= 2, (
        f"tool_trace should have ≥ 2 entries. Got: {result['tool_trace']}"
    )
    assert result["tool_trace"][-1] == "final_answer", (
        "Last tool call must always be final_answer"
    )


# ---------------------------------------------------------------------------
# Test 7: Full trace inspection for a 5-step question
# ---------------------------------------------------------------------------

def test_full_trace_five_step_question(client: TestClient):
    """
    Validates the exact multi-step pattern:
      observe_schema → run × N → final_answer

    Question deliberately requires broad-to-narrow investigation.
    """
    result = _analyze(
        client,
        "请逐步分析：① 哪个月份的平均订单金额最高？② 那个月里哪10个产品卖得最好？"
        "③ 这10个产品平均毛利率是多少（以MSRP衡量）？",
    )
    trace = result["tool_trace"]

    assert trace[0] == "observe_schema", f"First call must be observe_schema, got {trace[0]}"
    assert trace[-1] == "final_answer", f"Last call must be final_answer, got {trace[-1]}"

    code_runs = trace.count("run_python_analysis")
    assert code_runs >= 2, (
        f"Three-part question needs ≥ 2 code runs, got {code_runs}. Trace: {trace}"
    )

    print(f"\n  Tool trace ({len(trace)} calls): {' → '.join(trace)}")
    print(f"  Iterations: {result['iterations']}")
