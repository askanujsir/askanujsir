from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from .models import Activity
IST = ZoneInfo("Asia/Kolkata")
COUNTED = ("chat", "practice", "paper")  # community chat does not count toward streaks
def today(): return datetime.now(IST).date()
def ist(dt): return dt.replace(tzinfo=timezone.utc).astimezone(IST)
def log(db, uid, kind): db.add(Activity(user_id=uid, kind=kind, day=today()))
def streaks(days: set):
    longest = run = 0; prev = None
    for d in sorted(days):
        run = run + 1 if prev and d - prev == timedelta(days=1) else 1; longest = max(longest, run); prev = d
    t = today(); cur = 0; d = t if t in days else t - timedelta(days=1)
    while d in days: cur += 1; d -= timedelta(days=1)
    return cur, longest
