import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from .. import ai
from ..config import settings
from ..db import get_db
from ..models import GeneratedPaper, SyllabusVersion, Subject, User
from ..rate import limit
from ..security import current_user
from ..stats import log
r = APIRouter(prefix="/api/sample-papers", tags=["sample-papers"])
LABEL = "AI-Generated Practice Paper — CBSE Pattern"
WRITTEN_TYPES = ("short_answer", "long_answer", "case_study")
AR = ("For assertion_reason, text must contain 'Assertion (A): ...' and 'Reason (R): ...' and options must be the four standard CBSE options: "
      "Both A and R are true and R is the correct explanation of A; Both A and R are true but R is not the correct explanation of A; A is true but R is false; A is false but R is true.")
BOARD_SPEC = {"duration_min": 180, "instructions": ["All questions are compulsory."], "sections": [
    {"name": "Section A — MCQ", "count": 18, "marks": 1, "qtype": "single", "negative": 0},
    {"name": "Section B — Assertion-Reason", "count": 3, "marks": 1, "qtype": "assertion_reason", "negative": 0},
    {"name": "Section C — 2 Marks", "count": 7, "marks": 2, "qtype": "short_answer", "negative": 0},
    {"name": "Section D — 3 Marks", "count": 3, "marks": 3, "qtype": "short_answer", "negative": 0},
    {"name": "Section E — 5 Marks", "count": 2, "marks": 5, "qtype": "long_answer", "negative": 0},
]}
class Gen(BaseModel): subject_code: str = "cs"; difficulty: str = "medium"
class Submit(BaseModel): answers: dict[str, object] = {}
def build_board_prompt(name, syl, diff):
    return (f"Create a complete CBSE Class 12 {name} board-style practice paper at {diff} difficulty. "
            "Use only the uploaded syllabus below. Follow this exact board pattern: 18 MCQs of 1 mark, "
            "3 assertion-reasoning MCQs of 1 mark, 7 short-answer questions of 2 marks, "
            "3 short-answer questions of 3 marks, and 2 long-answer questions of 5 marks. "
            "Return the complete paper in one response as a clearly formatted board question paper. "
            "Use headings for each section, number every question, show four options for objective questions, "
            "and include the correct answer and a model answer after each question. "
            f"{AR} "
            f"\n\nUPLOADED SYLLABUS:\n{syl}")
def view(g, reveal):
    qs = [{k: v for k, v in q.items() if reveal or k not in ("answer", "model_answer", "explanation")} for q in g.questions]
    spec = g.meta.get("spec", {})
    return {"id": g.id, "label": LABEL, "title": g.title, "subject_code": g.subject_code, "difficulty": g.difficulty, "status": g.status,
            "duration_min": spec.get("duration_min"), "instructions": spec.get("instructions", []), "sections": [s["name"] for s in spec.get("sections", [])],
            "board_sections": [{"name": s["name"], "count": s["count"], "marks": s["marks"], "qtype": s["qtype"]}
                                  for s in spec.get("sections", [])],
            "total_marks": g.total, "syllabus_version_id": g.syllabus_version_id, "blueprint_version": g.blueprint_version, "created_at": g.created_at,
            "questions": qs, "generated_text": g.meta.get("generated_text", ""), "score": g.score if reveal else None, "result": g.result if reveal else None}
def own(db, u, pid):
    g = db.get(GeneratedPaper, pid)
    if not g or g.user_id != u.id: raise HTTPException(404, "Paper not found")
    return g
@r.get("")
def mine(u: User = Depends(current_user), db: Session = Depends(get_db)):
    return [{"id": g.id, "title": g.title, "difficulty": g.difficulty, "status": g.status, "score": g.score, "total": g.total, "created_at": g.created_at}
            for g in db.query(GeneratedPaper).filter_by(user_id=u.id).order_by(GeneratedPaper.created_at.desc())]
@r.post("/generate", status_code=201)
def generate(b: Gen, u: User = Depends(current_user), db: Session = Depends(get_db)):
    sub = db.get(Subject, b.subject_code)
    if not sub or not sub.enabled: raise HTTPException(400, "This subject is coming soon")
    if b.difficulty not in ("easy", "medium", "hard"): raise HTTPException(400, "Bad difficulty")
    sv = db.query(SyllabusVersion).filter_by(subject_code=sub.code, is_active=True, status="published").first()
    if not sv: raise HTTPException(409, "Sample papers need a published syllabus (ask the admin)")
    limit(f"gen:{u.id}", 5, 3600)
    syl = "\n".join(f"- {x['title']}: " + "; ".join(x.get("topics", [])) for x in sv.content.get("units", []))[:5000]
    raw = ai.generate_sample_paper([{"role": "user", "content": build_board_prompt(sub.name, syl, b.difficulty)}])
    if not raw.strip():
        raise HTTPException(502, "Groq returned no displayable text. Check GROQ_MODEL availability and try again.")
    qs = []
    total = 0
    g = GeneratedPaper(user_id=u.id, subject_code=sub.code, syllabus_version_id=sv.id, blueprint_id="fixed-board-pattern", blueprint_version=1, difficulty=b.difficulty,
                       title=f"{sub.name} Practice Paper ({sv.academic_year})", questions=qs, total=total,
                       meta={"spec": BOARD_SPEC, "model": settings.GROQ_MODEL, "generated_text": raw})
    db.add(g); db.commit(); return view(g, False)
@r.get("/{pid}")
def get(pid: str, u: User = Depends(current_user), db: Session = Depends(get_db)):
    g = own(db, u, pid); return view(g, g.status == "submitted")
@r.post("/{pid}/submit")
def submit(pid: str, b: Submit, u: User = Depends(current_user), db: Session = Depends(get_db)):
    g = own(db, u, pid)
    if g.status == "submitted": raise HTTPException(409, "Already submitted")
    sc = c = i = 0; res = []
    for q in g.questions:
        supplied = b.answers.get(q["id"], [])
        if q["qtype"] in WRITTEN_TYPES:
            response = str(supplied).strip()
            st, m = ("written", 0) if response else ("skipped", 0)
            sel = response
        else:
            sel = sorted(set(supplied if isinstance(supplied, list) else []))
            if not sel: st, m = "skipped", 0
            elif sel == q["answer"]: st, m = "correct", q["marks"]; c += 1
            else: st, m = "incorrect", -q["negative"]; i += 1
        sc += m; res.append({"id": q["id"], "selected": sel, "status": st, "marks": m})
    g.score, g.correct, g.incorrect, g.result, g.status, g.submitted_at = sc, c, i, res, "submitted", datetime.utcnow()
    log(db, u.id, "paper"); db.commit(); return view(g, True)
