import { useEffect, useState } from 'react';
import { parkingApi, slotApi } from '../api/services.js';
import { useAuth } from '../context/AuthContext.jsx';
import { useToast } from '../context/ToastContext.jsx';
import { usePolling } from '../hooks/usePolling.js';
import ConfirmDialog from '../components/ConfirmDialog.jsx';
import { EmptyState, ErrorAlert, LoadingSpinner, StatusBadge, StatusLegend } from '../components/common.jsx';
import { SLOT_STATUS_META, errorMessage } from '../utils/format.js';

const INITIAL_FILTERS = { floor: '', vehicle_type: '', status: '', search: '' };

export default function SlotsPage() {
  const { identity: user, isAdmin } = useAuth();
  const toast = useToast();
  const [filters, setFilters] = useState(INITIAL_FILTERS);
  const [floors, setFloors] = useState([]);
  const [selectedSlotId, setSelectedSlotId] = useState(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [busy, setBusy] = useState(false);

  const slots = usePolling(() => slotApi.list(filters).then((r) => r.data), [JSON.stringify(filters)]);
  const mine = usePolling(() => parkingApi.myAllocation().then((r) => r.data));

  useEffect(() => {
    slotApi.floors().then((r) => setFloors(r.data.floors)).catch(() => setFloors([]));
  }, []);

  const slotList = slots.data?.slots || [];
  const selected = slotList.find((slot) => slot.slot_id === selectedSlotId) || null;
  const alreadyParked = Boolean(mine.data);
  const canOccupy = Boolean(
    selected && selected.status === 'Available' && selected.vehicle_type === user?.vehicle_type && !alreadyParked,
  );

  function updateFilter(name, value) {
    setFilters((current) => ({ ...current, [name]: value }));
  }

  async function handleOccupy() {
    setBusy(true);
    try {
      const response = await parkingApi.occupy(selected.slot_id);
      toast.success(response.message);
      setConfirmOpen(false);
      setSelectedSlotId(null);
    } catch (error) {
      toast.error(errorMessage(error));
      setConfirmOpen(false);
    } finally {
      setBusy(false);
      slots.refresh();
      mine.refresh();
    }
  }

  function describeBlock() {
    if (!selected) return null;
    if (alreadyParked) return 'You already hold a parking slot. Release it on My Parking before taking another.';
    if (selected.status !== 'Available') return `This slot is ${selected.status.toLowerCase()} and cannot be selected.`;
    if (selected.vehicle_type !== user?.vehicle_type) {
      return `This slot is for ${selected.vehicle_type} parking. Your registered vehicle is a ${user?.vehicle_type}.`;
    }
    return null;
  }

  const blockReason = describeBlock();

  return (
    <div>
      <div className="page-header">
        <div>
          <h2 className="page-title">Parking Slots</h2>
          <p className="page-subtitle">Select an available slot to view its details and occupy it.</p>
        </div>
        <span className="live-pill"><span className="live-dot" /> Live</span>
      </div>

      <div className="card mb-3">
        <div className="card-body">
          <div className="row g-2 align-items-end">
            <div className="col-6 col-md-3 col-lg-2">
              <label className="form-label small fw-semibold" htmlFor="filter-floor">Floor</label>
              <select id="filter-floor" className="form-select form-select-sm" value={filters.floor} onChange={(e) => updateFilter('floor', e.target.value)}>
                <option value="">All floors</option>
                {floors.map((floor) => <option key={floor} value={floor}>Floor {floor}</option>)}
              </select>
            </div>
            <div className="col-6 col-md-3 col-lg-2">
              <label className="form-label small fw-semibold" htmlFor="filter-type">Vehicle type</label>
              <select id="filter-type" className="form-select form-select-sm" value={filters.vehicle_type} onChange={(e) => updateFilter('vehicle_type', e.target.value)}>
                <option value="">All types</option>
                <option value="Car">Car</option>
                <option value="Bike">Bike</option>
              </select>
            </div>
            <div className="col-6 col-md-3 col-lg-2">
              <label className="form-label small fw-semibold" htmlFor="filter-status">Status</label>
              <select id="filter-status" className="form-select form-select-sm" value={filters.status} onChange={(e) => updateFilter('status', e.target.value)}>
                <option value="">All statuses</option>
                {Object.keys(SLOT_STATUS_META).map((status) => <option key={status} value={status}>{status}</option>)}
              </select>
            </div>
            <div className="col-6 col-md-3 col-lg-3">
              <label className="form-label small fw-semibold" htmlFor="filter-search">Search slot ID</label>
              <div className="input-group input-group-sm">
                <span className="input-group-text"><i className="bi bi-search" /></span>
                <input id="filter-search" className="form-control" placeholder="e.g. G-C01" value={filters.search} onChange={(e) => updateFilter('search', e.target.value)} />
              </div>
            </div>
            <div className="col-12 col-lg-3 d-flex justify-content-lg-end align-items-center">
              <button type="button" className="btn btn-sm btn-outline-secondary" onClick={() => setFilters(INITIAL_FILTERS)}>
                <i className="bi bi-arrow-counterclockwise me-1" />Clear filters
              </button>
            </div>
          </div>
        </div>
      </div>

      <ErrorAlert error={slots.error} onRetry={slots.refresh} />

      <div className="row g-3">
        <div className="col-lg-8">
          <div className="card h-100">
            <div className="card-body">
              <div className="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3">
                <h3 className="section-title mb-0">
                  Slots <span className="text-muted fw-normal">({slots.data?.count ?? 0})</span>
                </h3>
                <StatusLegend />
              </div>
              {slots.loading && !slots.data ? (
                <LoadingSpinner label="Loading parking slots..." />
              ) : slotList.length === 0 ? (
                <EmptyState icon="bi-search" title="No slots match these filters" message="Try clearing a filter." />
              ) : (
                <div className="slot-grid">
                  {slotList.map((slot) => {
                    const isSelectable = slot.status === 'Available';
                    const isSelected = slot.slot_id === selectedSlotId;
                    const meta = SLOT_STATUS_META[slot.status];
                    return (
                      <button
                        key={slot.slot_id}
                        type="button"
                        className={`slot-card ${meta.colorClass} ${isSelected ? 'selected' : ''} ${!isSelectable ? 'not-selectable' : ''}`}
                        onClick={() => setSelectedSlotId(slot.slot_id)}
                        disabled={!isSelectable}
                        aria-pressed={isSelected}
                        aria-label={`Slot ${slot.slot_id}, ${slot.status}`}
                      >
                        <div className="slot-card-id">{slot.slot_id}</div>
                        <div className="slot-card-meta">
                          <i className={`bi ${slot.vehicle_type === 'Car' ? 'bi-car-front-fill' : 'bi-bicycle'}`} />
                          {' '}{slot.vehicle_type} · F{slot.floor}
                        </div>
                        <div className="slot-card-status">{meta.label}</div>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="col-lg-4">
          <div className="card h-100">
            <div className="card-body">
              <h3 className="section-title">Slot details</h3>
              {!selected ? (
                <EmptyState icon="bi-hand-index-thumb" title="No slot selected" message="Click a slot in the grid to see its details." />
              ) : (
                <>
                  <dl className="row small mb-3 detail-list">
                    <dt className="col-5 text-muted">Slot ID</dt>
                    <dd className="col-7 fw-bold">{selected.slot_id}</dd>
                    <dt className="col-5 text-muted">Floor</dt>
                    <dd className="col-7">{selected.floor}</dd>
                    <dt className="col-5 text-muted">Location</dt>
                    <dd className="col-7">{selected.location}</dd>
                    <dt className="col-5 text-muted">Vehicle type</dt>
                    <dd className="col-7">{selected.vehicle_type}</dd>
                    <dt className="col-5 text-muted">Status</dt>
                    <dd className="col-7"><StatusBadge status={selected.status} /></dd>
                    {isAdmin && selected.occupied_by && (
                      <>
                        <dt className="col-5 text-muted">Occupied by</dt>
                        <dd className="col-7">{selected.occupied_by}</dd>
                      </>
                    )}
                  </dl>
                  {blockReason && <div className="alert alert-warning small py-2">{blockReason}</div>}
                  <button
                    type="button"
                    className="btn btn-primary w-100"
                    disabled={!canOccupy}
                    onClick={() => setConfirmOpen(true)}
                  >
                    <i className="bi bi-p-square me-2" />Occupy this slot
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      </div>

      <ConfirmDialog
        show={confirmOpen}
        title="Confirm parking allocation"
        message={selected ? `Occupy slot ${selected.slot_id} (floor ${selected.floor}, ${selected.location}) for ${user?.vehicle_number}?` : ''}
        confirmLabel="Occupy slot"
        busy={busy}
        onConfirm={handleOccupy}
        onCancel={() => setConfirmOpen(false)}
      />
    </div>
  );
}
