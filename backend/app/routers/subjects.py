from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import Subject, QuestionPaper
r = APIRouter(prefix="/api", tags=["subjects"])
@r.get("/subjects")
def subjects(db: Session = Depends(get_db)):
    return [{"code": s.code, "name": s.name, "description": s.description, "enabled": s.enabled} for s in db.query(Subject).all()]
@r.get("/pyq/papers")
def papers(subject: str, db: Session = Depends(get_db)):
    ps = db.query(QuestionPaper).filter_by(subject_code=subject, status="published").order_by(QuestionPaper.year.desc()).all()
    return [{"id": p.id, "year": p.year, "title": p.title, "duration": p.default_duration_min, "count": len(p.questions)} for p in ps]
