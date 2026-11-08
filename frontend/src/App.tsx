import { useEffect, useState } from "react";
import { Routes, Route, Link, Navigate, useNavigate } from "react-router-dom";
import { Brain, ListChecks, LayoutDashboard, LogOut, Trash2, Send, Sparkles, MessagesSquare, Trophy, UserRound, ShieldCheck } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkBreaks from "remark-breaks";
import { Admin } from "./pages/Admin";
import { SamplePapers, Community, Leaderboard, Profile } from "./pages/More";
import { api, err } from "./api";

const Logo = () => <Link to="/" className="flex items-center gap-2 font-black text-2xl"><img src="/logo.png" alt="" className="h-9" onError={(e: any) => (e.currentTarget.style.display = "none")} />askanujsir</Link>;

function Landing() {
  const [subs, setSubs] = useState<any[]>([]);
  useEffect(() => { api.get("/subjects").then((r) => setSubs(r.data)).catch(() => {}); }, []);
  const F = [["AI Chat Companion", "A tutor grounded in the active syllabus."], ["Previous Year Questions", "Timed or untimed PYQ practice with full review."], ["AI-Generated Sample Papers", "CBSE-pattern papers built from a blueprint."], ["Performance Analytics", "Accuracy, subject-wise trends and history."], ["Student Community", "Real-time discussion with other students."], ["Streaks & Leaderboards", "Stay consistent and climb the ranks."]];
  const steps = ["Create your free account", "Pick a subject", "Practise PYQs and chat with the AI tutor", "Generate sample papers and track your streak"];
  const C = ["#FFE45E", "#A78BFA", "#FF914D", "#9BF6C0", "#75D9FF", "#FF8FAB"];
  return <div><div className="max-w-5xl mx-auto p-6" id="home">
    <nav className="flex flex-wrap justify-between items-center gap-3 mb-10"><Logo /><div className="flex flex-wrap gap-4 items-center font-bold"><a href="#home">Home</a><a href="#subjects">Subjects</a><a href="#features">Features</a><a href="#about">About</a><Link className="btn bg-white" to="/login">Login</Link><Link className="btn" to="/register">Get Started</Link></div></nav>
    <h1 className="text-5xl md:text-6xl font-black leading-tight">Your Class 12 Boards Journey, Made Smarter.</h1>
    <p className="mt-4 text-lg max-w-2xl">Practice previous year questions, learn with AI, generate sample papers and track your preparation — all in one place.</p>
    <div className="flex gap-3 mt-6"><Link to="/register" className="btn text-lg">Start Learning</Link><a href="#subjects" className="btn bg-white text-lg">Explore Subjects</a></div>
    <h2 id="subjects" className="text-3xl font-black mt-14 mb-4">Subjects</h2>
    <div className="grid sm:grid-cols-3 gap-5">{subs.map((s, i) => <div key={s.code} className="nb p-4" style={{ background: C[i % 6] }}><h3 className="font-black text-xl">{s.name}</h3><p className="text-sm">{s.description}</p>
      <span className="inline-block mt-2 border-2 border-ink bg-white rounded-full px-3 text-sm font-bold">{s.enabled ? "Available" : "Coming Soon"}</span></div>)}</div>
    <h2 id="features" className="text-3xl font-black mt-14 mb-4">Features</h2>
    <div className="grid sm:grid-cols-3 gap-5">{F.map(([t, d], i) => <div key={t} className="nb p-4" style={{ background: C[(i + 2) % 6] }}><h3 className="font-black">{t}</h3><p className="text-sm">{d}</p></div>)}</div>
    <h2 className="text-3xl font-black mt-14 mb-4">How it works</h2>
    <div className="grid sm:grid-cols-4 gap-4">{steps.map((t, i) => <div key={t} className="nb p-4"><div className="text-3xl font-black">{i + 1}</div><p className="font-bold">{t}</p></div>)}</div>
    <h2 id="about" className="text-3xl font-black mt-14 mb-2">About</h2><p className="max-w-2xl">askanujsir is an AI-powered practice platform for CBSE Class 12 boards. Generated papers are practice material in the CBSE pattern, not official CBSE papers.</p></div>
    <footer className="mt-16 border-t-4 border-ink bg-pop-yellow p-8"><div className="max-w-5xl mx-auto grid sm:grid-cols-4 gap-6"><div><Logo /><p className="text-sm mt-2">AI-powered CBSE Class 12 preparation.</p></div>
      <div><b>Subjects</b>{subs.map((s) => <p key={s.code} className="text-sm">{s.name}</p>)}</div><div><b>Platform</b><p className="text-sm">AI Tutor · PYQs · Sample Papers · Community · Leaderboard</p></div>
      <div><b>Account</b><p><Link to="/login">Login</Link></p><p><Link to="/register">Register</Link></p></div></div><p className="text-center text-sm mt-6">© {new Date().getFullYear()} askanujsir</p></footer></div>;
}

function AuthPage({ mode }: { mode: "login" | "register" }) {
  const nav = useNavigate(); const [f, setF] = useState({ name: "", email: "", password: "", confirm: "" }); const [role, setRole] = useState("student"); const [msg, setMsg] = useState("");
  const submit = async () => {
    if (role === "teacher") return setMsg("Teacher Portal is currently under development. Stay tuned!");
    if (mode === "register" && f.password !== f.confirm) return setMsg("Passwords do not match");
    try { const r = await api.post(`/auth/${mode}`, f); localStorage.setItem("token", r.data.token); localStorage.setItem("refresh", r.data.refresh_token); nav("/app"); } catch (e) { setMsg(err(e)); }
  };
  return <div className="max-w-md mx-auto p-6 mt-10"><Logo /><div className="nb p-6 mt-6 space-y-3">
    <div className="flex gap-2">{["student", "teacher"].map((r) => <button key={r} onClick={() => setRole(r)} className={`btn flex-1 capitalize ${role === r ? "" : "bg-white"}`}>{r}</button>)}</div>
    {mode === "register" && <input className="inp" placeholder="Name" onChange={(e) => setF({ ...f, name: e.target.value })} />}
    <input className="inp" placeholder="Email" onChange={(e) => setF({ ...f, email: e.target.value })} />
    <input className="inp" type="password" placeholder="Password (min 8)" onChange={(e) => setF({ ...f, password: e.target.value })} />
    {mode === "register" && <input className="inp" type="password" placeholder="Confirm password" onChange={(e) => setF({ ...f, confirm: e.target.value })} />}
    {msg && <p className="font-bold text-red-600">{msg}</p>}
    <button className="btn w-full" onClick={submit}>{mode === "login" ? "Login" : "Create account"}</button></div></div>;
}

function Shell({ children }: any) {
  const nav = useNavigate(); const [me, setMe] = useState<any>(null);
  useEffect(() => { api.get("/auth/me").then((r) => setMe(r.data)).catch(() => {}); }, []);
  if (!localStorage.getItem("token")) return <Navigate to="/login" />;
  const L = ({ to, icon: I, t }: any) => <Link to={to} className="btn bg-white flex items-center gap-2"><I size={18} />{t}</Link>;
  const out = () => { api.post("/auth/logout", { refresh_token: localStorage.getItem("refresh") }).catch(() => {}); localStorage.clear(); nav("/"); };
  return <div className="md:flex min-h-screen"><aside className="md:w-64 p-4 space-y-3 border-r-4 border-ink bg-pop-yellow"><Logo />
    <L to="/app" icon={LayoutDashboard} t="Overview" /><L to="/app/chat" icon={Brain} t="AI Chat Companion" /><L to="/app/practice" icon={ListChecks} t="Practice PYQs" /><L to="/app/sample" icon={Sparkles} t="Generate Sample Paper" />
    <L to="/app/community" icon={MessagesSquare} t="Community" /><L to="/app/leaderboard" icon={Trophy} t="Leaderboard" /><L to="/app/profile" icon={UserRound} t="Profile" />
    {me?.role === "admin" && <L to="/app/admin" icon={ShieldCheck} t="Admin" />}
    <button className="btn bg-white flex items-center gap-2 w-full" onClick={out}><LogOut size={18} />Logout</button></aside><main className="flex-1 p-6 min-w-0">{children}</main></div>;
}

function Dashboard() {
  const [d, setD] = useState<any>(null); useEffect(() => { api.get("/dashboard").then((r) => setD(r.data)); }, []);
  if (!d) return <p>Loading…</p>; const lb = d.leaderboard;
  const cards = [["Attempted", d.attempted], ["Correct", d.correct], ["Incorrect", d.incorrect], ["Skipped", d.skipped], ["Accuracy %", d.accuracy], ["Streak", d.streak], ["Longest streak", d.longest_streak], ["Active days", d.active_days], ["Chats", d.conversations], ["Messages", d.messages], ["Papers generated", d.sample_total], ["Papers completed", d.sample_completed], ["Weekly rank", lb.weekly.rank ?? "–"], ["All-time rank", lb.all.rank ?? "–"], ["Community posts", d.community_messages]];
  const max = Math.max(1, ...d.over_time.map((x: any) => x.attempted));
  return <div><h1 className="text-3xl font-black mb-4">Overview</h1><div className="grid grid-cols-2 md:grid-cols-5 gap-4">{cards.map(([k, v]: any, i) => <div key={k} className="nb p-4" style={{ background: ["#9BF6C0", "#75D9FF", "#FF8FAB", "#FFE45E", "#A78BFA"][i % 5] }}><div className="text-3xl font-black">{v}</div><div className="font-bold">{k}</div></div>)}</div>
    <div className="grid md:grid-cols-2 gap-4 mt-6"><div className="nb p-4"><h2 className="font-black mb-2">Subject-wise accuracy</h2>{d.subject_accuracy.length ? d.subject_accuracy.map((s: any) => <p key={s.subject}>{s.subject}: <b>{s.accuracy}%</b> ({s.attempted} attempted)</p>) : <p>No practice yet.</p>}</div>
      <div className="nb p-4"><h2 className="font-black mb-2">Questions attempted over time</h2><div className="flex items-end gap-1 h-24">{d.over_time.slice(-14).map((x: any) => <div key={x.day} title={`${x.day}: ${x.attempted}`} className="flex-1 bg-pop-purple border-2 border-ink" style={{ height: `${(100 * x.attempted) / max}%` }} />)}</div></div>
      <div className="nb p-4"><h2 className="font-black mb-2">Recent practice sessions</h2>{d.recent.map((s: any, n: number) => <p key={n}>{s.score}/{s.total} · {new Date(s.at).toLocaleDateString()}</p>)}{!d.recent.length && <p>None yet.</p>}</div>
      <div className="nb p-4"><h2 className="font-black mb-2">Top students (weekly)</h2>{lb.weekly.top.map((t: any) => <p key={t.rank}>#{t.rank} {t.name} — {t.score}</p>)}{!lb.weekly.top.length && <p>No activity this week.</p>}</div>
      <div className="nb p-4"><h2 className="font-black mb-2">Recent chats</h2>{d.recent_chats.map((c: any) => <p key={c.id}>{c.title}</p>)}{!d.recent_chats.length && <p>None yet.</p>}</div>
      <div className="nb p-4"><h2 className="font-black mb-2">Recent sample papers</h2>{d.recent_papers.map((c: any) => <p key={c.id}>{c.title} · {c.status}</p>)}{!d.recent_papers.length && <p>None yet.</p>}</div></div>
    <h2 className="text-xl font-black mt-6 mb-2">Activity (last 12 weeks)</h2>
    <div className="grid grid-flow-col grid-rows-7 gap-1 w-max">{Array.from({ length: 84 }).map((_, i) => { const day = new Date(Date.now() - (83 - i) * 864e5).toLocaleDateString("en-CA", { timeZone: "Asia/Kolkata" }); const n = d.heatmap[day] || 0;
      return <div key={i} title={`${day}: ${n}`} className="w-4 h-4 border border-ink" style={{ background: n ? (n > 2 ? "#16a34a" : "#9BF6C0") : "#fff" }} />; })}</div></div>;
}

function normalizeChatMarkdown(content: string) {
  return content
    .replace(/<br\s*\/?>/gi, "\n")
    .replace(/^(\s*)[•◦▪‣]\s+/gm, "$1- ");
}

function Chat() {
  const [cs, setCs] = useState<any[]>([]); const [cur, setCur] = useState<string | null>(null); const [ms, setMs] = useState<any[]>([]); const [txt, setTxt] = useState(""); const [busy, setBusy] = useState(false); const [e, setE] = useState("");
  const load = () => api.get("/chat/conversations").then((r) => { setCs(r.data); return r.data; });
  useEffect(() => { load().then((r) => { if (!r.length) mk(); else open(r[0].id); }).catch((x) => setE(err(x))); }, []);
  const open = (id: string) => { setCur(id); api.get(`/chat/conversations/${id}/messages`).then((r) => setMs(r.data)); };
  const mk = async () => { try { const r = await api.post("/chat/conversations", { subject_code: "cs" }); await load(); open(r.data.id); } catch (x) { setE(err(x)); } };
  const send = async () => { if (!cur || !txt.trim()) return; const t = txt; setTxt(""); setBusy(true); setE(""); setMs((m) => [...m, { role: "user", content: t }]);
    try { const r = await api.post(`/chat/conversations/${cur}/messages`, { content: t }); setMs((m) => [...m, r.data]); load(); } catch (x) { setE(err(x)); } setBusy(false); };
  return <div className="md:flex gap-4 h-[calc(100vh-3rem)] min-h-0"><div className="md:w-60 space-y-2 overflow-y-auto"><button className="btn w-full" onClick={mk}>+ New chat (Computer Science)</button>
    <p className="text-xs">Biology, Maths, Physics, Chemistry, English — Coming Soon</p>
    {cs.map((c) => <div key={c.id} className={`nb p-2 flex justify-between ${cur === c.id ? "bg-pop-sky" : ""}`}><button className="text-left truncate" onClick={() => open(c.id)}>{c.title}</button><button onClick={async () => { await api.delete(`/chat/conversations/${c.id}`); if (cur === c.id) setCur(null); load(); }}><Trash2 size={16} /></button></div>)}</div>
    <div className="flex-1 nb p-4 min-h-0 flex flex-col overflow-hidden"><div className="flex-1 min-h-0 space-y-3 overflow-y-auto pr-1">{ms.map((m, i) => <div key={i} className={`p-3 border-2 border-ink rounded-xl ${m.role === "user" ? "bg-pop-yellow ml-12 whitespace-pre-wrap" : "bg-pop-mint mr-12 chat-markdown"}`}>{m.role === "assistant" ? <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]}>{normalizeChatMarkdown(m.content)}</ReactMarkdown> : m.content}</div>)}{busy && <p className="font-bold">Thinking…</p>}</div>
      {e && <p className="text-red-600 font-bold">{e}</p>}
      {cur && <div className="flex gap-2 mt-3"><input className="inp" value={txt} onChange={(x) => setTxt(x.target.value)} onKeyDown={(x) => x.key === "Enter" && send()} placeholder="Ask about your syllabus…" /><button className="btn" onClick={send}><Send size={18} /></button></div>}</div></div>;
}

function Practice() {
  const [ps, setPs] = useState<any[]>([]); const [mode, setMode] = useState("timed"); const [mins, setMins] = useState(30);
  const [s, setS] = useState<any>(null); const [i, setI] = useState(0); const [ans, setAns] = useState<Record<string, number[]>>({}); const [left, setLeft] = useState(0); const [res, setRes] = useState<any>(null); const [e, setE] = useState("");
  useEffect(() => { api.get("/pyq/papers", { params: { subject: "cs" } }).then((r) => setPs(r.data)); }, []);
  const start = async (id: string) => { try { const r = await api.post("/practice/start", { paper_id: id, mode, duration_min: mins }); setS(r.data); setLeft(mode === "timed" ? mins * 60 : 0); setAns({}); setI(0); setRes(null); } catch (x) { setE(err(x)); } };
  const submit = async () => { const r = await api.post(`/practice/${s.session_id}/submit`, { answers: ans }); setRes(r.data); setS(null); };
  useEffect(() => { if (!s || mode !== "timed") return; if (left <= 0) { submit(); return; } const t = setTimeout(() => setLeft(left - 1), 1000); return () => clearTimeout(t); }, [left, s]);
  if (res) return <div><h1 className="text-3xl font-black">Result: {res.score}/{res.total} ({res.percentage}%)</h1><p>Correct {res.correct} · Incorrect {res.incorrect} · Skipped {res.skipped} · Accuracy {res.accuracy}% · {res.time_taken_s}s</p>
    {res.review.map((q: any, n: number) => <div key={q.id} className={`nb p-3 mt-3 ${q.status === "correct" ? "bg-pop-mint" : q.status === "incorrect" ? "bg-pop-pink" : "bg-white"}`}>
      <b>{n + 1}. {q.text}</b>
      <p>Your answer: {q.selected.map((x: number) => q.options[x]).join(", ") || "skipped"}</p>
      <p>Correct: {q.answer.map((x: number) => q.options[x]).join(", ")}</p>
      <div className="mt-2 space-y-1">
        {q.options.map((option: string, i: number) => <div key={i} className={`rounded-md border-2 border-ink px-2 py-1 ${q.answer.includes(i) ? "bg-pop-mint text-green-950" : q.selected.includes(i) ? "bg-pop-pink text-red-950" : "bg-white"}`}>
          {String.fromCharCode(65 + i)}. {option}
        </div>)}
      </div>
      {q.explanation && <p className={`text-sm mt-2 p-2 rounded-md border-2 border-ink ${q.status === "correct" ? "bg-pop-mint text-green-950" : "bg-pop-pink text-red-950"}`}><b>Explanation:</b> {q.explanation}</p>}
    </div>)}
    <button className="btn mt-4" onClick={() => setRes(null)}>Back</button></div>;
  if (s) { const q = s.questions[i], multi = q.qtype === "multiple", cur = ans[q.id] || [];
    const pick = (k: number) => setAns({ ...ans, [q.id]: multi ? (cur.includes(k) ? cur.filter((x) => x !== k) : [...cur, k]) : [k] });
    return <div><div className="flex justify-between font-black"><span>Q{i + 1}/{s.questions.length}</span>{mode === "timed" && <span>{Math.floor(left / 60)}:{String(left % 60).padStart(2, "0")}</span>}</div>
      <div className="nb p-4 mt-2"><p className="font-bold whitespace-pre-wrap">{q.text}</p>{multi && <p className="text-sm">Select all that apply</p>}{q.options.map((o: string, k: number) => <button key={k} onClick={() => pick(k)} className={`block w-full text-left border-2 border-ink rounded-lg p-2 mt-2 ${cur.includes(k) ? "bg-pop-purple" : "bg-white"}`}>{o}</button>)}</div>
      <div className="flex flex-wrap gap-1 my-3">{s.questions.map((x: any, n: number) => <button key={x.id} onClick={() => setI(n)} className={`w-8 h-8 border-2 border-ink rounded ${ans[x.id]?.length ? "bg-pop-mint" : "bg-white"}`}>{n + 1}</button>)}</div>
      <div className="flex gap-2"><button className="btn bg-white" disabled={i === 0} onClick={() => setI(i - 1)}>Prev</button><button className="btn bg-white" onClick={() => setAns({ ...ans, [q.id]: [] })}>Clear</button><button className="btn bg-white" disabled={i === s.questions.length - 1} onClick={() => setI(i + 1)}>Next</button><button className="btn" onClick={() => confirm("Submit test?") && submit()}>Submit</button></div></div>; }
  return <div><h1 className="text-3xl font-black mb-4">Practice PYQs — Computer Science</h1>
    <div className="flex gap-3 mb-4 items-center"><select className="inp w-auto" value={mode} onChange={(x) => setMode(x.target.value)}><option value="timed">Timed</option><option value="untimed">Untimed</option></select>{mode === "timed" && <input className="inp w-24" type="number" min={1} value={mins} onChange={(x) => setMins(+x.target.value)} />}</div>
    {e && <p className="text-red-600 font-bold">{e}</p>}{!ps.length && <p className="nb p-4">No published papers yet. An admin must upload and publish one.</p>}
    <div className="grid sm:grid-cols-3 gap-4">{ps.map((p) => <button key={p.id} className="nb p-4 bg-pop-sky text-left" onClick={() => start(p.id)}><b className="text-2xl">{p.year}</b><p>{p.title} · {p.count} Qs</p></button>)}</div></div>;
}

export default function App() {
  const S = (c: any) => <Shell>{c}</Shell>;
  return <Routes><Route path="/" element={<Landing />} /><Route path="/login" element={<AuthPage mode="login" />} /><Route path="/register" element={<AuthPage mode="register" />} />
    <Route path="/app" element={S(<Dashboard />)} /><Route path="/app/chat" element={S(<Chat />)} /><Route path="/app/practice" element={S(<Practice />)} /><Route path="/app/sample" element={S(<SamplePapers />)} />
    <Route path="/app/community" element={S(<Community />)} /><Route path="/app/leaderboard" element={S(<Leaderboard />)} /><Route path="/app/profile" element={S(<Profile />)} /><Route path="/app/admin" element={S(<Admin />)} /></Routes>;
}
