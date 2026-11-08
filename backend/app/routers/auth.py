import hashlib, secrets
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session
from ..config import settings
from ..db import get_db
from ..models import User, RefreshToken
from ..security import hash_pw, check_pw, make_token, current_user
r = APIRouter(prefix="/api/auth", tags=["auth"])
class Reg(BaseModel):
    name: str = Field(min_length=2, max_length=100); email: EmailStr; password: str = Field(min_length=8, max_length=72)
class Login(BaseModel): email: EmailStr; password: str
class Refresh(BaseModel): refresh_token: str
H = lambda t: hashlib.sha256(t.encode()).hexdigest()
def out(u): return {"id": u.id, "name": u.name, "email": u.email, "role": u.role, "created_at": u.created_at}
def issue(db, u):
    raw = secrets.token_urlsafe(48)
    db.add(RefreshToken(user_id=u.id, token_hash=H(raw), expires_at=datetime.utcnow() + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)))
    db.commit(); return {"token": make_token(u.id), "refresh_token": raw, "user": out(u)}
@r.post("/register", status_code=201)
def register(b: Reg, db: Session = Depends(get_db)):
    if db.query(User).filter_by(email=b.email.lower()).first(): raise HTTPException(409, "Email already registered")
    u = User(name=b.name, email=b.email.lower(), password_hash=hash_pw(b.password)); db.add(u); db.commit()
    return issue(db, u)
@r.post("/login")
def login(b: Login, db: Session = Depends(get_db)):
    u = db.query(User).filter_by(email=b.email.lower()).first()
    if not u or not check_pw(b.password, u.password_hash): raise HTTPException(401, "Invalid credentials")
    return issue(db, u)
@r.post("/refresh")
def refresh(b: Refresh, db: Session = Depends(get_db)):
    t = db.query(RefreshToken).filter_by(token_hash=H(b.refresh_token)).first()
    if not t or t.revoked or t.expires_at < datetime.utcnow(): raise HTTPException(401, "Invalid refresh token")
    t.revoked = True; return issue(db, db.get(User, t.user_id))  # rotation
@r.post("/logout")
def logout(b: Refresh, db: Session = Depends(get_db)):
    t = db.query(RefreshToken).filter_by(token_hash=H(b.refresh_token)).first()
    if t: t.revoked = True; db.commit()
    return {"ok": True}
@r.get("/me")
def me(u: User = Depends(current_user)): return out(u)
