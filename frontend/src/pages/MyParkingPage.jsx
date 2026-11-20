import { useState } from 'react';
import { parkingApi, slotApi } from '../api/services.js';
import { useAuth } from '../context/AuthContext.jsx';
import { useToast } from '../context/ToastContext.jsx';
import { usePolling } from '../hooks/usePolling.js';
import ConfirmDialog from '../components/ConfirmDialog.jsx';
import MyBookings from '../components/MyBookings.jsx';
import { EmptyState, ErrorAlert, LoadingSpinner, StatusBadge } from '../components/common.jsx';
import { errorMessage, formatDateTime, formatDuration } from '../utils/format.js';

export default function MyParkingPage() {
  const { identity: user } = useAuth();
  const toast = useToast();
  const [selectedSlotId, setSelectedSlotId] = useState(null);
  const [pendingAction, setPendingAction] = useState(null); // 'occupy' | 'release' | null
  const [busy, setBusy] = useState(false);

  const allocation = usePolling(() => parkingApi.myAllocation().then((r) => r.data));
  const available = usePolling(() => slotApi.available(user.vehicle_type).then((r) => r.data.slots));

  const current = allocation.data;
  const selectedSlot = (available.data || []).find((slot) => slot.slot_id === selectedSlotId) || null;

  async function runAction() {
    setBusy(true);
    try {
      if (pendingAction === 'occupy') {
        const response = await parkingApi.occupy(selectedSlot.slot_id);
        toast.success(response.message);
        setSelectedSlotId(null);
      } else {
        const response = await parkingApi.release();
        toast.success(response.message);
      }
    } catch (error) {
      toast.error(errorMessage(error));
    } finally {
      setBusy(false);
      setPendingAction(null);
      allocation.refresh();
      available.refresh();
    }
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h2 className="page-title">My Parking</h2>
          <p className="page-subtitle">Your allocation, your vehicle, and slots you can take now.</p>
        </div>
        <span className="live-pill"><span className="live-dot" /> Live</span>
      </div>

      <div className="row g-3">
        <div className="col-lg-4">
          <div className="card mb-3">
            <div className="card-body">
              <h3 className="section-title">Employee details</h3>
              <dl className="row small mb-0 detail-list">
                <dt className="col-5 text-muted">Employee ID</dt>
                <dd className="col-7 fw-semibold">{user.employee_id}</dd>
                <dt className="col-5 text-muted">Name</dt>
                <dd className="col-7">{user.employee_name}</dd>
                <dt className="col-5 text-muted">Department</dt>
                <dd className="col-7">{user.department}</dd>
                <dt className="col-5 text-muted">Vehicle type</dt>
                <dd className="col-7">{user.vehicle_type}</dd>
                <dt className="col-5 text-muted">Registration</dt>
                <dd className="col-7 font-monospace">{user.vehicle_number}</dd>
              </dl>
            </div>
          </div>

          <div className="card">
            <div className="card-body">
              <h3 className="section-title">Current allocation</h3>
              <ErrorAlert error={allocation.error} onRetry={allocation.refresh} />
              {allocation.loading && !allocation.data ? (
                <LoadingSpinner label="Checking your allocation..." />
              ) : current ? (
                <>
                  <div className="allocation-highlight mb-3">
                    <div className="small text-muted">Your slot</div>
                    <div className="display-6 fw-bold">{current.slot?.slot_id}</div>
                    <div className="small">Floor {current.slot?.floor} · {current.slot?.location}</div>
                  </div>
                  <dl className="row small mb-3 detail-list">
                    <dt className="col-6 text-muted">Entered</dt>
                    <dd className="col-6">{formatDateTime(current.allocation.entry_time)}</dd>
                    <dt className="col-6 text-muted">Time parked</dt>
                    <dd className="col-6">{formatDuration(current.elapsed_minutes)}</dd>
                    <dt className="col-6 text-muted">Status</dt>
                    <dd className="col-6">{current.slot && <StatusBadge status={current.slot.status} />}</dd>
                  </dl>
                  <button type="button" className="btn btn-danger w-100" onClick={() => setPendingAction('release')}>
                    <i className="bi bi-box-arrow-up-right me-2" />Release my slot
                  </button>
                </>
              ) : (
                <EmptyState icon="bi-car-front" title="No active slot" message="Pick an available slot to park." />
              )}
            </div>
          </div>
        </div>

        <div className="col-lg-8">
          <div className="card h-100">
            <div className="card-body">
              <div className="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3">
                <h3 className="section-title mb-0">Available {user.vehicle_type} slots</h3>
                <span className="small text-muted">{available.data?.length ?? 0} free</span>
              </div>
              {current && (
                <div className="alert alert-info small py-2">
                  You already have slot {current.slot?.slot_id}. Release it before selecting another.
                </div>
              )}
              <ErrorAlert error={available.error} onRetry={available.refresh} />
              {available.loading && !available.data ? (
                <LoadingSpinner label="Loading available slots..." />
              ) : (available.data || []).length === 0 ? (
                <EmptyState icon="bi-slash-circle" title="No free slots right now" message="This list refreshes every 5 seconds." />
              ) : (
                <div className="table-responsive mb-3">
                  <table className="table table-hover align-middle small mb-0">
                    <thead>
                      <tr>
                        <th style={{ width: 40 }} aria-label="Select" />
                        <th>Slot ID</th>
                        <th>Floor</th>
                        <th>Location</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {available.data.map((slot) => (
                        <tr
                          key={slot.slot_id}
                          className={`${selectedSlotId === slot.slot_id ? 'table-primary' : ''} ${current ? 'text-muted' : 'selectable-row'}`}
                          onClick={() => !current && setSelectedSlotId(slot.slot_id)}
                        >
                          <td>
                            <input
                              type="radio"
                              className="form-check-input"
                              name="available-slot"
                              aria-label={`Select slot ${slot.slot_id}`}
                              checked={selectedSlotId === slot.slot_id}
                              disabled={Boolean(current)}
                              onChange={() => setSelectedSlotId(slot.slot_id)}
                            />
                          </td>
                          <td className="fw-semibold">{slot.slot_id}</td>
                          <td>{slot.floor}</td>
                          <td>{slot.location}</td>
                          <td><StatusBadge status={slot.status} /></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              <div className="d-flex justify-content-end">
                <button
                  type="button"
                  className="btn btn-primary"
                  disabled={!selectedSlot || Boolean(current)}
                  onClick={() => setPendingAction('occupy')}
                >
                  <i className="bi bi-check2-circle me-2" />
                  {selectedSlot ? `Confirm allocation of ${selectedSlot.slot_id}` : 'Select a slot to continue'}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="mt-3">
        <MyBookings />
      </div>

      <ConfirmDialog
        show={pendingAction === 'occupy'}
        title="Confirm parking allocation"
        message={`Allocate slot ${selectedSlot?.slot_id} (floor ${selectedSlot?.floor}) to vehicle ${user.vehicle_number}?`}
        confirmLabel="Allocate slot"
        busy={busy}
        onConfirm={runAction}
        onCancel={() => setPendingAction(null)}
      />
      <ConfirmDialog
        show={pendingAction === 'release'}
        title="Release parking slot"
        message={`Release slot ${current?.slot?.slot_id}? Another employee will be able to use it immediately.`}
        confirmLabel="Release slot"
        variant="danger"
        busy={busy}
        onConfirm={runAction}
        onCancel={() => setPendingAction(null)}
      />
    </div>
  );
}
