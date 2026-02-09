import pytest
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
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
