import { useState } from 'react';
import { identityApi } from '../api/services.js';
import { useAuth } from '../context/AuthContext.jsx';
import { useToast } from '../context/ToastContext.jsx';
import { errorMessage } from '../utils/format.js';

const NAME_RE = /^[A-Za-z]+(?: [A-Za-z]+)*$/;
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const VEHICLE_NUMBER_RE = /^[A-Za-z0-9 -]{4,15}$/;

function normaliseName(value) {
  return value.trim().split(/\s+/).join(' ');
}

/** Name, email, vehicle type and vehicle number. Saved in this browser after the backend confirms it. */
export function IdentityForm({ compact = false, onSaved }) {
  const { saveIdentity } = useAuth();
  const toast = useToast();
  const [form, setForm] = useState({ employee_name: '', email: '', vehicle_type: 'Car', vehicle_number: '' });
  const [errors, setErrors] = useState({});
  const [serverError, setServerError] = useState(null);
  const [saving, setSaving] = useState(false);

  function setField(name, value) {
    setForm((current) => ({ ...current, [name]: value }));
  }

  function validate() {
    const next = {};
    const name = normaliseName(form.employee_name);
    if (name.length < 2) next.employee_name = 'Enter your name.';
    else if (!NAME_RE.test(name)) next.employee_name = 'Use English letters and single spaces only.';
    if (!EMAIL_RE.test(form.email.trim())) next.email = 'Enter a valid email address.';
    if (!VEHICLE_NUMBER_RE.test(form.vehicle_number.trim())) next.vehicle_number = 'Enter 4 to 15 letters or digits, e.g. KA01AB1234.';
    return next;
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setServerError(null);
    const next = validate();
    setErrors(next);
    if (Object.keys(next).length) return;

    setSaving(true);
    try {
      const response = await identityApi.save({
        employee_name: normaliseName(form.employee_name),
        email: form.email.trim(),
        vehicle_type: form.vehicle_type,
        vehicle_number: form.vehicle_number.trim(),
      });
      saveIdentity(response.data);
      toast.success(response.message);
      onSaved?.(response.data);
    } catch (error) {
      setServerError(errorMessage(error));
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="row g-3">
      {serverError && <div className="col-12"><div className="alert alert-danger py-2 small mb-0">{serverError}</div></div>}
      <div className={compact ? 'col-md-6' : 'col-12'}>
        <label className="form-label small fw-semibold" htmlFor="identity-name">Your name</label>
        <input id="identity-name" className={`form-control ${errors.employee_name ? 'is-invalid' : ''}`} value={form.employee_name} onChange={(e) => setField('employee_name', e.target.value)} placeholder="e.g. Aarav Sharma" />
        {errors.employee_name && <div className="invalid-feedback">{errors.employee_name}</div>}
      </div>
      <div className={compact ? 'col-md-6' : 'col-12'}>
        <label className="form-label small fw-semibold" htmlFor="identity-email">Your email</label>
        <input id="identity-email" type="email" className={`form-control ${errors.email ? 'is-invalid' : ''}`} value={form.email} onChange={(e) => setField('email', e.target.value)} placeholder="name@company.com" />
        {errors.email && <div className="invalid-feedback">{errors.email}</div>}
      </div>
      <div className="col-md-6">
        <label className="form-label small fw-semibold" htmlFor="identity-vehicle-type">Vehicle type</label>
        <select id="identity-vehicle-type" className="form-select" value={form.vehicle_type} onChange={(e) => setField('vehicle_type', e.target.value)}>
          <option value="Car">Car</option>
          <option value="Bike">Bike</option>
        </select>
      </div>
      <div className="col-md-6">
        <label className="form-label small fw-semibold" htmlFor="identity-vehicle-number">Vehicle number</label>
        <input id="identity-vehicle-number" className={`form-control ${errors.vehicle_number ? 'is-invalid' : ''}`} value={form.vehicle_number} onChange={(e) => setField('vehicle_number', e.target.value.toUpperCase())} placeholder="KA01AB1234" />
        {errors.vehicle_number && <div className="invalid-feedback">{errors.vehicle_number}</div>}
      </div>
      <div className="col-12">
        <button type="submit" className="btn btn-primary" disabled={saving}>
          {saving && <span className="spinner-border spinner-border-sm me-2" />}
          Save my details
        </button>
      </div>
    </form>
  );
}

/** Shows the page only once the employee has entered name and email (or when an administrator is signed in). */
export default function IdentityGate({ children, allowAdmin = false }) {
  const { identity, isAdmin } = useAuth();
  if (identity || (allowAdmin && isAdmin)) {
    return children;
  }
  return (
    <div className="card" style={{ maxWidth: 640 }}>
      <div className="card-body">
        <h2 className="section-title">Enter your details</h2>
        <p className="text-muted small">
          Enter your name, email and vehicle once. This browser remembers them, so you do not need to enter them again.
        </p>
        <IdentityForm />
      </div>
    </div>
  );
}
