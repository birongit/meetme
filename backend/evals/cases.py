"""Golden eval cases for the AI slot-ranking agent.

Each case is a real or representative user input plus deterministic
expectations. Groups:
  happy          — basic requests that should always work
  failure-replay — inputs that broke production (seeded from Langfuse traces)
  tool-discipline— cases where calling fetch_available_slots is required
  edge           — calendar shapes that stress the pipeline

Failure-replay provenance (Langfuse, gemini-2.5-flash-lite):
  - "What about the week after?"  Jul 8 2026: prose-prefixed JSON
  - "only weekends please"        Jul 12 2026: clarifying question instead of tool call
  - initial round, dense calendar Jul 12 2026: empty output after tool call (x3)
  - holiday-weekend phrasing      Aug 30 2026: pure prose, no JSON
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable, Optional
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Los_Angeles")


def today() -> datetime:
    return datetime.now(TZ).replace(hour=0, minute=0, second=0, microsecond=0)


@dataclass
class EvalCase:
    id: str
    group: str
    user_feedback: Optional[str] = None
    calendar: str = "normal"  # normal | sparse | dense
    expect_tool: Optional[str] = None
    # Constraint applied to every suggested slot's start datetime
    slot_constraint: Optional[Callable[[datetime], bool]] = None
    constraint_desc: str = ""
    min_slots: int = 5
    max_slots: int = 10


def _is_weekend(dt: datetime) -> bool:
    return dt.weekday() >= 5


def _is_morning(dt: datetime) -> bool:
    return dt.hour < 12


def _is_tuesday(dt: datetime) -> bool:
    return dt.weekday() == 1


def _next_week_or_later(dt: datetime) -> bool:
    return dt >= today() + timedelta(days=7)


def _within_three_days(dt: datetime) -> bool:
    return dt <= today() + timedelta(days=3)


def _sat_sun_mon(dt: datetime) -> bool:
    return dt.weekday() in (5, 6, 0)


CASES = [
    # ── happy ────────────────────────────────────────────────────────────────
    EvalCase(id="initial-no-feedback", group="happy"),
    EvalCase(id="mornings", group="happy", user_feedback="mornings please",
             slot_constraint=_is_morning, constraint_desc="start before 12:00"),
    EvalCase(id="weekends-only", group="happy", user_feedback="only weekends",
             slot_constraint=_is_weekend, constraint_desc="Saturday or Sunday"),
    EvalCase(id="next-tuesday", group="happy", user_feedback="next Tuesday",
             slot_constraint=_is_tuesday, constraint_desc="a Tuesday",
             min_slots=1),  # only one Tuesday in range; 5+ may be impossible
    # ── failure-replay ───────────────────────────────────────────────────────
    EvalCase(id="week-after-jul08", group="failure-replay",
             user_feedback="What about the week after?",
             expect_tool="fetch_available_slots",
             slot_constraint=_next_week_or_later, constraint_desc=">= 7 days out"),
    EvalCase(id="weekends-please-jul12", group="failure-replay",
             user_feedback="only weekends please",
             slot_constraint=_is_weekend, constraint_desc="Saturday or Sunday"),
    EvalCase(id="empty-output-jul12", group="failure-replay", calendar="dense"),
    EvalCase(id="long-weekend-aug30", group="failure-replay",
             user_feedback="something on a long weekend, Saturday through Monday",
             slot_constraint=_sat_sun_mon, constraint_desc="Sat, Sun, or Mon"),
    # ── tool-discipline ──────────────────────────────────────────────────────
    EvalCase(id="week-after-next", group="tool-discipline",
             user_feedback="the week after next",
             expect_tool="fetch_available_slots",
             slot_constraint=_next_week_or_later, constraint_desc=">= 7 days out"),
    EvalCase(id="in-three-weeks", group="tool-discipline",
             user_feedback="in about three weeks",
             expect_tool="fetch_available_slots",
             slot_constraint=lambda dt: dt >= today() + timedelta(days=14),
             constraint_desc=">= 14 days out"),
    EvalCase(id="tomorrow", group="tool-discipline",
             user_feedback="tomorrow if possible",
             expect_tool="fetch_available_slots",
             slot_constraint=_within_three_days, constraint_desc="<= 3 days out",
             min_slots=1),
    # ── edge ─────────────────────────────────────────────────────────────────
    EvalCase(id="sparse-calendar", group="edge", calendar="sparse",
             min_slots=1, max_slots=10),
    EvalCase(id="dense-calendar", group="edge", calendar="dense"),
    EvalCase(id="impossible-time", group="edge",
             user_feedback="3am would be perfect",
             min_slots=1),  # no 3am slots exist; any legal suggestion is fine
]
