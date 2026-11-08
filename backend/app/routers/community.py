import jwt
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from ..config import settings
from ..db import get_db, SessionLocal
from ..models import CommunityMessage, User
from ..rate import limit
from ..security import current_user
from ..stats import log
r = APIRouter(prefix="/api/community", tags=["community"])
hub: set = set()
def pub(m, name): return {"id": m.id, "user": name, "content": m.content, "created_at": m.created_at.isoformat() + "Z"}
@r.get("/messages")
def history(limit_: int = 50, u: User = Depends(current_user), db: Session = Depends(get_db)):
    ms = db.query(CommunityMessage).order_by(CommunityMessage.created_at.desc()).limit(min(limit_, 100)).all()
    names = {x.id: x.name for x in db.query(User).filter(User.id.in_({m.user_id for m in ms}))}
    return [pub(m, names.get(m.user_id, "Student")) for m in reversed(ms)]
@r.post("/messages/{mid}/report")
def report(mid: str, u: User = Depends(current_user), db: Session = Depends(get_db)):
    m = db.get(CommunityMessage, mid)
    if not m: raise HTTPException(404, "Not found")
    m.reports += 1; db.commit(); return {"ok": True}
@r.websocket("/ws")
async def ws_endpoint(ws: WebSocket, token: str = ""):
    db = SessionLocal()
    try:
        try: uid = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"])["sub"]
        except Exception: await ws.close(code=4401); return
        u = db.get(User, uid)
        if not u: await ws.close(code=4401); return
        await ws.accept(); hub.add(ws)
        try:
            while True:
                text = (await ws.receive_text()).strip()
                if not text: continue
                if len(text) > 500: await ws.send_json({"error": "Message too long (max 500 characters)"}); continue
                try: limit(f"ws:{u.id}", 10, 30); limit(f"wsb:{u.id}", 1, 1)
                except HTTPException: await ws.send_json({"error": "You're sending messages too fast"}); continue
                m = CommunityMessage(user_id=u.id, content=text); db.add(m); log(db, u.id, "community"); db.commit()
                payload = pub(m, u.name)
                for c in list(hub):
                    try: await c.send_json(payload)
                    except Exception: hub.discard(c)
        except WebSocketDisconnect: pass
    finally:
        hub.discard(ws); db.close()
