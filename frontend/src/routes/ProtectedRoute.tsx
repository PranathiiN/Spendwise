import { Navigate, Outlet, useLocation } from "react-router";
import { PageLoader } from "../components/common/Spinner";
import { useAuth } from "../contexts/AuthContext";

/** Only lets authenticated users through; otherwise redirects to /login. */
export function ProtectedRoute() {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) return <PageLoader />;
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  return <Outlet />;
}

/** Keeps logged-in users away from the login/register pages. */
export function PublicOnlyRoute() {
  const { user, loading } = useAuth();
  if (loading) return <PageLoader />;
  if (user) return <Navigate to="/dashboard" replace />;
  return <Outlet />;
}
