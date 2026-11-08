import { useEffect, useState } from "react";
import { api, err } from "../api";
const TABS = ["Overview", "Subjects & Years", "Syllabus", "Papers"];
type P = { run: (f: () => Promise<any>, ok?: string) => Promise<void> };
export function Admin() {
  const [tab, setTab] = useState(TABS[0]); const [msg, setMsg] = useState("");
  const run = async (f: () => Promise<any>, ok = "Done") => { try { await f(); setMsg(ok); } catch (e) { setMsg(err(e)); } };
  return <div><h1 className="text-3xl font-black mb-3">Content Administration</h1>
    <div className="flex flex-wrap gap-2 mb-3">{TABS.map((t) => <button key={t} className={`btn ${tab === t ? "" : "bg-white"}`} onClick={() => { setTab(t); setMsg(""); }}>{t}</button>)}</div>
    {msg && <p className="nb p-2 mb-3 bg-pop-mint font-bold">{msg}</p>}
    {tab === TABS[0] && <Overview />}{tab === TABS[1] && <Subjects run={run} />}{tab === TABS[2] && <Syllabus run={run} />}{tab === TABS[3] && <Papers run={run} />}</div>;
}
function Overview() { const [d, setD] = useState<any>(null); useEffect(() => { api.get("/admin/overview").then((r) => setD(r.data)); }, []);
  return <pre className="nb p-4 bg-white overflow-auto">{d ? JSON.stringify(d, null, 2) : "Loading…"}</pre>; }
function Subjects({ run }: P) {
  const [s, setS] = useState<any[]>([]); const [y, setY] = useState<any[]>([]); const [l, setL] = useState("");
  const load = () => { api.get("/subjects").then((r) => setS(r.data)); api.get("/admin/academic-years").then((r) => setY(r.data)); }; useEffect(load, []);
  return <div className="grid md:grid-cols-2 gap-4"><div className="nb p-4"><h3 className="font-black">Subjects</h3>{s.map((x) => <label key={x.code} className="flex gap-2 my-1"><input type="checkbox" checked={x.enabled} onChange={(e) => run(() => api.post(`/admin/subjects/${x.code}/enabled`, null, { params: { enabled: e.target.checked } }).then(load))} />{x.name}</label>)}</div>
    <div className="nb p-4"><h3 className="font-black">Academic years</h3>{y.map((x) => <div key={x.label} className="my-1">{x.label} {x.is_current ? "✅ current" : <button className="underline" onClick={() => run(() => api.post(`/admin/academic-years/${x.label}/current`).then(load))}>make current</button>}</div>)}
      <div className="flex gap-2 mt-2"><input className="inp" placeholder="2027-28" value={l} onChange={(e) => setL(e.target.value)} /><button className="btn" onClick={() => run(() => api.post("/admin/academic-years", null, { params: { label: l } }).then(load))}>Add</button></div></div></div>;
}
function Syllabus({ run }: P) {
  const [list, setList] = useState<any[]>([]); const [sel, setSel] = useState<any>(null); const [json, setJson] = useState(""); const [f, setF] = useState<{ sub: string; yr: string; file: File | null }>({ sub: "cs", yr: "", file: null });
  const load = () => api.get("/admin/syllabus").then((r) => setList(r.data)); useEffect(() => { load(); }, []);
  const up = () => {
    if (!f.file) return run(async () => { throw new Error("Choose a PDF or DOCX syllabus first"); });
    if (!/^\d{4}-\d{2}$/.test(f.yr.trim())) return run(async () => { throw new Error("Academic year must use format 2026-27"); });
    const fd = new FormData(); fd.append("subject_code", f.sub); fd.append("academic_year", f.yr.trim()); fd.append("file", f.file);
    run(() => api.post("/admin/syllabus", fd).then(load), "Uploaded as draft — review below");
  };
  return <div className="space-y-4"><div className="nb p-4 flex flex-wrap gap-2 items-center"><input className="inp w-28" value={f.sub} onChange={(e) => setF({ ...f, sub: e.target.value })} /><input className="inp w-32" placeholder="2026-27" value={f.yr} onChange={(e) => setF({ ...f, yr: e.target.value })} /><input type="file" accept=".pdf,.docx" onChange={(e) => setF({ ...f, file: e.target.files?.[0] || null })} /><button className="btn" onClick={up}>Upload syllabus</button></div>
    {list.map((s) => <div key={s.id} className="nb p-3 flex justify-between items-center"><span>{s.subject_code} · {s.academic_year} · {s.status}{s.is_active && " · ACTIVE"}</span><button className="btn" onClick={() => { setSel(s); setJson(JSON.stringify(s.content.units, null, 2)); }}>Review</button></div>)}
    {sel && <div className="nb p-3"><p className="font-bold">Edit units JSON ([{"{"}"title","topics":[…]{"}"}])</p><textarea className="inp h-64 font-mono text-sm" value={json} onChange={(e) => setJson(e.target.value)} />
      <div className="flex gap-2 mt-2"><button className="btn bg-white" onClick={() => run(async () => { await api.put(`/admin/syllabus/${sel.id}`, { units: JSON.parse(json) }); load(); }, "Saved")}>Save</button>
        <button className="btn" onClick={() => run(async () => { await api.put(`/admin/syllabus/${sel.id}`, { units: JSON.parse(json) }); await api.post(`/admin/syllabus/${sel.id}/publish`); load(); }, "Published & activated")}>Save, publish & activate</button></div></div>}</div>;
}
function Papers({ run }: P) {
  const [list, setList] = useState<any[]>([]); const [rev, setRev] = useState<string | null>(null);
  const [subjects, setSubjects] = useState<any[]>([]);
  const [f, setF] = useState<any>({ sub: "cs", year: "", title: "", neg: "0", file: null, key: null });
  const load = () => api.get("/admin/papers").then((r) => setList(r.data)); useEffect(() => { load(); api.get("/subjects").then((r) => setSubjects(r.data)); }, []);
  const up = () => { const fd = new FormData(); fd.append("subject_code", f.sub); if (f.year.trim()) fd.append("year", f.year.trim()); fd.append("title", f.title); fd.append("negative", f.neg); fd.append("file", f.file);
    run(() => api.post("/admin/papers/extract", fd).then((r) => { load(); setRev(r.data.id); }), "Extracted — review every question before publishing"); };
  if (rev) return <Review id={rev} run={run} back={() => { setRev(null); load(); }} />;
  return <div className="space-y-4"><div className="nb p-4 flex flex-wrap gap-2 items-center"><select className="inp w-40" value={f.sub} onChange={(e) => setF({ ...f, sub: e.target.value })}>{subjects.map((s) => <option key={s.code} value={s.code}>{s.name}</option>)}</select><label>Year (optional) <input className="inp w-24" placeholder="Current year" onChange={(e) => setF({ ...f, year: e.target.value })} /></label><input className="inp w-48" placeholder="Title" onChange={(e) => setF({ ...f, title: e.target.value })} /><input className="inp w-24" title="negative marks" value={f.neg} onChange={(e) => setF({ ...f, neg: e.target.value })} />
    <label>MCQ CSV <input type="file" accept=".csv,text/csv" onChange={(e) => setF({ ...f, file: e.target.files?.[0] })} /></label><button className="btn" onClick={up}>Extract</button></div>
    <p className="text-sm">Required CSV columns: <code>question, option_a, option_b, option_c, option_d, answer</code>. Optional columns: <code>marks, explanation</code>. Blank option columns are allowed for fill-in-the-blank rows, but complete options are required before publishing.</p>
    {list.map((p) => <div key={p.id} className="nb p-3 flex flex-wrap gap-2 justify-between items-center"><span>{p.year} · {p.title} · {p.count} Qs · <b>{p.status}</b></span><span className="flex gap-2">
      <button className="btn bg-white" onClick={() => setRev(p.id)}>Review</button>{p.status === "published" && <button className="btn bg-white" onClick={() => run(() => api.post(`/admin/papers/${p.id}/archive`).then(load))}>Archive</button>}
      {p.status === "draft" && <button className="btn bg-pop-pink" onClick={() => run(() => api.delete(`/admin/papers/${p.id}`).then(load))}>Delete</button>}</span></div>)}</div>;
}
function Review({ id, run, back }: P & { id: string; back: () => void }) {
  const [qs, setQs] = useState<any[]>([]); const [loading, setLoading] = useState(true); const [error, setError] = useState("");
  useEffect(() => {
    setLoading(true); setError("");
    api.get(`/admin/papers/${id}`)
      .then((r) => setQs(r.data.questions.map((q: any) => ({ ...q, _a: q.answer.join(",") }))))
      .catch((e) => setError(err(e)))
      .finally(() => setLoading(false));
  }, [id]);
  const set = (i: number, k: string, v: any) => setQs(qs.map((q, n) => (n === i ? { ...q, [k]: v } : q)));
  const move = (i: number, d: number) => { const a = [...qs], j = i + d; if (j < 0 || j >= a.length) return; [a[i], a[j]] = [a[j], a[i]]; setQs(a); };
  const add = () => setQs([...qs, { qtype: "single", text: "", options: ["", ""], answer: [], _a: "", marks: 1, negative: 0, explanation: "" }]);
  const body = () => qs.map((q) => ({ qtype: q.qtype, text: q.text, options: q.options, answer: q._a.split(",").map((s: string) => parseInt(s)).filter((n: number) => !isNaN(n)), marks: +q.marks, negative: +q.negative, explanation: q.explanation || "" }));
  if (loading) return <div className="space-y-3"><button className="btn bg-white" onClick={back}>← Back</button><p className="nb p-4">Loading extracted questions…</p></div>;
  if (error) return <div className="space-y-3"><button className="btn bg-white" onClick={back}>← Back</button><p className="nb p-4 text-red-600 font-bold">{error}</p></div>;
  return <div className="space-y-3"><div className="flex flex-wrap gap-2 items-center"><button className="btn bg-white" onClick={back}>← Back</button><b>Review paper · {qs.length} question{qs.length === 1 ? "" : "s"}</b><button className="btn" onClick={add}>+ Add question</button></div>
    {!qs.length && <p className="nb p-4 bg-pop-yellow">No supported MCQs were extracted. Add questions manually below, or go back and upload a paper containing MCQs.</p>}
    {qs.map((q, i) => <div key={i} className="nb p-3 space-y-2"><div className="flex gap-2 items-center"><b>Q{i + 1}</b>
      <select className="inp w-auto" value={q.qtype} onChange={(e) => set(i, "qtype", e.target.value)}>{["single", "multiple", "assertion_reason"].map((t) => <option key={t}>{t}</option>)}</select>
      marks<input className="inp w-16" value={q.marks} onChange={(e) => set(i, "marks", e.target.value)} />neg<input className="inp w-16" value={q.negative} onChange={(e) => set(i, "negative", e.target.value)} />
      <button onClick={() => move(i, -1)}>↑</button><button onClick={() => move(i, 1)}>↓</button><button className="text-red-600 font-bold" onClick={() => setQs(qs.filter((_, n) => n !== i))}>Remove</button></div>
      <textarea className="inp" value={q.text} onChange={(e) => set(i, "text", e.target.value)} /><textarea className="inp" placeholder="One option per line" value={q.options.join("\n")} onChange={(e) => set(i, "options", e.target.value.split("\n"))} />
      <input className="inp" placeholder="Correct option indices, 0 = first (e.g. 1 or 0,2)" value={q._a} onChange={(e) => set(i, "_a", e.target.value)} /><input className="inp" placeholder="Explanation (optional)" value={q.explanation || ""} onChange={(e) => set(i, "explanation", e.target.value)} /></div>)}
    <div className="flex gap-2"><button className="btn bg-white" onClick={() => run(() => api.put(`/admin/papers/${id}/questions`, body()), "Saved")}>Save changes</button>
      <button className="btn" onClick={() => run(async () => { await api.put(`/admin/papers/${id}/questions`, body()); await api.post(`/admin/papers/${id}/publish`); }, "Published — now visible to students")}>Save & publish</button></div></div>;
}
