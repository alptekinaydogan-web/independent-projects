import { Navigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";

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
  if (role && user.role !== role) {
    return <Navigate to={user.role === "admin" ? "/admin" : "/rep"} replace />;
  }
  return children;
}
