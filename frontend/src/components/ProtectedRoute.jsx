import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";

const ADMIN_ROLES = new Set(["admin", "owner"]);
const KNOWN_ROLES = new Set(["admin", "owner", "representative"]);

// Where should a user with *this* role land after auth? Returns null for
// unknown roles so we can force-logout instead of Navigate-looping.
function landingFor(role) {
  if (ADMIN_ROLES.has(role)) return "/admin";
  if (role === "representative") return "/rep";
  return null;
}

export default function ProtectedRoute({ children, role }) {
  const { user, logout } = useAuth();
  const location = useLocation();

  // Auth check in progress.
  if (user === null) {
    return (
      <div className="h-screen w-screen flex items-center justify-center bg-[#F9F9F6]">
        <div className="imh-eyebrow" data-testid="auth-loading">Loading platform</div>
      </div>
    );
  }

  // Anonymous.
  if (user === false) return <Navigate to="/" replace />;

  // Authenticated but with a role the app doesn't understand
  // (stale token, deleted user, half-migrated document). Force
  // sign-out to break any redirect loop and land back on `/`.
  // This is what would previously blank the screen when landing on
  // `/rep`: ProtectedRoute would `<Navigate to="/rep">` — a no-op
  // against the current URL — and render nothing at all.
  if (!KNOWN_ROLES.has(user.role)) {
    logout();
    return <Navigate to="/" replace />;
  }

  // Role guard for this route.
  const required = role === "admin" ? ADMIN_ROLES : (role ? new Set([role]) : null);
  if (required && !required.has(user.role)) {
    const target = landingFor(user.role);
    // Extra safety: if we're already at the target path, don't
    // `<Navigate>` to it (that renders null / blank). Send home.
    if (!target || target === location.pathname) {
      return <Navigate to="/" replace />;
    }
    return <Navigate to={target} replace />;
  }

  return children;
}
