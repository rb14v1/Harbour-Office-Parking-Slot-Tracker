import { Navigate, Route, Routes } from 'react-router-dom';
import Layout from './components/Layout.jsx';
import ProtectedRoute from './components/ProtectedRoute.jsx';
import DashboardPage from './pages/DashboardPage.jsx';
import SlotsPage from './pages/SlotsPage.jsx';
import MyParkingPage from './pages/MyParkingPage.jsx';
import ReportsPage from './pages/ReportsPage.jsx';
import HistoryPage from './pages/HistoryPage.jsx';
import AdminPage from './pages/AdminPage.jsx';
import AdminLoginPage from './pages/AdminLoginPage.jsx';
import NotFoundPage from './pages/NotFoundPage.jsx';
import IdentityGate from './components/IdentityGate.jsx';

export default function App() {
  return (
    <Routes>
      <Route path="/admin-login" element={<AdminLoginPage />} />
      <Route element={<Layout />}>
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/history" element={<IdentityGate><HistoryPage /></IdentityGate>} />
        <Route path="/slots" element={<IdentityGate><SlotsPage /></IdentityGate>} />
        <Route path="/my-parking" element={<IdentityGate><MyParkingPage /></IdentityGate>} />
        <Route element={<ProtectedRoute />}>
          <Route path="/reports" element={<ReportsPage />} />
          <Route path="/admin" element={<AdminPage />} />
        </Route>
      </Route>
      <Route path="/login" element={<Navigate to="/dashboard" replace />} />
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
