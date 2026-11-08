from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import PracticeSession, GeneratedPaper, User, Activity
from ..security import current_user
from ..stats import COUNTED, streaks
r = APIRouter(prefix="/api/leaderboard", tags=["leaderboard"])
def compute(db: Session, weekly: bool):
    """Score = per paper, BEST PYQ attempt only: 2*correct + 5 completion; plus a user's top-5 sample papers by correct answers.
    Retaking a paper or generating many papers can't farm points."""
    since = datetime.utcnow() - timedelta(days=7) if weekly else None
    q = db.query(PracticeSession).filter(PracticeSession.submitted_at.isnot(None))
    if since: q = q.filter(PracticeSession.submitted_at >= since)
    best, pts = {}, {}
    for s in q:
        k = (s.user_id, s.paper_id)
        if k not in best or (s.correct, s.score) > (best[k].correct, best[k].score):
            best[k] = s
    for (u, _), s in best.items(): pts[u] = pts.get(u, 0) + s.correct * 2 + 5
    g = db.query(GeneratedPaper).filter(GeneratedPaper.status == "submitted")
    if since: g = g.filter(GeneratedPaper.submitted_at >= since)
    gp = {}
    for x in g: gp.setdefault(x.user_id, []).append(x.correct)
    for u, v in gp.items(): pts[u] = pts.get(u, 0) + sum(sorted(v, reverse=True)[:5])
    if not pts: return []
    names = {u.id: u.name for u in db.query(User).filter(User.id.in_(pts))}
    days = {}
    for a in db.query(Activity).filter(Activity.user_id.in_(pts), Activity.kind.in_(COUNTED)): days.setdefault(a.user_id, set()).add(a.day)
    rows = []
    for u, p in pts.items():
        c = sum(s.correct for (user_id, _), s in best.items() if user_id == u)
        i = sum(s.incorrect for (user_id, _), s in best.items() if user_id == u)
        rows.append({"user_id": u, "name": names.get(u, "Student"), "score": p, "attempted": c + i,
                     "accuracy": round(100 * c / (c + i), 1) if c + i else 0, "streak": streaks(days.get(u, set()))[0]})
    rows.sort(key=lambda x: (-x["score"], x["name"]))
    for n, x in enumerate(rows, 1): x["rank"] = n
    return rows
@r.get("")
def board(period: str = "weekly", u: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = compute(db, period == "weekly"); me = next((x for x in rows if x["user_id"] == u.id), None)
    strip = lambda x: {k: v for k, v in x.items() if k != "user_id"}  # no ids/emails exposed
    return {"rows": [{**strip(x), "me": x["user_id"] == u.id} for x in rows[:50]], "me": strip(me) if me else None}
