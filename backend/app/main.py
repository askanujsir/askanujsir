from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .db import Base, engine, SessionLocal
from .models import Subject, User
from .security import hash_pw
from .routers import auth, users, subjects, chat, practice, dashboard, admin, sample_papers, community, leaderboard
SUBJECTS = [("cs", "Computer Science", "Python, networks and databases.", True), ("bio", "Biology", "Life processes and genetics.", False),
            ("math", "Mathematics", "Calculus, algebra and probability.", False), ("phy", "Physics", "Mechanics, optics and modern physics.", False),
            ("chem", "Chemistry", "Organic, inorganic and physical.", False), ("eng", "English", "Literature and writing skills.", False)]
@asynccontextmanager
async def lifespan(app):
    if settings.AUTO_CREATE_TABLES: Base.metadata.create_all(engine)  # in production run `alembic upgrade head` and set this false
    with SessionLocal() as db:
        for c, n, d, e in SUBJECTS:
            if not db.get(Subject, c): db.add(Subject(code=c, name=n, description=d, enabled=e))
        if settings.ADMIN_EMAIL and settings.ADMIN_PASSWORD and not db.query(User).filter_by(email=settings.ADMIN_EMAIL.lower()).first():
            db.add(User(name="Admin", email=settings.ADMIN_EMAIL.lower(), password_hash=hash_pw(settings.ADMIN_PASSWORD), role="admin"))
        db.commit()
    yield
app = FastAPI(title="askanujsir", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[settings.FRONTEND_URL], allow_methods=["*"], allow_headers=["*"])
@app.get("/health")
def health():
    return {"status": "ok"}
for m in (auth, users, subjects, chat, practice, dashboard, admin, sample_papers, community, leaderboard): app.include_router(m.r)
