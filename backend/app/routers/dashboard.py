from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import Activity, PracticeSession, Conversation, Message, QuestionPaper, GeneratedPaper, CommunityMessage, User
from ..security import current_user
from ..stats import COUNTED, streaks, ist
from .leaderboard import compute
r = APIRouter(prefix="/api/dashboard", tags=["dashboard"])
@r.get("")
def dash(u: User = Depends(current_user), db: Session = Depends(get_db)):
    ss = db.query(PracticeSession).filter(PracticeSession.user_id == u.id, PracticeSession.submitted_at.isnot(None)).order_by(PracticeSession.submitted_at).all()
    c, i, k = (sum(getattr(s, f) for s in ss) for f in ("correct", "incorrect", "skipped"))
    codes = {p.id: p.subject_code for p in db.query(QuestionPaper)}; sub, over = {}, {}
    for s in ss:
        a = sub.setdefault(codes.get(s.paper_id), [0, 0]); a[0] += s.correct; a[1] += s.incorrect
        d = str(ist(s.submitted_at).date()); over[d] = over.get(d, 0) + s.correct + s.incorrect
    acts = db.query(Activity).filter_by(user_id=u.id).all(); heat = {}
    for a in acts: heat[str(a.day)] = heat.get(str(a.day), 0) + 1
    cur, longest = streaks({a.day for a in acts if a.kind in COUNTED})
    convs = db.query(Conversation).filter_by(user_id=u.id).order_by(Conversation.created_at.desc()).all()
    msgs = db.query(func.count(Message.id)).join(Conversation, Message.conversation_id == Conversation.id).filter(Conversation.user_id == u.id).scalar()
    gps = db.query(GeneratedPaper).filter_by(user_id=u.id).order_by(GeneratedPaper.created_at.desc()).all()
    cm = db.query(func.count(CommunityMessage.id)).filter_by(user_id=u.id).scalar()
    out = {}
    for p in ("weekly", "all"):
        rows = compute(db, p == "weekly"); me = next((x for x in rows if x["user_id"] == u.id), None)
        out[p] = {"rank": me["rank"] if me else None, "score": me["score"] if me else 0,
                  "top": [{"rank": x["rank"], "name": x["name"], "score": x["score"]} for x in rows[:5]]}
    return {"attempted": c + i, "correct": c, "incorrect": i, "skipped": k, "accuracy": round(100 * c / (c + i), 1) if c + i else 0, "sessions": len(ss),
            "recent": [{"score": s.score, "total": s.total, "at": s.submitted_at} for s in ss[-5:]],
            "subject_accuracy": [{"subject": s, "attempted": a + b, "accuracy": round(100 * a / (a + b), 1) if a + b else 0} for s, (a, b) in sub.items()],
            "over_time": [{"day": d, "attempted": n} for d, n in sorted(over.items())],
            "conversations": len(convs), "messages": msgs, "recent_chats": [{"id": x.id, "title": x.title} for x in convs[:5]],
            "sample_total": len(gps), "sample_completed": sum(g.status == "submitted" for g in gps),
            "recent_papers": [{"id": g.id, "title": g.title, "status": g.status} for g in gps[:5]], "community_messages": cm,
            "streak": cur, "longest_streak": longest, "active_days": len({a.day for a in acts if a.kind in COUNTED}), "heatmap": heat, "leaderboard": out}
