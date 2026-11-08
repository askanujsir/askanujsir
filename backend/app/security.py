from datetime import datetime, timedelta
import bcrypt, jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from .config import settings
from .db import get_db
from .models import User
def hash_pw(p: str) -> str: return bcrypt.hashpw(p.encode()[:72], bcrypt.gensalt()).decode()
def check_pw(p: str, h: str) -> bool: return bcrypt.checkpw(p.encode()[:72], h.encode())
def make_token(uid: str) -> str:
    exp = datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": uid, "exp": exp}, settings.JWT_SECRET_KEY, algorithm="HS256")
bearer = HTTPBearer()
def current_user(cred=Depends(bearer), db: Session = Depends(get_db)) -> User:
    try: uid = jwt.decode(cred.credentials, settings.JWT_SECRET_KEY, algorithms=["HS256"])["sub"]
    except Exception: raise HTTPException(401, "Invalid or expired token")
    u = db.get(User, uid)
    if not u: raise HTTPException(401, "User not found")
    return u
def admin_user(u: User = Depends(current_user)) -> User:
    if u.role != "admin": raise HTTPException(403, "Admin only")
    return u
