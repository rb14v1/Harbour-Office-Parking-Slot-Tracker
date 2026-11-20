import { useState } from 'react';
import { bookingApi, parkingApi } from '../api/services.js';
import { useAuth } from '../context/AuthContext.jsx';
import { usePolling } from '../hooks/usePolling.js';
import { EmptyState, ErrorAlert, LoadingSpinner, Pagination } from '../components/common.jsx';
import { formatDateTime, formatDuration, formatTime } from '../utils/format.js';
import { isoToIstInputs } from '../utils/istTime.js';

const PAGE_SIZE = 10;

const BOOKING_STATE_BADGES = {
  upcoming: { label: 'Upcoming', className: 'bg-info text-dark' },
  in_progress: { label: 'In progress', className: 'bg-warning text-dark' },
  past: { label: 'Completed', className: 'bg-secondary' },
  cancelled: { label: 'Cancelled', className: 'bg-danger' },
};

/** Everything about the signed-in employee: profile, parking sessions and bookings. */
export default function HistoryPage() {
  const { identity } = useAuth();
  const [sessionPage, setSessionPage] = useState(1);
  const [bookingPage, setBookingPage] = useState(1);

  const sessions = usePolling(
    () => parkingApi.history({ page: sessionPage, page_size: PAGE_SIZE, sort_by: 'entry_time', sort_order: 'desc' }).then((r) => r.data),
    [sessionPage, identity?.email],
  );
  const bookings = usePolling(
    () => bookingApi.list({ scope: 'all', page: bookingPage, page_size: PAGE_SIZE }).then((r) => r.data),
    [bookingPage, identity?.email],
  );

  return (
    <div>
      <div className="page-header">
        <div>
          <h2 className="page-title">My History</h2>
          <p className="page-subtitle">Your details, every parking session and every booking, newest first. Times are IST.</p>
        </div>
      </div>

      <div className="card mb-4">
        <div className="card-body">
          <h3 className="section-title">My details</h3>
          <dl className="row small mb-0 detail-list">
            <dt className="col-sm-3 col-lg-2 text-muted">Employee ID</dt>
            <dd className="col-sm-9 col-lg-4 fw-semibold">{identity.employee_id}</dd>
            <dt className="col-sm-3 col-lg-2 text-muted">Name</dt>
            <dd className="col-sm-9 col-lg-4">{identity.employee_name}</dd>
            <dt className="col-sm-3 col-lg-2 text-muted">Email</dt>
            <dd className="col-sm-9 col-lg-4">{identity.email}</dd>
            <dt className="col-sm-3 col-lg-2 text-muted">Department</dt>
            <dd className="col-sm-9 col-lg-4">{identity.department}</dd>
            <dt className="col-sm-3 col-lg-2 text-muted">Vehicle type</dt>
            <dd className="col-sm-9 col-lg-4">{identity.vehicle_type}</dd>
            <dt className="col-sm-3 col-lg-2 text-muted">Vehicle number</dt>
            <dd className="col-sm-9 col-lg-4 font-monospace">{identity.vehicle_number}</dd>
          </dl>
        </div>
      </div>

      <div className="card mb-4">
        <div className="card-body">
          <div className="d-flex justify-content-between align-items-center mb-3">
            <h3 className="section-title mb-0">Parking sessions</h3>
            {sessions.data && <span className="small text-muted">{sessions.data.total} session(s)</span>}
          </div>
          <ErrorAlert error={sessions.error} onRetry={sessions.refresh} />
          {sessions.loading && !sessions.data ? (
            <LoadingSpinner label="Loading parking sessions..." />
          ) : (sessions.data?.items || []).length === 0 ? (
            <EmptyState icon="bi-car-front" title="No parking sessions yet" message="Sessions appear here after you occupy a slot." />
          ) : (
            <div className="table-responsive">
              <table className="table table-hover align-middle small mb-0">
                <thead>
                  <tr>
                    <th>Slot</th>
                    <th>Vehicle number</th>
                    <th>Entry</th>
                    <th>Exit</th>
                    <th>Duration</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {sessions.data.items.map((row) => (
                    <tr key={row.id}>
                      <td className="fw-semibold">{row.slot_id}</td>
                      <td className="font-monospace">{row.vehicle_number}</td>
                      <td className="text-nowrap">{formatDateTime(row.entry_time)}</td>
                      <td className="text-nowrap">{row.exit_time ? formatDateTime(row.exit_time) : '—'}</td>
                      <td>{row.status === 'active' ? <span className="text-muted">In progress</span> : formatDuration(row.duration_minutes)}</td>
                      <td>
                        <span className={`badge ${row.status === 'active' ? 'bg-danger' : 'bg-success'}`}>
                          {row.status === 'active' ? 'Parked' : 'Completed'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {sessions.data && (
            <div className="d-flex justify-content-end mt-3">
              <Pagination page={sessions.data.page} totalPages={sessions.data.total_pages} onChange={setSessionPage} />
            </div>
          )}
        </div>
      </div>

      <div className="card">
        <div className="card-body">
          <div className="d-flex justify-content-between align-items-center mb-3">
            <h3 className="section-title mb-0">Bookings</h3>
            {bookings.data && <span className="small text-muted">{bookings.data.total} booking(s)</span>}
          </div>
          <ErrorAlert error={bookings.error} onRetry={bookings.refresh} />
          {bookings.loading && !bookings.data ? (
            <LoadingSpinner label="Loading bookings..." />
          ) : (bookings.data?.items || []).length === 0 ? (
            <EmptyState icon="bi-calendar-x" title="No bookings yet" message="Reserve a slot on My Parking." />
          ) : (
            <div className="table-responsive">
              <table className="table table-hover align-middle small mb-0">
                <thead>
                  <tr>
                    <th>Booking ID</th>
                    <th>Slot</th>
                    <th>Floor / location</th>
                    <th>Date</th>
                    <th>Start – end (IST)</th>
                    <th>Duration</th>
                    <th>Status</th>
                    <th>Booked on</th>
                    <th>Cancelled on</th>
                  </tr>
                </thead>
                <tbody>
                  {bookings.data.items.map((row) => {
                    const badge = BOOKING_STATE_BADGES[row.state];
                    return (
                      <tr key={row.id}>
                        <td className="font-monospace">{row.id.slice(-6).toUpperCase()}</td>
                        <td className="fw-semibold">{row.slot_id}</td>
                        <td>Floor {row.floor ?? '—'} · {row.location ?? '—'}</td>
                        <td>{isoToIstInputs(row.start_time).date}</td>
                        <td className="text-nowrap">{formatTime(row.start_time)} – {formatTime(row.end_time)}</td>
                        <td>{formatDuration(row.duration_minutes)}</td>
                        <td><span className={`badge ${badge.className}`}>{badge.label}</span></td>
                        <td className="text-nowrap">{formatDateTime(row.created_at)}</td>
                        <td className="text-nowrap">{row.cancelled_at ? formatDateTime(row.cancelled_at) : '—'}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
          {bookings.data && (
            <div className="d-flex justify-content-end mt-3">
              <Pagination page={bookings.data.page} totalPages={bookings.data.total_pages} onChange={setBookingPage} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
