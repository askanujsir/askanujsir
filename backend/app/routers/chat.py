from datetime import datetime
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from .. import ai
from ..db import get_db
from ..models import Conversation, Message, Subject, SyllabusVersion, Activity, User
from ..security import current_user
from ..rate import limit
r = APIRouter(prefix="/api/chat", tags=["chat"])
class New(BaseModel): subject_code: str = "cs"
class Msg(BaseModel): content: str = Field(min_length=1, max_length=2000)
def owned(db, u, cid):
    c = db.get(Conversation, cid)
    if not c or c.user_id != u.id: raise HTTPException(404, "Conversation not found")
    return c
@r.get("/conversations")
def lst(u: User = Depends(current_user), db: Session = Depends(get_db)):
    cs = db.query(Conversation).filter_by(user_id=u.id).order_by(Conversation.created_at.desc()).all()
    return [{"id": c.id, "title": c.title, "subject_code": c.subject_code} for c in cs]
@r.post("/conversations", status_code=201)
def new(b: New, u: User = Depends(current_user), db: Session = Depends(get_db)):
    s = db.get(Subject, b.subject_code)
    if not s or not s.enabled: raise HTTPException(400, "This subject is coming soon")
    sv = db.query(SyllabusVersion).filter_by(subject_code=s.code, is_active=True, status="published").first()
    c = Conversation(user_id=u.id, subject_code=s.code, syllabus_version_id=sv.id if sv else None); db.add(c); db.commit()
    return {"id": c.id, "title": c.title}
@r.get("/conversations/{cid}/messages")
def msgs(cid: str, u: User = Depends(current_user), db: Session = Depends(get_db)):
    return [{"role": m.role, "content": m.content} for m in owned(db, u, cid).messages]
@r.delete("/conversations/{cid}", status_code=204)
def delete(cid: str, u: User = Depends(current_user), db: Session = Depends(get_db)):
    db.delete(owned(db, u, cid)); db.commit()
@r.post("/conversations/{cid}/messages")
def send(cid: str, b: Msg, u: User = Depends(current_user), db: Session = Depends(get_db)):
    limit(f"chat:{u.id}", 20, 60)
    c = owned(db, u, cid)
    sv = db.get(SyllabusVersion, c.syllabus_version_id) if c.syllabus_version_id else None
    if sv:
        syl = "\n".join(f"- {x['title']}: " + "; ".join(x.get("topics", [])) for x in sv.content.get("units", []))[:6000]
        year = sv.academic_year
    else: syl, year = "(no syllabus published yet; say so if asked about syllabus coverage)", "n/a"
    sys = ai.TUTOR.format(subject=c.subject_code, year=year, syllabus=syl)
    hist = [{"role": m.role, "content": m.content} for m in c.messages][-12:]  # recent-window context
    reply = ai.chat([{"role": "system", "content": sys}, *hist, {"role": "user", "content": b.content}])
    if not c.messages: c.title = b.content[:60]
    db.add_all([Message(conversation_id=c.id, role="user", content=b.content), Message(conversation_id=c.id, role="assistant", content=reply)])
    db.add(Activity(user_id=u.id, kind="chat", day=datetime.now(ZoneInfo("Asia/Kolkata")).date())); db.commit()
    return {"role": "assistant", "content": reply, "title": c.title}
