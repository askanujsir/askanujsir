from datetime import datetime
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import QuestionPaper, PracticeSession, PracticeResponse, Activity, User
from ..security import current_user
r = APIRouter(prefix="/api/practice", tags=["practice"])
class Start(BaseModel): paper_id: str; mode: str = "timed"; duration_min: int | None = 30
class Submit(BaseModel): answers: dict[str, list[int]] = {}
def own(db, u, sid):
    s = db.get(PracticeSession, sid)
    if not s or s.user_id != u.id: raise HTTPException(404, "Session not found")
    return s
@r.post("/start", status_code=201)
def start(b: Start, u: User = Depends(current_user), db: Session = Depends(get_db)):
    p = db.get(QuestionPaper, b.paper_id)
    if not p or p.status != "published": raise HTTPException(404, "Paper not found")
    if b.mode not in ("timed", "untimed"): raise HTTPException(400, "Bad mode")
    s = PracticeSession(user_id=u.id, paper_id=p.id, mode=b.mode, duration_min=b.duration_min if b.mode == "timed" else None)
    db.add(s); db.commit()
    qs = [{"id": q.id, "qtype": q.qtype, "text": q.text, "options": q.options, "marks": q.marks} for q in p.questions]  # no answers
    return {"session_id": s.id, "duration_min": s.duration_min, "started_at": s.started_at, "questions": qs}
@r.post("/{sid}/submit")
def submit(sid: str, b: Submit, u: User = Depends(current_user), db: Session = Depends(get_db)):
    s = own(db, u, sid)
    if s.submitted_at: raise HTTPException(409, "Already submitted")
    p = db.get(QuestionPaper, s.paper_id)
    now = datetime.utcnow(); taken = int((now - s.started_at).total_seconds())
    if s.duration_min and taken > s.duration_min * 60 + 30: b.answers = {}  # server-side time enforcement (30s grace)
    sc = tot = 0; c = i = k = 0; review = []
    for q in p.questions:
        sel = sorted(set(b.answers.get(q.id, []))); tot += q.marks
        if not sel: st, m = "skipped", 0; k += 1
        elif sel == sorted(q.answer): st, m = "correct", q.marks; c += 1
        else: st, m = "incorrect", -q.negative; i += 1
        sc += m
        s.responses.append(PracticeResponse(question_id=q.id, selected=sel, status=st, marks=m))
        review.append({"id": q.id, "text": q.text, "options": q.options, "selected": sel, "answer": q.answer, "status": st, "marks": m, "explanation": q.explanation})
    s.score, s.total, s.correct, s.incorrect, s.skipped, s.submitted_at, s.time_taken_s = sc, tot, c, i, k, now, taken
    db.add(Activity(user_id=u.id, kind="practice", day=datetime.now(ZoneInfo("Asia/Kolkata")).date())); db.commit()
    return {"score": sc, "total": tot, "percentage": round(100 * sc / tot, 1) if tot else 0, "correct": c, "incorrect": i, "skipped": k,
            "accuracy": round(100 * c / (c + i), 1) if c + i else 0, "time_taken_s": taken, "review": review}
