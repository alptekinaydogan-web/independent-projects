import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

const api = axios.create({
  baseURL: API,
  withCredentials: true,
  headers: { "Content-Type": "application/json" },
});

// Send Bearer as backup if we ever store token
api.interceptors.request.use((cfg) => {
  const t = localStorage.getItem("imh_token");
  if (t) cfg.headers.Authorization = `Bearer ${t}`;
  return cfg;
});

export function formatApiError(detail) {
  if (detail == null) return "Something went wrong. Please try again.";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail))
    return detail.map((e) => (e && typeof e.msg === "string" ? e.msg : JSON.stringify(e))).filter(Boolean).join(" ");
  if (detail && typeof detail.msg === "string") return detail.msg;
  return String(detail);
}

// Surface the actual failure category for a caught axios error. Used
// by auth/login and friends so operators can distinguish "wrong
// password" (401 + detail) from "backend unreachable / nginx 502 /
// CORS preflight blocked / DNS failure" (no response, or non-JSON
// response) — which otherwise all collapse into the same generic
// "Something went wrong" toast.
export function describeAxiosError(err) {
  if (!err) return "Unknown error";
  // 1. FastAPI-style JSON body: {detail: "..."}
  const detail = err.response?.data?.detail;
  if (detail != null) return formatApiError(detail);
  // 2. Response arrived, but not FastAPI-shaped (e.g. nginx HTML page
  //    for 502/504 — data is a string starting with "<html").
  if (err.response) {
    const status = err.response.status;
    const statusText = err.response.statusText || "";
    return `Server error ${status}${statusText ? ` — ${statusText}` : ""}. The server is up but the API did not respond correctly.`;
  }
  // 3. No response at all — network / CORS / DNS / connection reset.
  if (err.code === "ERR_NETWORK") return "Network error — the server is unreachable (CORS, DNS, or the backend is down).";
  if (err.code === "ECONNABORTED") return "Request timed out — the server took too long to respond.";
  return err.message || "Unknown network error";
}

export default api;
