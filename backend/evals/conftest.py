import json
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path

RESULTS = []

RESULTS_DIR = Path(__file__).parent / "results"


def pytest_sessionfinish(session, exitstatus):
    if not RESULTS:
        return
    by_group = defaultdict(lambda: {"pass": 0, "fail": 0})
    for r in RESULTS:
        by_group[r["group"]]["pass" if r["passed"] else "fail"] += 1
    total = len(RESULTS)
    passed = sum(1 for r in RESULTS if r["passed"])
    scorecard = {
        "run_at": datetime.now().isoformat(timespec="seconds"),
        "model": os.environ.get("GEMINI_MODEL", "gemini-2.5-flash-lite (default)"),
        "pass_rate": round(passed / total, 3),
        "passed": passed,
        "total": total,
        "by_group": {g: dict(v) for g, v in sorted(by_group.items())},
        "cases": RESULTS,
    }
    RESULTS_DIR.mkdir(exist_ok=True)
    out = RESULTS_DIR / f"scorecard-{datetime.now().strftime('%Y%m%d-%H%M')}.json"
    out.write_text(json.dumps(scorecard, indent=2))
    print(f"\n── Eval scorecard: {passed}/{total} passed ({scorecard['pass_rate']:.0%}) → {out}")
    for g, v in sorted(by_group.items()):
        print(f"   {g}: {v['pass']}/{v['pass'] + v['fail']}")
