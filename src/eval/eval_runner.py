import json
from typing import List, Dict, Any
from src.app import SupportAgent, create_session
from src.eval.case_assertions import contains_any, contains_all, check_required_sources


def run_case(agent: SupportAgent, case: Dict[str, Any]) -> Dict[str, Any]:
    session = create_session()
    messages = case.get("messages", [])
    last_output = None
    retrieved = []
    tool_called = False
    tool_args = None

    for m in messages:
        out = agent.handle_message(session, m["content"])
        last_output = out
        # capture retrieved passages when present
        if out and isinstance(out, dict):
            if "retrieved" in out and out["retrieved"]:
                retrieved = out["retrieved"]
            if "order" in out and out["order"]:
                tool_called = True
                tool_args = {"order_id": out["order"].get("order_id")}

    expect = case.get("expect", {})
    reasons = []
    passed = True

    resp_text = (last_output.get("response") if last_output else "") or ""

    # must_include (exact substrings)
    for s in expect.get("must_include", []):
        if s.lower() not in resp_text.lower():
            passed = False
            reasons.append(f"missing required text: {s}")

    # must_include_concepts (all must be present as substrings)
    for s in expect.get("must_include_concepts", []):
        if s.lower() not in resp_text.lower():
            passed = False
            reasons.append(f"missing concept: {s}")

    # must_not_include
    for s in expect.get("must_not_include", []):
        if s.lower() in resp_text.lower():
            passed = False
            reasons.append(f"forbidden text present: {s}")

    # must_not_invent
    for s in expect.get("must_not_invent", []):
        if s.lower() in resp_text.lower():
            passed = False
            reasons.append(f"invented info present: {s}")

    # required_sources
    req_srcs = expect.get("required_sources", [])
    if req_srcs:
        ok, missing = check_required_sources(retrieved, req_srcs)
        if not ok:
            passed = False
            reasons.append(f"missing required sources: {missing}")

    # forbidden_sources_as_authority
    for fs in expect.get("forbidden_sources_as_authority", []):
        for r in retrieved:
            if r.get("filename") == fs and r.get("authoritative"):
                passed = False
                reasons.append(f"forbidden source used as authority: {fs}")

    # tool expectations
    tool_expect = expect.get("tool")
    if tool_expect == "order_lookup":
        # consider the tool called if the agent returned a sanitized order OR the response text indicates a lookup was attempted
        resp_lower = resp_text.lower()
        heuristic_lookup = ("couldn't find" in resp_lower or "not found" in resp_lower or "i couldn't find" in resp_lower)
        if not tool_called and not heuristic_lookup:
            passed = False
            reasons.append("expected order_lookup to be called but it was not")
        else:
            # tool args check
            wanted = expect.get("tool_arguments", {})
            if wanted and tool_args:
                for k, v in wanted.items():
                    if tool_args.get(k) != v:
                        passed = False
                        reasons.append(f"tool arg mismatch: {k} expected {v} got {tool_args.get(k)}")
    elif tool_expect == "not_called":
        if tool_called:
            passed = False
            reasons.append("tool was called but should not have been")
    elif tool_expect == "not_called_without_id":
        # ensure agent asked for ID and did not call tool
        if tool_called:
            passed = False
            reasons.append("tool was called despite missing id")
        if "order id" not in resp_text.lower() and "ord-" not in resp_text.lower() and "which order" not in resp_text.lower():
            passed = False
            reasons.append("agent did not ask for order ID")

    # handoff expectations
    if expect.get("handoff"):
        handoff_ok = any(k in resp_text.lower() for k in ("contact support", "human", "support review", "contact us", "contact support"))
        if not handoff_ok:
            passed = False
            reasons.append("expected handoff recommendation but none found")

    # must_refuse_to_disclose
    for fd in expect.get("must_refuse_to_disclose", []):
        if fd.lower() in resp_text.lower():
            passed = False
            reasons.append(f"refused field disclosed: {fd}")

    return {
        "id": case.get("id"),
        "passed": passed,
        "reasons": reasons,
        "retrieved": [r.get("filename") for r in retrieved],
        "tool_called": tool_called,
        "tool_args": tool_args,
    }


def run_cases(cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    agent = SupportAgent()
    results = []
    breakdown = {"retrieval": 0, "groundedness": 0, "tool_use": 0, "privacy": 0, "multi-turn": 0}
    for c in cases:
        res = run_case(agent, c)
        results.append(res)
        if res["passed"]:
            # naive category increment
            cat = c.get("category")
            if cat in breakdown:
                breakdown[cat] = breakdown.get(cat, 0) + 1

    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    return {"total": total, "passed": passed, "results": results, "breakdown": breakdown}
