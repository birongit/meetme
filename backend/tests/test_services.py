import pytest
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from unittest.mock import patch, MagicMock
from app.services.calendar import CalendarService

# Sample preferences
sample_prefs = {
    "no_meetings": [
        {"days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"], "start": "08:00", "end": "19:00", "reason": "work"},
        {"days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"], "start": "22:00", "end": "07:00", "reason": "sleep"},
        {"days": ["Monday"], "start": "19:00", "end": "23:59", "reason": "Monday night unavailable"}
    ],
    "batch_meetings": True
}

def test_is_slot_blocked():
    # Test specific blocking logic
    tz = timezone.utc
    
    # Monday 10:00 - 11:00 (Work block 08:00-19:00) -> Should be BLOCKED
    dt_start = datetime(2025, 11, 17, 10, 0, tzinfo=tz) # Nov 17 2025 is Monday
    dt_end = dt_start + timedelta(hours=1)
    assert CalendarService.is_slot_blocked(dt_start, dt_end, sample_prefs) is True

    # Tuesday 19:00 - 20:00 (Work block ends 19:00) -> Should be FREE
    dt_start = datetime(2025, 11, 18, 19, 0, tzinfo=tz) # Nov 18 2025 is Tuesday
    dt_end = dt_start + timedelta(hours=1)
    assert CalendarService.is_slot_blocked(dt_start, dt_end, sample_prefs) is False

def test_is_slot_blocked_partial_overlap():
    tz = ZoneInfo("America/Los_Angeles")
    # Block Saturday 21:00-22:00
    test_prefs = {
        "no_meetings": [
            {"days": ["Saturday"], "start": "21:00", "end": "22:00", "reason": "test block"}
        ]
    }
    
    # Case 1: Ends at block start -> OK
    dt_start = datetime(2025, 11, 22, 20, 0, tzinfo=tz)
    dt_end = datetime(2025, 11, 22, 21, 0, tzinfo=tz)
    assert CalendarService.is_slot_blocked(dt_start, dt_end, test_prefs) is False

    # Case 2: Exact overlap -> Blocked
    dt_start = datetime(2025, 11, 22, 21, 0, tzinfo=tz)
    dt_end = datetime(2025, 11, 22, 22, 0, tzinfo=tz)
    assert CalendarService.is_slot_blocked(dt_start, dt_end, test_prefs) is True

    # Case 3: Partial overlap -> Blocked
    dt_start = datetime(2025, 11, 22, 21, 30, tzinfo=tz)
    dt_end = datetime(2025, 11, 22, 22, 30, tzinfo=tz)
    assert CalendarService.is_slot_blocked(dt_start, dt_end, test_prefs) is True

    # Case 4: Starts at block end -> OK
    dt_start = datetime(2025, 11, 22, 22, 0, tzinfo=tz)
    dt_end = datetime(2025, 11, 22, 23, 0, tzinfo=tz)
    assert CalendarService.is_slot_blocked(dt_start, dt_end, test_prefs) is False


# --- Tests for get_available_slots with custom date range ---

def _mock_calendar_service():
    """Helper to mock Google Calendar API calls used by get_available_slots."""
    mock_service = MagicMock()
    mock_service.calendarList().get().execute.return_value = {"timeZone": "UTC"}
    mock_service.events().list().execute.return_value = {"items": []}
    return mock_service


@patch("app.services.calendar.PreferencesService.get_preferences", return_value={"no_meetings": []})
@patch("app.services.calendar.CalendarService.get_service")
def test_get_available_slots_custom_range(mock_get_service, mock_prefs):
    """Custom start/end returns slots only within that range."""
    mock_get_service.return_value = _mock_calendar_service()

    # Pick a date range 20 days from now so it's clearly in the future
    start = (datetime.now(timezone.utc) + timedelta(days=20)).strftime('%Y-%m-%d')
    end = (datetime.now(timezone.utc) + timedelta(days=22)).strftime('%Y-%m-%d')

    slots = CalendarService.get_available_slots("UTC", start_date=start, end_date=end)

    # All returned slots should fall within the requested range
    for slot in slots:
        slot_date = slot['start'][:10]
        assert start <= slot_date <= end, f"Slot {slot_date} outside range {start}–{end}"

    # Should have some slots (3 days × up to 15 hours each)
    assert len(slots) > 0


@patch("app.services.calendar.PreferencesService.get_preferences", return_value={"no_meetings": []})
@patch("app.services.calendar.CalendarService.get_service")
def test_get_available_slots_max_14_day_guardrail(mock_get_service, mock_prefs):
    """A 30-day range is clamped to 14 days."""
    mock_get_service.return_value = _mock_calendar_service()

    start = (datetime.now(timezone.utc) + timedelta(days=20)).strftime('%Y-%m-%d')
    end = (datetime.now(timezone.utc) + timedelta(days=50)).strftime('%Y-%m-%d')

    slots = CalendarService.get_available_slots("UTC", start_date=start, end_date=end)

    if slots:
        # The latest slot date should be at most 14 days after start
        latest_slot_date = max(s['start'][:10] for s in slots)
        expected_max = (datetime.strptime(start, '%Y-%m-%d') + timedelta(days=14)).strftime('%Y-%m-%d')
        assert latest_slot_date <= expected_max, f"Slot {latest_slot_date} exceeds 14-day cap {expected_max}"


@patch("app.services.calendar.PreferencesService.get_preferences", return_value={"no_meetings": []})
@patch("app.services.calendar.CalendarService.get_service")
def test_get_available_slots_default_unchanged(mock_get_service, mock_prefs):
    """No start/end params = 7 days from now (original behavior)."""
    mock_get_service.return_value = _mock_calendar_service()

    slots = CalendarService.get_available_slots("UTC")

    if slots:
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        max_date = (datetime.now(timezone.utc) + timedelta(days=7)).strftime('%Y-%m-%d')
        for slot in slots:
            slot_date = slot['start'][:10]
            assert today <= slot_date <= max_date, f"Slot {slot_date} outside default 7-day range"
