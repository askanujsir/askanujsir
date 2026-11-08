import csv, io, re, uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session
from .. import ai
from ..db import get_db
from ..models import *
from ..security import admin_user
from ..storage import get_storage
r = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(admin_user)])
MAX = 15 * 1024 * 1024; QT = ("single", "multiple", "assertion_reason")
def normalize_subject(code: str, db: Session) -> str:
    normalized = code.strip().lower()
    if not db.get(Subject, normalized):
        raise HTTPException(400, f"Unknown subject code: {code}")
    return normalized
def pdf_text(data):
    import fitz
    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:
        raise HTTPException(422, "Could not read the PDF file") from exc
    t = "\n".join(p.get_text() for p in doc)
    if len(t.strip()) >= 50: return t
    try: import pytesseract; from PIL import Image  # OCR fallback for scanned PDFs
    except ImportError: raise HTTPException(422, "Scanned PDF: install pytesseract and the Tesseract binary to enable OCR")
    t = "\n".join(pytesseract.image_to_string(Image.open(io.BytesIO(p.get_pixmap(dpi=200).tobytes("png")))) for p in doc)
    if len(t.strip()) < 50: raise HTTPException(422, "Could not read any text from this PDF")
    return t
async def ingest(f: UploadFile):
    data = await f.read(); name = (f.filename or "").lower()
    if len(data) > MAX: raise HTTPException(413, "File too large (max 15 MB)")
    if name.endswith(".pdf") and data[:4] == b"%PDF": return pdf_text(data), data
    if name.endswith(".docx") and data[:2] == b"PK":
        import docx
        try: return "\n".join(p.text for p in docx.Document(io.BytesIO(data)).paragraphs), data
        except Exception: raise HTTPException(422, "Invalid DOCX file")
    raise HTTPException(400, "Only valid PDF or DOCX files are allowed")
def save_doc(db, kind, owner, f, data):
    key = f"{kind}/{owner}/{uuid.uuid4().hex[:8]}-{re.sub(r'[^A-Za-z0-9._-]', '_', f.filename or 'file')}"
    try:
        get_storage().put(key, data)
    except OSError as exc:
        raise HTTPException(503, "Could not save the uploaded file. Check backend storage permissions.") from exc
    db.add(Document(kind=kind, owner_id=owner, filename=f.filename or "file", storage_key=key))
@r.get("/overview")
def overview(db: Session = Depends(get_db)):
    papers = dict(db.query(QuestionPaper.status, func.count()).group_by(QuestionPaper.status).all())
    return {"users": db.query(func.count(User.id)).scalar(), "conversations": db.query(func.count(Conversation.id)).scalar(),
            "practice_sessions": db.query(func.count(PracticeSession.id)).scalar(), "generated_papers": db.query(func.count(GeneratedPaper.id)).scalar(),
            "papers": papers, "syllabus_versions": db.query(func.count(SyllabusVersion.id)).scalar()}
@r.get("/academic-years")
def years(db: Session = Depends(get_db)): return [{"label": y.label, "is_current": y.is_current} for y in db.query(AcademicYear).order_by(AcademicYear.label.desc())]
@r.post("/academic-years", status_code=201)
def add_year(label: str, db: Session = Depends(get_db)):
    if not re.fullmatch(r"\d{4}-\d{2}", label): raise HTTPException(400, "Use format 2026-27")
    if not db.get(AcademicYear, label): db.add(AcademicYear(label=label)); db.commit()
    return {"ok": True}
@r.post("/academic-years/{label}/current")
def set_year(label: str, db: Session = Depends(get_db)):
    for y in db.query(AcademicYear): y.is_current = y.label == label
    db.commit(); return {"ok": True}
@r.post("/subjects/{code}/enabled")
def toggle(code: str, enabled: bool, db: Session = Depends(get_db)):
    subject = db.get(Subject, subject_code(code, db))
    subject.enabled = enabled; db.commit(); return {"ok": True}
# ---- syllabus
@r.get("/syllabus")
def list_syllabus(db: Session = Depends(get_db)):
    return [{"id": s.id, "subject_code": s.subject_code, "academic_year": s.academic_year, "status": s.status, "is_active": s.is_active, "content": s.content}
            for s in db.query(SyllabusVersion).order_by(SyllabusVersion.created_at.desc())]
@r.post("/syllabus", status_code=201)
async def syllabus(subject_code: str = Form(...), academic_year: str = Form(...), file: UploadFile = File(...), db: Session = Depends(get_db)):
    subject_code = normalize_subject(subject_code, db)
    if not re.fullmatch(r"\d{4}-\d{2}", academic_year.strip()):
        raise HTTPException(400, "Academic year must use format 2026-27")
    text, data = await ingest(file); units, cur = [], None
    for line in (l.strip() for l in text.splitlines() if l.strip()):  # heuristic; admin reviews/edits
        if re.match(r"^(unit|chapter)\b", line, re.I): cur = {"title": line, "topics": []}; units.append(cur)
        elif cur: cur["topics"].append(line)
    sv = SyllabusVersion(subject_code=subject_code, academic_year=academic_year, content={"units": units}); db.add(sv); db.flush()
    save_doc(db, "syllabus", sv.id, file, data); db.commit()
    return {"id": sv.id, "content": sv.content}
class Content(BaseModel): units: list[dict]
@r.put("/syllabus/{sid}")
def edit_syllabus(sid: str, b: Content, db: Session = Depends(get_db)):
    sv = db.get(SyllabusVersion, sid)
    if not sv: raise HTTPException(404, "Not found")
    sv.content = {"units": b.units}; db.commit(); return {"ok": True}
@r.post("/syllabus/{sid}/publish")
def publish_syllabus(sid: str, db: Session = Depends(get_db)):
    sv = db.get(SyllabusVersion, sid)
    if not sv: raise HTTPException(404, "Not found")
    for o in db.query(SyllabusVersion).filter_by(subject_code=sv.subject_code, is_active=True): o.is_active = False  # history kept
    sv.status, sv.is_active = "published", True; db.commit(); return {"ok": True}
# ---- papers
def clean(q):
    try:
        if q.get("qtype") not in QT: return None
        return dict(qtype=q["qtype"], text=str(q["text"]), options=[str(o) for o in q.get("options", [])], answer=[int(a) for a in q.get("answer", [])],
                    marks=float(q.get("marks") or 1), explanation=str(q.get("explanation", "")))
    except Exception: return None
def parse_mcqs(text: str, answer_key: str = "") -> list[dict]:
    questions, current, option = [], None, None
    answer_map = {}
    for line in answer_key.splitlines():
        match = re.match(r"^\s*(?:q(?:uestion)?\s*)?(\d+)\s*[\].:)\-]?\s*([A-Da-d])\b", line)
        if match: answer_map[int(match.group(1))] = ord(match.group(2).upper()) - ord("A")
    def flush():
        nonlocal current
        if current and len(current["options"]) >= 2:
            number = current.pop("number")
            if number in answer_map: current["answer"] = [answer_map[number]]
            questions.append(current)
        current = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line: continue
        question = re.match(r"^(\d+)\s*[\.)]\s*(.+)$", line)
        if question:
            flush()
            current = {"number": int(question.group(1)), "qtype": "single", "text": question.group(2).strip(),
                       "options": [], "answer": [], "marks": 1, "explanation": ""}
            option = None
            continue
        if current:
            choice = re.match(r"^(?:\(?([A-Da-d])\)|([A-Da-d])[\.)])\s+(.+)$", line)
            if choice:
                current["options"].append(choice.group(3).strip()); option = len(current["options"]) - 1
            elif option is not None:
                current["options"][option] += " " + line
            else:
                current["text"] += " " + line
    flush()
    return questions
def parse_csv_mcqs(data: bytes) -> tuple[list[dict], int]:
    try:
        rows = list(csv.DictReader(io.StringIO(data.decode("utf-8-sig"))))
    except UnicodeDecodeError as exc:
        raise HTTPException(422, "CSV must be UTF-8 encoded") from exc
    if not rows:
        raise HTTPException(422, "CSV contains no question rows")
    headers = [str(h or "").strip().lower() for h in (rows[0].keys())]
    required = ["question", "option_a", "option_b", "option_c", "option_d", "answer"]
    if any(h not in headers for h in required):
        raise HTTPException(422, "CSV headers must include exactly: question, option_a, option_b, option_c, option_d, answer; marks and explanation are optional")
    questions = []
    errors = []
    for row_number, row in enumerate(rows, 2):
        values = {(key or "").strip().lower(): (value or "").strip() for key, value in row.items()}
        text = values.get("question", "")
        options = [values.get(f"option_{letter}", "") for letter in "abcd"]
        qtype = "assertion_reason" if re.match(r"^\s*assertion\s*\(", text, re.I) else "single"
        if not text or sum(bool(option) for option in options) < 1:
            errors.append(f"row {row_number}: question and at least one option are required")
            continue
        answer = []
        try:
            for value in re.split(r"[,;|]", values.get("answer", "")):
                value = value.strip()
                if not value:
                    continue
                if len(value) != 1 or value.upper() not in "ABCD":
                    raise ValueError
                answer.append(ord(value.upper()) - ord("A"))
        except ValueError:
            errors.append(f"row {row_number}: answer must contain only A, B, C, or D")
            continue
        if not answer:
            errors.append(f"row {row_number}: answer is required")
            continue
        questions.append({"qtype": qtype, "text": text, "options": options, "answer": answer,
                          "marks": float(values.get("marks") or 1), "explanation": values.get("explanation", "")})
    if errors:
        raise HTTPException(422, "Invalid CSV rows: " + "; ".join(errors[:10]))
    return questions, 0
@r.get("/papers")
def list_papers(db: Session = Depends(get_db)):
    return [{"id": p.id, "subject_code": p.subject_code, "year": p.year, "title": p.title, "status": p.status, "count": len(p.questions)}
            for p in db.query(QuestionPaper).order_by(QuestionPaper.year.desc())]
@r.post("/papers/extract", status_code=201)
async def extract(subject_code: str = Form(...), year: int | None = Form(None), title: str = Form(...), negative: float = Form(0),
                  file: UploadFile = File(...), answer_key: UploadFile | None = File(None), db: Session = Depends(get_db)):
    subject_code = normalize_subject(subject_code, db)
    data = await file.read()
    if len(data) > MAX: raise HTTPException(413, "File too large (max 15 MB)")
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(400, "Paper uploads must be CSV files")
    raw, skipped = parse_csv_mcqs(data)
    qs = [x for x in map(clean, raw) if x]
    p = QuestionPaper(subject_code=subject_code, year=year or datetime.utcnow().year, title=title); db.add(p); db.flush()
    for n, q in enumerate(qs, 1): p.questions.append(Question(position=n, negative=negative, **q))
    save_doc(db, "paper", p.id, file, data)
    db.commit(); return {"id": p.id, "count": len(qs), "skipped_unsupported": skipped + len(raw) - len(qs)}
class QIn(BaseModel):
    qtype: str; text: str; options: list[str] = []; answer: list[int] = []; marks: float = 1; negative: float = 0; explanation: str = ""
@r.get("/papers/{pid}")
def get_paper(pid: str, db: Session = Depends(get_db)):
    p = db.get(QuestionPaper, pid)
    if not p: raise HTTPException(404, "Not found")
    return {"id": p.id, "status": p.status, "questions": [{c: getattr(q, c) for c in QIn.model_fields} for q in p.questions]}
@r.put("/papers/{pid}/questions")
def edit_questions(pid: str, b: list[QIn], db: Session = Depends(get_db)):
    p = db.get(QuestionPaper, pid)
    if not p: raise HTTPException(404, "Not found")
    if any(q.qtype not in QT for q in b): raise HTTPException(422, "Unsupported question type")
    db.query(Question).filter(Question.paper_id == p.id).delete(synchronize_session=False)
    db.flush()
    db.add_all(Question(paper_id=p.id, position=n, **q.model_dump()) for n, q in enumerate(b, 1))
    db.commit(); return {"ok": True, "count": len(b)}
@r.post("/papers/{pid}/publish")
def publish_paper(pid: str, db: Session = Depends(get_db)):
    p = db.get(QuestionPaper, pid)
    if not p: raise HTTPException(404, "Not found")
    bad = [q for q in p.questions if not q.answer or not any(option.strip() for option in q.options)
           or any(a < 0 or a >= len(q.options) or not q.options[a].strip() for a in q.answer)]
    if not p.questions or bad: raise HTTPException(422, "Every question needs options and a valid correct answer before publishing")
    p.status = "published"; db.commit(); return {"ok": True}
@r.post("/papers/{pid}/archive")
def archive_paper(pid: str, db: Session = Depends(get_db)):
    db.get(QuestionPaper, pid).status = "archived"; db.commit(); return {"ok": True}
@r.delete("/papers/{pid}", status_code=204)
def delete_draft(pid: str, db: Session = Depends(get_db)):
    p = db.get(QuestionPaper, pid)
    if p and p.status != "draft": raise HTTPException(409, "Only drafts can be deleted; archive instead")
    if p: db.delete(p); db.commit()
