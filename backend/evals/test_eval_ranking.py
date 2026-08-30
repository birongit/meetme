"""Live-LLM evals for AIService.rank_slots.

Runs the real agent against the real Gemini API with a synthetic
calendar. Deterministic checks only — no LLM-as-judge.

    cd backend && pytest -m eval evals/ -v

Each case records named check results into the session scorecard
(evals/results/) so runs can be diffed across models and migrations.
"""
import uuid
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from app.services.ai_service import AIService
from evals.cases import CASES, TZ, EvalCase, today
from evals.conftest import RESULTS

RUN_ID = f"eval-{datetime.now().strftime('%Y%m%d-%H%M')}-{uuid.uuid4().hex[:6]}"

CALENDAR_HOURS = {
    "normal": [9, 10, 14, 19],
    "dense": list(range(7, 22)),
    "sparse": None,  # special-cased below
}


def synth_slots(profile: str, start: datetime, end: datetime):
    """Deterministic synthetic calendar matching CalendarService's slot shape."""
    slots = []
    day = start
    while day < end:
        if profile == "sparse":
            # two slots total, first two days only
            if (day - start).days < 2:
                hours = [10]
            else:
                hours = []
        else:
            hours = CALENDAR_HOURS[profile]
        for h in hours:
            s = day.replace(hour=h)
            if s > datetime.now(TZ):
                slots.append({"start": s.isoformat(),
                              "end": (s + timedelta(hours=1)).isoformat()})
        day += timedelta(days=1)
    return slots


def run_case(case: EvalCase):
    profile = case.calendar
    served = []  # every slot the mock ever returned — the legality universe

    def mock_get_available_slots(user_tz=None, start_date=None, end_date=None):
        if start_date and end_date:
            start = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=TZ)
            end = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=TZ)
        else:
            start, end = today(), today() + timedelta(days=7)
        slots = synth_slots(profile, start, end)
        served.extend(slots)
        return slots

    legal = mock_get_available_slots()
    with patch("app.services.ai_service.CalendarService.get_available_slots",
               side_effect=mock_get_available_slots):
        result = AIService.rank_slots(
            legal, case.user_feedback, user_tz="America/Los_Angeles",
            session_id=RUN_ID,
        )

    suggested = result.get("suggested_slots", [])
    tools_called = [s["tool"] for s in result.get("agent_steps", [])]
    legality = {(s["start"], s["end"]) for s in served}

    checks = {
        "no_fallback": "llm_fallback" not in result,
        "has_slots": len(suggested) >= case.min_slots,
        "count_in_range": case.min_slots <= len(suggested) <= case.max_slots,
        "slots_legal": all((s["start"], s["end"]) in legality for s in suggested),
        "message_nonempty": bool(result.get("ai_message", "").strip()),
    }
    if case.expect_tool:
        checks["tool_called"] = case.expect_tool in tools_called
    if case.slot_constraint:
        checks[f"constraint({case.constraint_desc})"] = bool(suggested) and all(
            case.slot_constraint(datetime.fromisoformat(s["start"]))
            for s in suggested
        )
    return result, checks


@pytest.mark.eval
@pytest.mark.parametrize("case", CASES, ids=[c.id for c in CASES])
def test_eval(case: EvalCase):
    result, checks = run_case(case)
    passed = all(checks.values())
    RESULTS.append({
        "id": case.id,
        "group": case.group,
        "feedback": case.user_feedback,
        "passed": passed,
        "checks": checks,
        "num_slots": len(result.get("suggested_slots", [])),
        "fallback": result.get("llm_fallback"),
    })
    failed = [name for name, ok in checks.items() if not ok]
    assert passed, f"{case.id}: failed checks: {failed} (fallback={result.get('llm_fallback')})"
