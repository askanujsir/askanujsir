from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import User, RefreshToken
from ..security import current_user, check_pw, hash_pw
r = APIRouter(prefix="/api/users", tags=["users"])
class Name(BaseModel): name: str = Field(min_length=2, max_length=100)
class Pw(BaseModel): current: str; new: str = Field(min_length=8, max_length=72)
@r.patch("/me")
def rename(b: Name, u: User = Depends(current_user), db: Session = Depends(get_db)):
    u.name = b.name.strip(); db.commit(); return {"name": u.name}
@r.post("/me/password")
def password(b: Pw, u: User = Depends(current_user), db: Session = Depends(get_db)):
    if not check_pw(b.current, u.password_hash): raise HTTPException(400, "Current password is wrong")
    u.password_hash = hash_pw(b.new)
    for t in db.query(RefreshToken).filter_by(user_id=u.id, revoked=False): t.revoked = True
    db.commit(); return {"ok": True}
