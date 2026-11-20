import { useState } from 'react';
import { employeeApi, parkingApi, slotApi } from '../api/services.js';
import { useToast } from '../context/ToastContext.jsx';
import { usePolling } from '../hooks/usePolling.js';
import ConfirmDialog from '../components/ConfirmDialog.jsx';
import { EmptyState, ErrorAlert, LoadingSpinner, StatusBadge } from '../components/common.jsx';
import { EmployeeFormModal, SlotFormModal } from '../components/AdminModals.jsx';
import { errorMessage, formatDateTime, formatDuration } from '../utils/format.js';

const TABS = [
  { key: 'slots', label: 'Parking slots', icon: 'bi-p-square' },
  { key: 'employees', label: 'Employees', icon: 'bi-people' },
  { key: 'occupancy', label: 'Live occupancy', icon: 'bi-broadcast' },
];

export default function AdminPage() {
  const [tab, setTab] = useState('slots');

  return (
    <div>
      <div className="page-header">
        <div>
          <h2 className="page-title">Administration</h2>
          <p className="page-subtitle">Manage parking slots, employee accounts and live occupancy.</p>
        </div>
      </div>

      <ul className="nav nav-tabs mb-3" role="tablist">
        {TABS.map((item) => (
          <li className="nav-item" key={item.key} role="presentation">
            <button
              type="button"
              role="tab"
              aria-selected={tab === item.key}
              className={`nav-link ${tab === item.key ? 'active' : ''}`}
              onClick={() => setTab(item.key)}
            >
              <i className={`bi ${item.icon} me-2`} />{item.label}
            </button>
          </li>
        ))}
      </ul>

      {tab === 'slots' && <SlotManagement />}
      {tab === 'employees' && <EmployeeManagement />}
      {tab === 'occupancy' && <LiveOccupancy />}
    </div>
  );
}

function SlotManagement() {
  const toast = useToast();
  const [search, setSearch] = useState('');
  const [editing, setEditing] = useState(null); // slot object, or 'new'
  const [deactivating, setDeactivating] = useState(null);
  const [busy, setBusy] = useState(false);
  const slots = usePolling(() => slotApi.list({ search }).then((r) => r.data.slots), [search]);

  async function handleDeactivate() {
    setBusy(true);
    try {
      const response = await slotApi.deactivate(deactivating.slot_id);
      toast.success(response.message);
      setDeactivating(null);
    } catch (error) {
      toast.error(errorMessage(error));
      setDeactivating(null);
    } finally {
      setBusy(false);
      slots.refresh();
    }
  }

  function handleSaved(message) {
    toast.success(message);
    setEditing(null);
    slots.refresh();
  }

  return (
    <div className="card">
      <div className="card-body">
        <div className="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3">
          <div className="input-group input-group-sm" style={{ maxWidth: 300 }}>
            <span className="input-group-text"><i className="bi bi-search" /></span>
            <input className="form-control" placeholder="Search slot ID" value={search} onChange={(e) => setSearch(e.target.value)} aria-label="Search slot ID" />
          </div>
          <button type="button" className="btn btn-primary btn-sm" onClick={() => setEditing('new')}>
            <i className="bi bi-plus-lg me-1" />Add slot
          </button>
        </div>
        <ErrorAlert error={slots.error} onRetry={slots.refresh} />
        {slots.loading && !slots.data ? (
          <LoadingSpinner label="Loading slots..." />
        ) : (slots.data || []).length === 0 ? (
          <EmptyState icon="bi-p-square" title="No slots found" />
        ) : (
          <div className="table-responsive">
            <table className="table table-hover align-middle small mb-0">
              <thead>
                <tr>
                  <th>Slot ID</th><th>Floor</th><th>Location</th><th>Vehicle</th><th>Status</th><th>Occupied by</th><th className="text-end">Actions</th>
                </tr>
              </thead>
              <tbody>
                {slots.data.map((slot) => (
                  <tr key={slot.slot_id}>
                    <td className="fw-semibold">{slot.slot_id}</td>
                    <td>{slot.floor}</td>
                    <td>{slot.location}</td>
                    <td>{slot.vehicle_type}</td>
                    <td><StatusBadge status={slot.status} /></td>
                    <td>{slot.occupied_by || '—'}</td>
                    <td className="text-end text-nowrap">
                      <button type="button" className="btn btn-sm btn-outline-primary me-1" onClick={() => setEditing(slot)}>
                        <i className="bi bi-pencil-square me-1" />Edit
                      </button>
                      <button
                        type="button"
                        className="btn btn-sm btn-outline-danger"
                        disabled={slot.status === 'Occupied' || slot.status === 'Inactive'}
                        title={slot.status === 'Occupied' ? 'Occupied slots cannot be deactivated' : 'Deactivate slot'}
                        onClick={() => setDeactivating(slot)}
                      >
                        <i className="bi bi-slash-circle me-1" />Deactivate
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {editing && (
        <SlotFormModal slot={editing === 'new' ? null : editing} onClose={() => setEditing(null)} onSaved={handleSaved} />
      )}
      <ConfirmDialog
        show={Boolean(deactivating)}
        title="Deactivate parking slot"
        message={`Deactivate slot ${deactivating?.slot_id}? Employees will no longer be able to select it.`}
        confirmLabel="Deactivate"
        variant="danger"
        busy={busy}
        onConfirm={handleDeactivate}
        onCancel={() => setDeactivating(null)}
      />
    </div>
  );
}

function EmployeeManagement() {
  const toast = useToast();
  const [search, setSearch] = useState('');
  const [editing, setEditing] = useState(null);
  const [toggling, setToggling] = useState(null);
  const [busy, setBusy] = useState(false);
  const employees = usePolling(() => employeeApi.list({ search }).then((r) => r.data.employees), [search]);

  async function handleToggle() {
    setBusy(true);
    try {
      const response = await employeeApi.setActive(toggling.employee.employee_id, toggling.activate);
      toast.success(response.message);
    } catch (error) {
      toast.error(errorMessage(error));
    } finally {
      setBusy(false);
      setToggling(null);
      employees.refresh();
    }
  }

  function handleSaved(message) {
    toast.success(message);
    setEditing(null);
    employees.refresh();
  }

  return (
    <div className="card">
      <div className="card-body">
        <div className="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3">
          <div className="input-group input-group-sm" style={{ maxWidth: 320 }}>
            <span className="input-group-text"><i className="bi bi-search" /></span>
            <input className="form-control" placeholder="Search by ID, name or email" value={search} onChange={(e) => setSearch(e.target.value)} aria-label="Search employees" />
          </div>
          <button type="button" className="btn btn-primary btn-sm" onClick={() => setEditing('new')}>
            <i className="bi bi-person-plus me-1" />Add employee
          </button>
        </div>
        <ErrorAlert error={employees.error} onRetry={employees.refresh} />
        {employees.loading && !employees.data ? (
          <LoadingSpinner label="Loading employees..." />
        ) : (employees.data || []).length === 0 ? (
          <EmptyState icon="bi-people" title="No employees found" />
        ) : (
          <div className="table-responsive">
            <table className="table table-hover align-middle small mb-0">
              <thead>
                <tr>
                  <th>ID</th><th>Name</th><th>Email</th><th>Department</th><th>Role</th><th>Vehicle</th><th>Account</th><th className="text-end">Actions</th>
                </tr>
              </thead>
              <tbody>
                {employees.data.map((employee) => (
                  <tr key={employee.employee_id}>
                    <td className="fw-semibold">{employee.employee_id}</td>
                    <td>{employee.employee_name}</td>
                    <td>{employee.email}</td>
                    <td>{employee.department}</td>
                    <td><span className={`badge ${employee.role === 'admin' ? 'bg-primary' : 'bg-light text-dark border'}`}>{employee.role}</span></td>
                    <td>{employee.vehicle_type} · <span className="font-monospace">{employee.vehicle_number}</span></td>
                    <td>
                      <span className={`badge ${employee.is_active ? 'bg-success' : 'bg-secondary'}`}>
                        {employee.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td className="text-end text-nowrap">
                      <button type="button" className="btn btn-sm btn-outline-primary me-1" onClick={() => setEditing(employee)}>
                        <i className="bi bi-pencil-square me-1" />Edit
                      </button>
                      <button
                        type="button"
                        className={`btn btn-sm ${employee.is_active ? 'btn-outline-danger' : 'btn-outline-success'}`}
                        onClick={() => setToggling({ employee, activate: !employee.is_active })}
                      >
                        {employee.is_active ? 'Deactivate' : 'Activate'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {editing && (
        <EmployeeFormModal employee={editing === 'new' ? null : editing} onClose={() => setEditing(null)} onSaved={handleSaved} />
      )}
      <ConfirmDialog
        show={Boolean(toggling)}
        title={toggling?.activate ? 'Activate employee' : 'Deactivate employee'}
        message={toggling?.activate
          ? `Re-activate ${toggling?.employee.employee_name}? They will be able to log in again.`
          : `Deactivate ${toggling?.employee.employee_name}? They will be logged out and cannot log in until reactivated.`}
        confirmLabel={toggling?.activate ? 'Activate' : 'Deactivate'}
        variant={toggling?.activate ? 'success' : 'danger'}
        busy={busy}
        onConfirm={handleToggle}
        onCancel={() => setToggling(null)}
      />
    </div>
  );
}

function LiveOccupancy() {
  const occupancy = usePolling(() => parkingApi.occupancy().then((r) => r.data));

  return (
    <div className="card">
      <div className="card-body">
        <div className="d-flex justify-content-between align-items-center mb-3">
          <h3 className="section-title mb-0">Occupied slots <span className="text-muted fw-normal">({occupancy.data?.count ?? 0})</span></h3>
          <span className="live-pill"><span className="live-dot" /> Live</span>
        </div>
        <ErrorAlert error={occupancy.error} onRetry={occupancy.refresh} />
        {occupancy.loading && !occupancy.data ? (
          <LoadingSpinner label="Loading occupancy..." />
        ) : (occupancy.data?.occupied || []).length === 0 ? (
          <EmptyState icon="bi-check2-all" title="No slots are occupied" message="Every usable slot is free." />
        ) : (
          <div className="table-responsive">
            <table className="table table-hover align-middle small mb-0">
              <thead>
                <tr><th>Slot</th><th>Floor</th><th>Employee</th><th>Vehicle</th><th>Entered</th><th>Time parked</th></tr>
              </thead>
              <tbody>
                {occupancy.data.occupied.map((row) => (
                  <tr key={row.slot_id}>
                    <td className="fw-semibold">{row.slot_id}</td>
                    <td>{row.floor}</td>
                    <td>{row.employee_name || row.occupied_by}</td>
                    <td className="font-monospace">{row.vehicle_number || '—'}</td>
                    <td>{formatDateTime(row.entry_time)}</td>
                    <td>{formatDuration(row.elapsed_minutes)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
