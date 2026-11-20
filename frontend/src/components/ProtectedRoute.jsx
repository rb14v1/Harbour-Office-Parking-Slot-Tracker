import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';

/** Guards administrator pages. Employees use the open pages with their name and email. */
export default function AdminRoute() {
  const { isAdmin } = useAuth();
  const location = useLocation();

  if (!isAdmin) {
    return <Navigate to="/admin-login" replace state={{ from: location.pathname }} />;
  }
  return <Outlet />;
}
