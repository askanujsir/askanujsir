import axios from "axios";
const BASE = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000") + "/api";
export const WS = import.meta.env.VITE_WS_BASE_URL || "ws://localhost:8000";
export const api = axios.create({ baseURL: BASE });
api.interceptors.request.use((c) => { const t = localStorage.getItem("token"); if (t) c.headers.Authorization = `Bearer ${t}`; return c; });
api.interceptors.response.use((r) => r, async (e) => {
  const o = e.config, rt = localStorage.getItem("refresh");
  if (e.response?.status === 401 && rt && !o._retried && !o.url.includes("/auth/")) {
    o._retried = true;
    try { const r = await axios.post(BASE + "/auth/refresh", { refresh_token: rt });
      localStorage.setItem("token", r.data.token); localStorage.setItem("refresh", r.data.refresh_token); return api(o);
    } catch { localStorage.clear(); location.href = "/login"; }
  }
  return Promise.reject(e);
});
export const err = (e: any) => { const d = e?.response?.data?.detail; return typeof d === "string" ? d : e?.message || "Something went wrong"; };
