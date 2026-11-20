import { useState } from 'react';
import { employeeApi, slotApi } from '../api/services.js';
import { errorMessage } from '../utils/format.js';

const SLOT_ID_PATTERN = /^[A-Za-z0-9-]{3,20}$/;
const EMPLOYEE_ID_PATTERN = /^[A-Za-z0-9-]{3,20}$/;
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function ModalShell({ title, onClose, children, footer }) {
  return (
    <>
      <div className="modal d-block" tabIndex="-1" role="dialog" aria-modal="true" aria-labelledby="form-modal-title">
        <div className="modal-dialog modal-dialog-centered modal-lg modal-dialog-scrollable">
          <div className="modal-content">
            <div className="modal-header">
              <h5 className="modal-title" id="form-modal-title">{title}</h5>
              <button type="button" className="btn-close" aria-label="Close" onClick={onClose} />
            </div>
            <div className="modal-body">{children}</div>
            <div className="modal-footer">{footer}</div>
          </div>
        </div>
      </div>
      <div className="modal-backdrop show" />
    </>
  );
}

export function SlotFormModal({ slot, onClose, onSaved }) {
  const isEdit = Boolean(slot);
  const [form, setForm] = useState({
    slot_id: slot?.slot_id || '',
    floor: slot?.floor || '',
    location: slot?.location || '',
    vehicle_type: slot?.vehicle_type || 'Car',
    status: slot?.status === 'Reserved' ? 'Reserved' : 'Available',
  });
  const [errors, setErrors] = useState({});
  const [serverError, setServerError] = useState(null);
  const [saving, setSaving] = useState(false);

  function setField(name, value) {
    setForm((current) => ({ ...current, [name]: value }));
  }

  function validate() {
    const next = {};
    if (!isEdit && !SLOT_ID_PATTERN.test(form.slot_id.trim())) next.slot_id = 'Use 3–20 letters, digits or hyphens.';
    if (!form.floor.trim()) next.floor = 'Floor is required.';
    if (form.location.trim().length < 2) next.location = 'Location must be at least 2 characters.';
    return next;
  }

  async function handleSave(event) {
    event.preventDefault();
    setServerError(null);
    const next = validate();
    setErrors(next);
    if (Object.keys(next).length) return;

    setSaving(true);
    try {
      const response = isEdit
        ? await slotApi.update(slot.slot_id, {
            floor: form.floor.trim(),
            location: form.location.trim(),
            vehicle_type: form.vehicle_type,
            status: slot.status === 'Occupied' ? undefined : form.status,
          })
        : await slotApi.create({
            slot_id: form.slot_id.trim(),
            floor: form.floor.trim(),
            location: form.location.trim(),
            vehicle_type: form.vehicle_type,
          });
      onSaved(response.message);
    } catch (error) {
      setServerError(errorMessage(error));
    } finally {
      setSaving(false);
    }
  }

  return (
    <ModalShell
      title={isEdit ? `Edit slot ${slot.slot_id}` : 'Add parking slot'}
      onClose={onClose}
      footer={
        <>
          <button type="button" className="btn btn-outline-secondary" onClick={onClose} disabled={saving}>Cancel</button>
          <button type="submit" form="slot-form" className="btn btn-primary" disabled={saving}>
            {saving && <span className="spinner-border spinner-border-sm me-2" />}
            {isEdit ? 'Save changes' : 'Create slot'}
          </button>
        </>
      }
    >
      {serverError && <div className="alert alert-danger py-2 small">{serverError}</div>}
      <form id="slot-form" onSubmit={handleSave} noValidate className="row g-3">
        <div className="col-md-6">
          <label className="form-label small fw-semibold" htmlFor="slot-id">Slot ID</label>
          <input id="slot-id" className={`form-control ${errors.slot_id ? 'is-invalid' : ''}`} value={form.slot_id} disabled={isEdit} onChange={(e) => setField('slot_id', e.target.value.toUpperCase())} placeholder="e.g. G-C07" />
          {errors.slot_id && <div className="invalid-feedback">{errors.slot_id}</div>}
        </div>
        <div className="col-md-3">
          <label className="form-label small fw-semibold" htmlFor="slot-floor">Floor</label>
          <input id="slot-floor" className={`form-control ${errors.floor ? 'is-invalid' : ''}`} value={form.floor} onChange={(e) => setField('floor', e.target.value)} placeholder="G, 1, 2..." />
          {errors.floor && <div className="invalid-feedback">{errors.floor}</div>}
        </div>
        <div className="col-md-3">
          <label className="form-label small fw-semibold" htmlFor="slot-type">Vehicle type</label>
          <select id="slot-type" className="form-select" value={form.vehicle_type} onChange={(e) => setField('vehicle_type', e.target.value)}>
            <option value="Car">Car</option>
            <option value="Bike">Bike</option>
          </select>
        </div>
        <div className="col-md-8">
          <label className="form-label small fw-semibold" htmlFor="slot-location">Location</label>
          <input id="slot-location" className={`form-control ${errors.location ? 'is-invalid' : ''}`} value={form.location} onChange={(e) => setField('location', e.target.value)} placeholder="e.g. North Wing" />
          {errors.location && <div className="invalid-feedback">{errors.location}</div>}
        </div>
        {isEdit && (
          <div className="col-md-4">
            <label className="form-label small fw-semibold" htmlFor="slot-status">Status</label>
            <select id="slot-status" className="form-select" value={form.status} disabled={slot.status === 'Occupied' || slot.status === 'Inactive'} onChange={(e) => setField('status', e.target.value)}>
              <option value="Available">Available</option>
              <option value="Reserved">Reserved</option>
            </select>
            {slot.status === 'Occupied' && <div className="form-text">Occupied slots cannot change status.</div>}
            {slot.status === 'Inactive' && <div className="form-text">Inactive slots cannot change status.</div>}
          </div>
        )}
      </form>
    </ModalShell>
  );
}

export function EmployeeFormModal({ employee, onClose, onSaved }) {
  const isEdit = Boolean(employee);
  const [form, setForm] = useState({
    employee_id: employee?.employee_id || '',
    employee_name: employee?.employee_name || '',
    email: employee?.email || '',
    department: employee?.department || '',
    vehicle_type: employee?.vehicle_type || 'Car',
    vehicle_number: employee?.vehicle_number || '',
  });
  const [errors, setErrors] = useState({});
  const [serverError, setServerError] = useState(null);
  const [saving, setSaving] = useState(false);

  function setField(name, value) {
    setForm((current) => ({ ...current, [name]: value }));
  }

  function validate() {
    const next = {};
    if (!isEdit && !EMPLOYEE_ID_PATTERN.test(form.employee_id.trim())) next.employee_id = 'Use 3–20 letters, digits or hyphens.';
    if (form.employee_name.trim().length < 2) next.employee_name = 'Name must be at least 2 characters.';
    if (!EMAIL_PATTERN.test(form.email.trim())) next.email = 'Enter a valid email address.';
    if (form.department.trim().length < 2) next.department = 'Department is required.';
    if (form.vehicle_number.trim().length < 4) next.vehicle_number = 'Vehicle number must be at least 4 characters.';
    return next;
  }

  async function handleSave(event) {
    event.preventDefault();
    setServerError(null);
    const next = validate();
    setErrors(next);
    if (Object.keys(next).length) return;

    const common = {
      employee_name: form.employee_name.trim(),
      email: form.email.trim(),
      department: form.department.trim(),
      vehicle_type: form.vehicle_type,
      vehicle_number: form.vehicle_number.trim(),
    };

    setSaving(true);
    try {
      const response = isEdit
        ? await employeeApi.update(employee.employee_id, common)
        : await employeeApi.create({ ...common, employee_id: form.employee_id.trim() });
      onSaved(response.message);
    } catch (error) {
      setServerError(errorMessage(error));
    } finally {
      setSaving(false);
    }
  }

  return (
    <ModalShell
      title={isEdit ? `Edit ${employee.employee_id}` : 'Add employee'}
      onClose={onClose}
      footer={
        <>
          <button type="button" className="btn btn-outline-secondary" onClick={onClose} disabled={saving}>Cancel</button>
          <button type="submit" form="employee-form" className="btn btn-primary" disabled={saving}>
            {saving && <span className="spinner-border spinner-border-sm me-2" />}
            {isEdit ? 'Save changes' : 'Create employee'}
          </button>
        </>
      }
    >
      {serverError && <div className="alert alert-danger py-2 small">{serverError}</div>}
      <form id="employee-form" onSubmit={handleSave} noValidate className="row g-3">
        <div className="col-md-4">
          <label className="form-label small fw-semibold" htmlFor="emp-id">Employee ID</label>
          <input id="emp-id" className={`form-control ${errors.employee_id ? 'is-invalid' : ''}`} value={form.employee_id} disabled={isEdit} onChange={(e) => setField('employee_id', e.target.value.toUpperCase())} />
          {errors.employee_id && <div className="invalid-feedback">{errors.employee_id}</div>}
        </div>
        <div className="col-md-8">
          <label className="form-label small fw-semibold" htmlFor="emp-name">Full name</label>
          <input id="emp-name" className={`form-control ${errors.employee_name ? 'is-invalid' : ''}`} value={form.employee_name} onChange={(e) => setField('employee_name', e.target.value)} />
          {errors.employee_name && <div className="invalid-feedback">{errors.employee_name}</div>}
        </div>
        <div className="col-md-6">
          <label className="form-label small fw-semibold" htmlFor="emp-email">Email</label>
          <input id="emp-email" type="email" className={`form-control ${errors.email ? 'is-invalid' : ''}`} value={form.email} onChange={(e) => setField('email', e.target.value)} />
          {errors.email && <div className="invalid-feedback">{errors.email}</div>}
        </div>
        <div className="col-md-4">
          <label className="form-label small fw-semibold" htmlFor="emp-dept">Department</label>
          <input id="emp-dept" className={`form-control ${errors.department ? 'is-invalid' : ''}`} value={form.department} onChange={(e) => setField('department', e.target.value)} />
          {errors.department && <div className="invalid-feedback">{errors.department}</div>}
        </div>
        <div className="col-md-4">
          <label className="form-label small fw-semibold" htmlFor="emp-vehicle-type">Vehicle type</label>
          <select id="emp-vehicle-type" className="form-select" value={form.vehicle_type} onChange={(e) => setField('vehicle_type', e.target.value)}>
            <option value="Car">Car</option>
            <option value="Bike">Bike</option>
          </select>
        </div>
        <div className="col-md-4">
          <label className="form-label small fw-semibold" htmlFor="emp-vehicle-no">Registration no.</label>
          <input id="emp-vehicle-no" className={`form-control ${errors.vehicle_number ? 'is-invalid' : ''}`} value={form.vehicle_number} onChange={(e) => setField('vehicle_number', e.target.value.toUpperCase())} />
          {errors.vehicle_number && <div className="invalid-feedback">{errors.vehicle_number}</div>}
        </div>
      </form>
    </ModalShell>
  );
}
