import os, io, json
if os.path.exists("test.db"): os.remove("test.db")
os.environ.update(DATABASE_URL="sqlite:///./test.db", ADMIN_EMAIL="admin@test.com", ADMIN_PASSWORD="adminpass123", STORAGE_LOCAL_DIR="./test_storage")
import docx, pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.db import SessionLocal
from app import models as M, ai
@pytest.fixture(scope="module")
def c():
    with TestClient(app) as c: yield c
H = lambda t: {"Authorization": "Bearer " + t}
def reg(c, name, email):
    r = c.post("/api/auth/register", json={"name": name, "email": email, "password": "password123"}).json(); return H(r["token"]), r
def adm(c): return H(c.post("/api/auth/login", json={"email": "admin@test.com", "password": "adminpass123"}).json()["token"])
def test_auth_refresh_profile(c):
    assert c.get("/api/dashboard").status_code in (401, 403)
    h, r = reg(c, "Asha", "a@x.com")
    assert c.post("/api/auth/register", json={"name": "A", "email": "a@x.com", "password": "password123"}).status_code in (409, 422)
    n = c.post("/api/auth/refresh", json={"refresh_token": r["refresh_token"]}); assert n.status_code == 200
    assert c.post("/api/auth/refresh", json={"refresh_token": r["refresh_token"]}).status_code == 401  # rotated
    assert c.patch("/api/users/me", json={"name": "Asha K"}, headers=h).json()["name"] == "Asha K"
    assert c.post("/api/users/me/password", json={"current": "bad", "new": "newpassword1"}, headers=h).status_code == 400
def test_isolation_roles_coming_soon(c):
    h, _ = reg(c, "Asha", "iso1@x.com"); h2, _ = reg(c, "Bo", "iso2@x.com")
    cid = c.post("/api/chat/conversations", json={"subject_code": "cs"}, headers=h).json()["id"]
    assert c.get(f"/api/chat/conversations/{cid}/messages", headers=h2).status_code == 404
    assert c.delete(f"/api/chat/conversations/{cid}", headers=h2).status_code == 404
    assert c.post("/api/chat/conversations", json={"subject_code": "bio"}, headers=h).status_code == 400
    assert c.get("/api/admin/overview", headers=h).status_code == 403
    assert c.get("/api/admin/overview", headers=adm(c)).status_code == 200
def test_syllabus_versions(c):
    a = adm(c); ids = []
    with SessionLocal() as db:
        for y in ("2026-27", "2027-28"):
            s = M.SyllabusVersion(subject_code="cs", academic_year=y, content={"units": [{"title": "Unit 1", "topics": ["Python"]}]}); db.add(s); db.commit(); ids.append(s.id)
    for i in ids: assert c.post(f"/api/admin/syllabus/{i}/publish", headers=a).status_code == 200
    h, _ = reg(c, "Syl", "syl@x.com"); cid = c.post("/api/chat/conversations", json={"subject_code": "cs"}, headers=h).json()["id"]
    with SessionLocal() as db:
        assert db.get(M.SyllabusVersion, ids[0]).is_active is False  # history kept, not active
        assert db.get(M.Conversation, cid).syllabus_version_id == ids[1]
def mkpaper(year, status="draft", ans=True):
    with SessionLocal() as db:
        p = M.QuestionPaper(subject_code="cs", year=year, title=f"CS {year}", status=status); db.add(p); db.flush()
        for n, (t, a, m, neg) in enumerate([("single", [1], 1, .25), ("multiple", [0, 2], 2, 0), ("single", [0], 1, 0)], 1):
            p.questions.append(M.Question(position=n, qtype=t, text=f"Q{n}", options=["a", "b", "c"], answer=a if ans else [], marks=m, negative=neg))
        db.commit(); return p.id
def test_publish_and_practice(c):
    a = adm(c); bad = mkpaper(2031, ans=False)
    assert c.post(f"/api/admin/papers/{bad}/publish", headers=a).status_code == 422
    pid = mkpaper(2032); h, _ = reg(c, "Prac", "prac@x.com")
    assert all(p["year"] != 2032 for p in c.get("/api/pyq/papers?subject=cs", headers=h).json())  # draft hidden
    assert c.post(f"/api/admin/papers/{pid}/publish", headers=a).status_code == 200
    assert any(p["year"] == 2032 for p in c.get("/api/pyq/papers?subject=cs").json())
    s = c.post("/api/practice/start", json={"paper_id": pid, "mode": "untimed"}, headers=h).json()
    assert "answer" not in s["questions"][0]
    q = [x["id"] for x in s["questions"]]
    res = c.post(f"/api/practice/{s['session_id']}/submit", json={"answers": {q[0]: [1], q[1]: [0]}}, headers=h).json()
    assert (res["correct"], res["incorrect"], res["skipped"], res["score"], res["total"]) == (1, 1, 1, 1, 4)
    h2, _ = reg(c, "Quin", "prac2@x.com"); assert c.post(f"/api/practice/{s['session_id']}/submit", json={}, headers=h2).status_code == 404
    d = c.get("/api/dashboard", headers=h).json(); assert d["attempted"] == 2 and d["correct"] == 1 and d["streak"] == 1
    t = c.post("/api/practice/start", json={"paper_id": pid, "mode": "timed", "duration_min": 30}, headers=h).json()
    with SessionLocal() as db: db.get(M.PracticeSession, t["session_id"]).started_at = datetime.utcnow() - timedelta(hours=2); db.commit()
    late = c.post(f"/api/practice/{t['session_id']}/submit", json={"answers": {q[2]: [0]}}, headers=h).json()
    assert late["correct"] == 0 and late["skipped"] == 3  # expired: answers void
    assert c.get("/api/leaderboard?period=all", headers=h).json()["me"]["score"] == 7  # best attempt only: 2*1 + 5
def test_extraction_review_publish(c, monkeypatch):
    fake = lambda m, json_mode=False: json.dumps({"questions": [
        {"qtype": "single", "text": "What is 2+2?", "options": ["3", "4"], "answer": [1], "marks": 1},
        {"qtype": "descriptive", "text": "Explain TCP.", "options": [], "answer": [], "marks": 3}]})
    monkeypatch.setattr(ai, "chat", fake); a = adm(c)
    d = docx.Document(); d.add_paragraph("CS paper 2033"); b = io.BytesIO(); d.save(b)
    r = c.post("/api/admin/papers/extract", data={"subject_code": "cs", "year": "2033", "title": "CS 2033"}, files={"file": ("p.docx", b.getvalue())}, headers=a)
    assert r.status_code == 201 and r.json()["count"] == 1 and r.json()["skipped_unsupported"] == 1
    pid = r.json()["id"]
    with SessionLocal() as db: assert db.query(M.Document).filter_by(owner_id=pid, kind="paper").count() == 1
    assert c.post(f"/api/admin/papers/{pid}/publish", headers=a).status_code == 200
    assert any(p["year"] == 2033 for p in c.get("/api/pyq/papers?subject=cs").json())  # appears dynamically
    assert c.post("/api/admin/papers/extract", data={"subject_code": "cs", "year": "1", "title": "x"}, files={"file": ("p.txt", b"hello")}, headers=a).status_code == 400
def test_sample_paper_and_leaderboard(c, monkeypatch):
    a = adm(c); spec = {"duration_min": 30, "instructions": ["All compulsory"], "sections": [
        {"name": "A", "count": 2, "marks": 1, "qtype": "single"}, {"name": "B", "count": 1, "marks": 2, "qtype": "multiple"}]}
    bid = c.post("/api/admin/blueprints", json={"subject_code": "cs", "spec": spec}, headers=a).json()["id"]
    assert c.post(f"/api/admin/blueprints/{bid}/publish", headers=a).status_code == 200
    def fake(m, json_mode=False):
        qs = [{"section": s, "qtype": t, "text": f"{s}{i}", "options": ["a", "b", "c"], "answer": [0] if t == "single" else [0, 1], "explanation": "x"} for s, t, n in (("A", "single", 2), ("B", "multiple", 1)) for i in range(n)]
        return json.dumps({"questions": qs})
    monkeypatch.setattr(ai, "chat", fake); h, _ = reg(c, "Gen", "gen@x.com")
    p = c.post("/api/sample-papers/generate", json={"subject_code": "cs"}, headers=h).json()
    assert p["label"].startswith("AI-Generated Practice Paper") and "answer" not in p["questions"][0]
    with SessionLocal() as db: key = {q["id"]: q["answer"] for q in db.get(M.GeneratedPaper, p["id"]).questions}
    r = c.post(f"/api/sample-papers/{p['id']}/submit", json={"answers": key}, headers=h).json()
    assert r["score"] == 4 and r["questions"][0]["answer"]
    monkeypatch.setattr(ai, "chat", lambda m, json_mode=False: json.dumps({"questions": []}))
    assert c.post("/api/sample-papers/generate", json={"subject_code": "cs"}, headers=h).status_code == 502  # never an incomplete paper
    assert c.get("/api/leaderboard?period=weekly", headers=h).json()["rows"][0]["score"] >= 3
def test_community_ws(c):
    t = c.post("/api/auth/register", json={"name": "Chat", "email": "ws@x.com", "password": "password123"}).json()["token"]
    with c.websocket_connect(f"/api/community/ws?token={t}") as ws:
        ws.send_text("<b>hello</b>"); m = ws.receive_json(); assert m["content"] == "<b>hello</b>" and m["user"] == "Chat"
    assert c.get("/api/community/messages", headers=H(t)).json()[-1]["content"] == "<b>hello</b>"
