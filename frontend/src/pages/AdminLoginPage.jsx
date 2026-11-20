import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';
import { useToast } from '../context/ToastContext.jsx';
import { normaliseError } from '../api/client.js';

export default function AdminLoginPage() {
  const { adminLogin, isAdmin } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();
  const location = useLocation();
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError(null);
    if (!password) {
      setError('Enter the administrator password.');
      return;
    }
    setSubmitting(true);
    try {
      await adminLogin(password);
      toast.success('Administrator session started.');
      navigate(location.state?.from || '/reports', { replace: true });
    } catch (err) {
      setError(normaliseError(err).message);
    } finally {
      setSubmitting(false);
    }
  }

  if (isAdmin) {
    return (
      <div className="login-page">
        <div className="card shadow-sm p-4 text-center" style={{ maxWidth: 420 }}>
          <p className="mb-3">You are signed in as administrator.</p>
          <Link to="/reports" className="btn btn-primary">Go to reports</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="login-page">
      <div className="login-card card shadow-lg">
        <div className="card-body p-4 p-md-5">
          <div className="text-center mb-4">
            <div className="login-logo"><i className="bi bi-shield-lock-fill" /></div>
            <h1 className="h4 fw-bold mt-3 mb-1">Administrator sign-in</h1>
            <p className="text-muted small mb-0">Reports and administration are restricted.</p>
          </div>

          {error && (
            <div className="alert alert-danger py-2 small" role="alert">
              <i className="bi bi-exclamation-circle-fill me-2" />
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} noValidate>
            <div className="mb-4">
              <label htmlFor="admin-password" className="form-label fw-semibold">Administrator password</label>
              <div className="input-group">
                <span className="input-group-text"><i className="bi bi-lock" /></span>
                <input
                  id="admin-password"
                  type="password"
                  className={`form-control ${error ? 'is-invalid' : ''}`}
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  autoComplete="current-password"
                  disabled={submitting}
                />
              </div>
            </div>
            <button type="submit" className="btn btn-primary w-100 py-2 fw-semibold" disabled={submitting}>
              {submitting ? <><span className="spinner-border spinner-border-sm me-2" />Checking...</> : 'Sign in as administrator'}
            </button>
          </form>
          <p className="text-center small mt-4 mb-0">
            <Link to="/dashboard">Back to dashboard</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
