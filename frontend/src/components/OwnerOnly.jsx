import { Navigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";

export default function OwnerOnly({ children }) {
  const { user } = useAuth();
  if (user === null) return null;
  if (user === false) return <Navigate to="/" replace />;
  if (user.role !== "owner") return <Navigate to="/admin" replace />;
  return children;
}
