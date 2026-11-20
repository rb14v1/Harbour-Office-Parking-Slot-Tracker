import { useState } from 'react';
import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';
import { useToast } from '../context/ToastContext.jsx';

const NAV_ITEMS = [
  { to: '/dashboard', label: 'Dashboard', icon: 'bi-speedometer2' },
  { to: '/slots', label: 'Parking Slots', icon: 'bi-grid-3x3-gap-fill' },
  { to: '/my-parking', label: 'My Parking', icon: 'bi-car-front-fill' },
  { to: '/history', label: 'My History', icon: 'bi-clock-history' },
];

const ADMIN_NAV_ITEMS = [
  { to: '/reports', label: 'Reports', icon: 'bi-bar-chart-line-fill' },
  { to: '/admin', label: 'Administration', icon: 'bi-shield-lock-fill' },
];

export default function Layout() {
  const { identity, isAdmin, clearIdentity, adminLogout } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const navItems = isAdmin ? [...NAV_ITEMS, ...ADMIN_NAV_ITEMS] : NAV_ITEMS;

  function handleChangeDetails() {
    clearIdentity();
    toast.info('Enter your details again to continue.');
    navigate('/my-parking');
  }

  function handleAdminSignOut() {
    adminLogout();
    toast.info('Administrator signed out.');
    navigate('/dashboard', { replace: true });
  }

  return (
    <div className="app-shell">
      <aside className={`app-sidebar ${sidebarOpen ? 'open' : ''}`}>
        <div className="sidebar-brand">
          <span className="brand-icon"><i className="bi bi-p-square-fill" /></span>
          <div>
            <div className="brand-title">ParkSmart</div>
            <div className="brand-subtitle">Office Parking Tracker</div>
          </div>
        </div>
        <nav className="sidebar-nav" aria-label="Main navigation">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}
              onClick={() => setSidebarOpen(false)}
            >
              <i className={`bi ${item.icon}`} />
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          {isAdmin ? (
            <button type="button" className="btn btn-sm btn-outline-light w-100" onClick={handleAdminSignOut}>
              <i className="bi bi-box-arrow-right me-1" />Sign out administrator
            </button>
          ) : (
            <Link to="/admin-login" className="sidebar-admin-link" onClick={() => setSidebarOpen(false)}>
              <i className="bi bi-shield-lock me-2" />Administrator sign-in
            </Link>
          )}
        </div>
      </aside>

      {sidebarOpen && <div className="sidebar-backdrop" onClick={() => setSidebarOpen(false)} />}

      <div className="app-main">
        <header className="app-topbar">
          <button
            type="button"
            className="btn btn-outline-secondary d-lg-none me-2"
            aria-label="Toggle navigation"
            onClick={() => setSidebarOpen((open) => !open)}
          >
            <i className="bi bi-list" />
          </button>
          <div className="topbar-title">
            {identity ? `Welcome, ${identity.employee_name}` : 'Welcome'}
          </div>
          <div className="ms-auto d-flex align-items-center gap-3">
            {identity && (
              <div className="text-end d-none d-sm-block">
                <div className="fw-semibold small">{identity.email}</div>
                <div className="text-muted small">{identity.vehicle_type} · {identity.vehicle_number}</div>
              </div>
            )}
            {identity && (
              <button type="button" className="btn btn-outline-secondary btn-sm" onClick={handleChangeDetails}>
                <i className="bi bi-pencil me-1" />Change details
              </button>
            )}
            {isAdmin && <span className="badge bg-primary text-uppercase">Administrator</span>}
          </div>
        </header>
        <main className="app-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
