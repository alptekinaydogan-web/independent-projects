import { createContext, useContext, useEffect, useState, useCallback } from "react";
import api, { formatApiError, describeAxiosError } from "@/lib/api";

const AuthCtx = createContext(null);

const KNOWN_ROLES = new Set(["admin", "owner", "representative"]);

// Guard against malformed /auth/me payloads (missing role, HTML SPA
// fallback slipping through a misrouted proxy, etc.). Anything that
// doesn't look like a real user object is treated as anonymous — the
// UI must never sit in a "truthy but role-less user" state because
// that used to blank-screen the app.
function isValidUser(u) {
  return !!(u && typeof u === "object" && KNOWN_ROLES.has(u.role) && u.id && u.email);
}

export function AuthProvider({ children }) {
  // null = checking; false = anon; object = user
  const [user, setUser] = useState(null);

  const refreshMe = useCallback(async () => {
    try {
      const { data } = await api.get("/auth/me");
      if (isValidUser(data)) {
        setUser(data);
        return data;
      }
      // Payload is unusable (stale token → deleted user, migration
      // artefact, unexpected shape). Wipe any local token and treat
      // as anonymous so the app renders the login form instead of
      // silently redirecting into a broken protected route.
      localStorage.removeItem("imh_token");
      setUser(false);
      return null;
    } catch {
      setUser(false);
      return null;
    }
  }, []);

  useEffect(() => { refreshMe(); }, [refreshMe]);

  const login = async (email, password) => {
    try {
      const { data } = await api.post("/auth/login", { email, password });
      if (!isValidUser(data.user)) {
        return { ok: false, error: "Your account has no valid role assigned. Contact the administrator." };
      }
      if (data.access_token) localStorage.setItem("imh_token", data.access_token);
      setUser(data.user);
      return { ok: true, user: data.user };
    } catch (e) {
      // Log the full axios error to the browser console so operators
      // can see status code, response body, and code (ERR_NETWORK etc.)
      // when triaging production login failures.
      // eslint-disable-next-line no-console
      console.error("[auth/login] failed:", {
        status:      e?.response?.status,
        statusText:  e?.response?.statusText,
        data:        e?.response?.data,
        code:        e?.code,
        message:     e?.message,
      });
      return { ok: false, error: describeAxiosError(e) };
    }
  };

  const logout = async () => {
    try { await api.post("/auth/logout"); } catch {}
    localStorage.removeItem("imh_token");
    setUser(false);
  };

  return (
    <AuthCtx.Provider value={{ user, login, logout, refreshMe, setUser }}>
      {children}
    </AuthCtx.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthCtx);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
