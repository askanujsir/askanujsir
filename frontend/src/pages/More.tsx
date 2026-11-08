import { useEffect, useRef, useState } from "react";
import { api, err, WS } from "../api";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkBreaks from "remark-breaks";

export function SamplePapers() {
  const [list, setList] = useState<any[]>([]); const [p, setP] = useState<any>(null); const [ans, setAns] = useState<Record<string, number[]>>({});
  const [diff, setDiff] = useState("medium"); const [busy, setBusy] = useState(false); const [e, setE] = useState("");
  const load = () => api.get("/sample-papers").then((r) => setList(r.data)); useEffect(() => { load(); }, []);
  const open = async (id: string) => { const r = await api.get(`/sample-papers/${id}`); setP(r.data); setAns({}); };
  const gen = async () => { setBusy(true); setE(""); try { const r = await api.post("/sample-papers/generate", { subject_code: "cs", difficulty: diff }); setP(r.data); setAns({}); load(); } catch (x) { setE(err(x)); } setBusy(false); };
  const submit = async () => { try { const r = await api.post(`/sample-papers/${p.id}/submit`, { answers: ans }); setP(r.data); load(); } catch (x) { setE(err(x)); } };
  const done = p?.status === "submitted"; const res: Record<string, any> = Object.fromEntries((p?.result || []).map((x: any) => [x.id, x]));
  const pick = (q: any, k: number) => { if (done) return; const cur = ans[q.id] || []; setAns({ ...ans, [q.id]: q.qtype === "multiple" ? (cur.includes(k) ? cur.filter((x) => x !== k) : [...cur, k]) : [k] }); };
  return <div><h1 className="text-3xl font-black mb-4">Generate Sample Paper</h1>
    <div className="nb p-4 flex flex-wrap gap-3 items-center bg-pop-purple"><b>Computer Science</b>
      <select className="inp w-auto" value={diff} onChange={(x) => setDiff(x.target.value)}>{["easy", "medium", "hard"].map((d) => <option key={d}>{d}</option>)}</select>
      <button className="btn" disabled={busy} onClick={gen}>{busy ? "Generating… (can take a minute)" : "Generate Sample Paper"}</button></div>
    {e && <p className="text-red-600 font-bold mt-2">{e}</p>}
    <div className="flex flex-wrap gap-2 my-3">{list.map((x) => <button key={x.id} className="btn bg-white text-sm" onClick={() => open(x.id)}>{x.title} · {x.difficulty} · {x.status === "submitted" ? `${x.score}/${x.total}` : "new"}</button>)}</div>
    {p && <div className="nb p-5">
      <p className="inline-block border-2 border-ink bg-pop-yellow px-2 font-black text-sm">{p.label}</p>
      <h2 className="text-2xl font-black mt-2">{p.title}</h2>
      <p className="text-sm">Fixed CBSE board pattern{done && ` · Score ${p.score}`}</p>
      <p className="text-sm mt-2 font-bold">Board format: {p.board_sections?.map((s: any) => `${s.count} × ${s.marks}-mark ${s.qtype.replace("_", " ")}`).join(" · ")}</p>
      <div className="mt-4 break-words bg-white border-2 border-ink rounded-lg p-4 chat-markdown">
        <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]}>
          {(p.generated_text || "This paper has no generated text.").replace(/<br\s*\/?>/gi, "\n")}
        </ReactMarkdown>
      </div>
    </div>}
  </div>;
}

export function Community() {
  const [ms, setMs] = useState<any[]>([]); const [t, setT] = useState(""); const [on, setOn] = useState(false); const [e, setE] = useState("");
  const ws = useRef<WebSocket | null>(null); const end = useRef<HTMLDivElement>(null);
  useEffect(() => {
    api.get("/community/messages").then((r) => setMs(r.data)); let stop = false;
    const conn = async () => { try { await api.get("/auth/me"); } catch {} if (stop) return;
      const s = new WebSocket(`${WS}/api/community/ws?token=${localStorage.getItem("token")}`); ws.current = s;
      s.onopen = () => setOn(true); s.onclose = () => { setOn(false); if (!stop) setTimeout(conn, 2000); };
      s.onmessage = (ev) => { const m = JSON.parse(ev.data); if (m.error) setE(m.error); else setMs((x) => [...x, m]); }; };
    conn(); return () => { stop = true; ws.current?.close(); };
  }, []);
  useEffect(() => { end.current?.scrollIntoView(); }, [ms]);
  const send = () => { if (t.trim() && on) { ws.current?.send(t); setT(""); setE(""); } };
  return <div><h1 className="text-3xl font-black mb-2">Community — Class 12 Room</h1><p className="mb-2 font-bold">{on ? "🟢 Connected" : "🔴 Reconnecting…"}</p>
    <div className="nb p-3 h-[55vh] overflow-auto space-y-2">{ms.map((m) => <div key={m.id} className="border-2 border-ink rounded-lg p-2 bg-pop-sky/40">
      <b>{m.user}</b> <span className="text-xs">{new Date(m.created_at).toLocaleTimeString()}</span>
      <button className="text-xs underline ml-2" onClick={() => api.post(`/community/messages/${m.id}/report`).then(() => setE("Reported. Thanks!"))}>report</button>
      <p className="whitespace-pre-wrap break-words">{m.content}</p></div>)}<div ref={end} /></div>
    {e && <p className="text-red-600 font-bold">{e}</p>}
    <div className="flex gap-2 mt-3"><input className="inp" maxLength={500} value={t} onChange={(x) => setT(x.target.value)} onKeyDown={(x) => x.key === "Enter" && send()} placeholder="Say something helpful…" /><button className="btn" onClick={send}>Send</button></div></div>;
}

export function Leaderboard() {
  const [p, setP] = useState("weekly"); const [d, setD] = useState<any>(null); useEffect(() => { api.get("/leaderboard", { params: { period: p } }).then((r) => setD(r.data)); }, [p]);
  return <div><h1 className="text-3xl font-black mb-3">Leaderboard</h1><div className="flex gap-2 mb-3">{["weekly", "all"].map((x) => <button key={x} className={`btn capitalize ${p === x ? "" : "bg-white"}`} onClick={() => setP(x)}>{x === "all" ? "All-time" : x}</button>)}</div>
    <p className="text-sm mb-2">Score = best attempt per PYQ paper (2 pts per correct answer + 5 for completing) + your top 5 sample papers (1 pt per correct answer).</p>
    {d?.me && <p className="font-black mb-2">Your rank: #{d.me.rank} · {d.me.score} pts</p>}
    <div className="nb overflow-x-auto"><table className="w-full text-left"><thead><tr className="bg-pop-yellow">{["Rank", "Student", "Score", "Attempted", "Accuracy", "Streak"].map((h) => <th key={h} className="p-2">{h}</th>)}</tr></thead>
      <tbody>{d?.rows.map((r: any) => <tr key={r.rank} className={r.me ? "bg-pop-mint font-bold" : ""}><td className="p-2">{r.rank}</td><td>{r.name}</td><td>{r.score}</td><td>{r.attempted}</td><td>{r.accuracy}%</td><td>{r.streak}🔥</td></tr>)}</tbody></table>
      {d && !d.rows.length && <p className="p-4">No activity yet — complete a practice session to get on the board!</p>}</div></div>;
}

export function Profile() {
  const [me, setMe] = useState<any>(null); const [d, setD] = useState<any>(null); const [name, setName] = useState(""); const [pw, setPw] = useState({ current: "", new: "" }); const [m, setM] = useState("");
  useEffect(() => { api.get("/auth/me").then((r) => { setMe(r.data); setName(r.data.name); }); api.get("/dashboard").then((r) => setD(r.data)); }, []);
  if (!me || !d) return <p>Loading…</p>;
  return <div className="max-w-xl space-y-4"><h1 className="text-3xl font-black">Profile</h1>
    <div className="nb p-4 bg-pop-sky"><p><b>{me.name}</b> · {me.email}</p><p>Joined {new Date(me.created_at).toLocaleDateString()}</p><p>Streak {d.streak} (longest {d.longest_streak}) · {d.attempted} questions · {d.accuracy}% accuracy</p></div>
    <div className="nb p-4 space-y-2"><input className="inp" value={name} onChange={(x) => setName(x.target.value)} /><button className="btn" onClick={() => api.patch("/users/me", { name }).then(() => setM("Name updated")).catch((x) => setM(err(x)))}>Update name</button></div>
    <div className="nb p-4 space-y-2"><input className="inp" type="password" placeholder="Current password" onChange={(x) => setPw({ ...pw, current: x.target.value })} /><input className="inp" type="password" placeholder="New password (min 8)" onChange={(x) => setPw({ ...pw, new: x.target.value })} />
      <button className="btn" onClick={() => api.post("/users/me/password", pw).then(() => setM("Password changed")).catch((x) => setM(err(x)))}>Change password</button></div>{m && <p className="font-bold">{m}</p>}</div>;
}
