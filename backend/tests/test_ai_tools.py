"""
Tests that verify the LangChain tools used by AIService are:
  1. Correctly exposed to the LLM (right names, right parameters in schema)
  2. Actually callable and produce the expected output

fetch_available_slots is defined as a closure inside rank_slots, so we
capture it by intercepting the create_tool_calling_agent call.
"""
from unittest.mock import patch, MagicMock

from app.services.ai_service import get_days_of_week, AIService


# ── Helpers ──────────────────────────────────────────────────────────────────

FAKE_SLOTS = [
    {"start": "2026-03-01T09:00:00+00:00", "end": "2026-03-01T10:00:00+00:00"},
    {"start": "2026-03-02T14:00:00+00:00", "end": "2026-03-02T15:00:00+00:00"},
]


def _capture_tools(user_feedback=None):
    """
    Run rank_slots with a mocked LLM and executor, returning the tools list
    that was passed to create_tool_calling_agent.
    """
    captured = {}

    def fake_create_agent(llm, tools, prompt):
        captured["tools"] = tools
        return MagicMock()

    mock_executor = MagicMock()
    mock_executor.invoke.return_value = {
        "output": '{"slots": [], "message": "ok"}',
        "intermediate_steps": [],
    }

    with patch("app.services.ai_service.create_tool_calling_agent", side_effect=fake_create_agent), \
         patch("app.services.ai_service.AgentExecutor", return_value=mock_executor), \
         patch("app.services.ai_service.ChatGoogleGenerativeAI", return_value=MagicMock()), \
         patch("app.services.ai_service.PreferencesService.get_preferences", return_value={"no_meetings": []}):
        try:
            AIService.rank_slots(FAKE_SLOTS, user_feedback=user_feedback, user_tz="UTC")
        except Exception:
            pass  # We only care about captured tools, not the full result

    return captured.get("tools", [])


# ── get_days_of_week: direct unit tests (module-level tool) ──────────────────

def test_get_days_of_week_plain_date():
    result = get_days_of_week.invoke({"date_strings": ["2025-11-17"]})  # Monday
    assert result["2025-11-17"] == "Monday"


def test_get_days_of_week_iso_format():
    result = get_days_of_week.invoke({"date_strings": ["2025-11-17T09:00:00"]})
    assert result["2025-11-17T09:00:00"] == "Monday"


def test_get_days_of_week_multiple_dates():
    result = get_days_of_week.invoke({"date_strings": ["2025-11-17", "2025-11-18", "2025-11-22"]})
    assert result["2025-11-17"] == "Monday"
    assert result["2025-11-18"] == "Tuesday"
    assert result["2025-11-22"] == "Saturday"


def test_get_days_of_week_invalid_date():
    result = get_days_of_week.invoke({"date_strings": ["not-a-date"]})
    assert "Invalid" in result["not-a-date"]


# ── Tool registration: both tools must be passed to the LLM ─────────────────

def test_both_tools_are_registered():
    tools = _capture_tools()
    names = {t.name for t in tools}
    assert "get_days_of_week" in names, f"get_days_of_week missing from {names}"
    assert "fetch_available_slots" in names, f"fetch_available_slots missing from {names}"


def test_fetch_available_slots_has_correct_parameters():
    tools = _capture_tools()
    tool = next(t for t in tools if t.name == "fetch_available_slots")
    assert "start_date" in tool.args, f"start_date missing from args: {tool.args}"
    assert "end_date" in tool.args, f"end_date missing from args: {tool.args}"


def test_get_days_of_week_has_correct_parameters():
    tools = _capture_tools()
    tool = next(t for t in tools if t.name == "get_days_of_week")
    assert "date_strings" in tool.args, f"date_strings missing from args: {tool.args}"


# ── fetch_available_slots: callability (closure tool) ───────────────────────

def test_fetch_available_slots_returns_formatted_slot_list():
    tools = _capture_tools(user_feedback="next month")
    fetch_tool = next(t for t in tools if t.name == "fetch_available_slots")

    mock_slots = [
        {"start": "2026-04-01T09:00:00+00:00", "end": "2026-04-01T10:00:00+00:00"},
        {"start": "2026-04-02T14:00:00+00:00", "end": "2026-04-02T15:00:00+00:00"},
    ]

    with patch("app.services.ai_service.CalendarService.get_available_slots", return_value=mock_slots):
        result = fetch_tool.invoke({"start_date": "2026-04-01", "end_date": "2026-04-07"})

    assert "2026-04-01T09:00:00" in result
    assert "2026-04-02T14:00:00" in result


def test_fetch_available_slots_empty_range_returns_message():
    tools = _capture_tools(user_feedback="next month")
    fetch_tool = next(t for t in tools if t.name == "fetch_available_slots")

    with patch("app.services.ai_service.CalendarService.get_available_slots", return_value=[]):
        result = fetch_tool.invoke({"start_date": "2026-04-01", "end_date": "2026-04-07"})

    assert result == "No available slots found in that date range."


def test_fetch_available_slots_passes_user_tz():
    """Verify the closure correctly passes user_tz from rank_slots to CalendarService."""
    tools = _capture_tools(user_feedback="next month")
    fetch_tool = next(t for t in tools if t.name == "fetch_available_slots")

    with patch("app.services.ai_service.CalendarService.get_available_slots", return_value=[]) as mock_cal:
        fetch_tool.invoke({"start_date": "2026-04-01", "end_date": "2026-04-07"})

    mock_cal.assert_called_once_with("UTC", "2026-04-01", "2026-04-07")


# ── End-to-end: tool actually called during rank_slots execution ─────────────

def test_fetch_available_slots_called_during_agent_run():
    """
    Simulates the LLM deciding to call fetch_available_slots mid-run.
    The mock executor captures the tools and invokes fetch_available_slots
    itself before returning, just like a real agent would.
    """
    import json

    tool_slots = [
        {"start": "2026-04-01T09:00:00+00:00", "end": "2026-04-01T10:00:00+00:00"},
    ]
    captured = {}

    def fake_create_agent(llm, tools, prompt):
        captured["tools"] = tools
        return MagicMock()

    def fake_executor_invoke(input, config=None):
        # Simulate LLM calling fetch_available_slots
        fetch_tool = next(t for t in captured["tools"] if t.name == "fetch_available_slots")
        fetch_tool.invoke({"start_date": "2026-04-01", "end_date": "2026-04-07"})

        # Return the fetched slot as the LLM's chosen result
        return {
            "output": json.dumps({
                "slots": [{"start": "2026-04-01T09:00:00+00:00", "end": "2026-04-01T10:00:00+00:00"}],
                "message": "Here is a slot in April.",
            }),
            "intermediate_steps": [],
        }

    mock_executor = MagicMock()
    mock_executor.invoke.side_effect = fake_executor_invoke

    with patch("app.services.ai_service.create_tool_calling_agent", side_effect=fake_create_agent), \
         patch("app.services.ai_service.AgentExecutor", return_value=mock_executor), \
         patch("app.services.ai_service.ChatGoogleGenerativeAI", return_value=MagicMock()), \
         patch("app.services.ai_service.PreferencesService.get_preferences", return_value={"no_meetings": []}), \
         patch("app.services.ai_service.CalendarService.get_available_slots", return_value=tool_slots) as mock_cal:

        result = AIService.rank_slots(FAKE_SLOTS, user_feedback="next month", user_tz="UTC")

    # CalendarService was called by the tool
    mock_cal.assert_called_once_with("UTC", "2026-04-01", "2026-04-07")

    # The slot from the tool made it through validation
    assert result["suggested_slots"] == [{"start": "2026-04-01T09:00:00+00:00", "end": "2026-04-01T10:00:00+00:00"}]
    assert result["ai_message"] == "Here is a slot in April."


# ── Resilience: retry on empty output, fallback on unusable output ───────────

def _run_rank_slots_with_outputs(outputs):
    """
    Run rank_slots with a mocked executor whose successive invoke() calls
    return the given output strings. Returns (result, temps, invoke_count).
    """
    llm_temps = []

    def fake_llm(**kwargs):
        llm_temps.append(kwargs.get("temperature"))
        return MagicMock()

    responses = [{"output": o, "intermediate_steps": []} for o in outputs]
    mock_executor = MagicMock()
    mock_executor.invoke.side_effect = responses

    with patch("app.services.ai_service.create_tool_calling_agent", return_value=MagicMock()), \
         patch("app.services.ai_service.AgentExecutor", return_value=mock_executor), \
         patch("app.services.ai_service.ChatGoogleGenerativeAI", side_effect=fake_llm), \
         patch("app.services.ai_service.PreferencesService.get_preferences", return_value={"no_meetings": []}):
        result = AIService.rank_slots(FAKE_SLOTS, user_tz="UTC")

    return result, llm_temps, mock_executor.invoke.call_count


def test_empty_output_retries_with_temperature():
    """Empty LLM output triggers one retry with temperature > 0."""
    import json
    good = json.dumps({"slots": FAKE_SLOTS[:1], "message": "Retry worked."})
    result, temps, calls = _run_rank_slots_with_outputs(["", good])

    assert calls == 2
    assert temps == [0, 0.7]
    assert result["suggested_slots"] == FAKE_SLOTS[:1]
    assert "llm_fallback" not in result


def test_unusable_output_after_retry_falls_back_to_random_sample():
    """If output stays unusable after the retry, serve sampled legal slots instead of an error."""
    result, temps, calls = _run_rank_slots_with_outputs(["", ""])

    assert calls == 2
    assert "error" not in result
    assert result["llm_fallback"]
    # Sampled slots must all be legal ones
    assert all(s in FAKE_SLOTS for s in result["suggested_slots"])
    assert len(result["suggested_slots"]) == len(FAKE_SLOTS)  # min(7, available)
    assert result["ai_message"]


def test_prose_only_output_falls_back_without_error():
    """Prose with no JSON at all (July 8 failure mode) degrades gracefully."""
    prose = "Here are some great slots:\n* Monday 9am\n* Tuesday 2pm\nLet me know!"
    result, temps, calls = _run_rank_slots_with_outputs([prose])

    assert calls == 1  # non-empty, so no retry
    assert "error" not in result
    assert result["llm_fallback"]
    assert all(s in FAKE_SLOTS for s in result["suggested_slots"])
