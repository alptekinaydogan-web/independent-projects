import { Navigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";

const ADMIN_ROLES = new Set(["admin", "owner"]);

function landingFor(role) {
  return ADMIN_ROLES.has(role) ? "/admin" : "/rep";
}

export default function ProtectedRoute({ children, role }) {
  const { user } = useAuth();
  if (user === null) {
    return (
      <div className="h-screen w-screen flex items-center justify-center bg-[#F9F9F6]">
        <div className="imh-eyebrow" data-testid="auth-loading">Loading platform</div>
      </div>
    );
  }
  if (user === false) return <Navigate to="/" replace />;

  if (role === "admin") {
    if (!ADMIN_ROLES.has(user.role)) return <Navigate to={landingFor(user.role)} replace />;
  } else if (role && user.role !== role) {
    return <Navigate to={landingFor(user.role)} replace />;
  }
  return children;
}
