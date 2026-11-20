import { useState } from 'react';
import { bookingApi } from '../api/services.js';
import { useAuth } from '../context/AuthContext.jsx';
import { useToast } from '../context/ToastContext.jsx';
import { usePolling } from '../hooks/usePolling.js';
import BookingFormModal from './BookingFormModal.jsx';
import ConfirmDialog from './ConfirmDialog.jsx';
import { EmptyState, ErrorAlert, LoadingSpinner } from './common.jsx';
import { errorMessage, formatDuration, formatTime } from '../utils/format.js';
import { isoToIstInputs } from '../utils/istTime.js';

const STATE_BADGES = {
  upcoming: { label: 'Upcoming', className: 'bg-info text-dark' },
  in_progress: { label: 'In progress', className: 'bg-warning text-dark' },
};

/** The employee's own upcoming bookings, with New, Edit and Cancel. Shown on My Parking. */
export default function MyBookings() {
  const { identity } = useAuth();
  const toast = useToast();
  const [formBooking, setFormBooking] = useState(null); // null = closed, 'new', or a booking to edit
  const [cancelling, setCancelling] = useState(null);
  const [busy, setBusy] = useState(false);

  const bookings = usePolling(
    () => bookingApi.list({ scope: 'upcoming', page_size: 20 }).then((r) => r.data.items),
    [identity?.email],
  );
  const rows = bookings.data || [];

  function handleSaved(message) {
    toast.success(message);
    setFormBooking(null);
    bookings.refresh();
  }

  async function handleCancel() {
    setBusy(true);
    try {
      const response = await bookingApi.cancel(cancelling.id);
      toast.success(response.message);
    } catch (error) {
      toast.error(errorMessage(error));
    } finally {
      setBusy(false);
      setCancelling(null);
      bookings.refresh();
    }
  }

  return (
    <div className="card">
      <div className="card-body">
        <div className="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3">
          <div>
            <h3 className="section-title mb-0">My bookings</h3>
            <div className="small text-muted">Reserve a slot for a future time. You can change or cancel it until it starts.</div>
          </div>
          <button type="button" className="btn btn-primary btn-sm" onClick={() => setFormBooking('new')}>
            <i className="bi bi-calendar-plus me-1" />New booking
          </button>
        </div>

        <ErrorAlert error={bookings.error} onRetry={bookings.refresh} />
        {bookings.loading && !bookings.data ? (
          <LoadingSpinner label="Loading your bookings..." />
        ) : rows.length === 0 ? (
          <EmptyState icon="bi-calendar-x" title="No upcoming bookings" message="Use New booking to reserve a slot." />
        ) : (
          <div className="table-responsive">
            <table className="table table-hover align-middle small mb-0">
              <thead>
                <tr>
                  <th>Slot</th>
                  <th>Floor / location</th>
                  <th>Date</th>
                  <th>Time (IST)</th>
                  <th>Duration</th>
                  <th>Status</th>
                  <th className="text-end">Actions</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((booking) => {
                  const badge = STATE_BADGES[booking.state] || STATE_BADGES.upcoming;
                  return (
                    <tr key={booking.id}>
                      <td className="fw-semibold">{booking.slot_id}</td>
                      <td>Floor {booking.floor ?? '—'} · {booking.location ?? '—'}</td>
                      <td>{isoToIstInputs(booking.start_time).date}</td>
                      <td className="text-nowrap">{formatTime(booking.start_time)} – {formatTime(booking.end_time)}</td>
                      <td>{formatDuration(booking.duration_minutes)}</td>
                      <td><span className={`badge ${badge.className}`}>{badge.label}</span></td>
                      <td className="text-end text-nowrap">
                        {booking.editable && (
                          <button type="button" className="btn btn-sm btn-outline-primary me-1" onClick={() => setFormBooking(booking)}>
                            <i className="bi bi-pencil-square me-1" />Edit
                          </button>
                        )}
                        {booking.cancelable && (
                          <button type="button" className="btn btn-sm btn-outline-danger" onClick={() => setCancelling(booking)}>
                            <i className="bi bi-x-circle me-1" />Cancel
                          </button>
                        )}
                        {!booking.editable && <span className="text-muted small">In progress</span>}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {formBooking && (
        <BookingFormModal
          booking={formBooking === 'new' ? null : formBooking}
          vehicleType={identity?.vehicle_type}
          onClose={() => setFormBooking(null)}
          onSaved={handleSaved}
        />
      )}
      <ConfirmDialog
        show={Boolean(cancelling)}
        title="Cancel booking"
        message={cancelling ? `Cancel slot ${cancelling.slot_id} on ${isoToIstInputs(cancelling.start_time).date} at ${formatTime(cancelling.start_time)}?` : ''}
        confirmLabel="Cancel booking"
        variant="danger"
        busy={busy}
        onConfirm={handleCancel}
        onCancel={() => setCancelling(null)}
      />
    </div>
  );
}
