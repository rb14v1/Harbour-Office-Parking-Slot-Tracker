import { useState } from 'react';
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { reportApi } from '../api/services.js';
import { usePolling } from '../hooks/usePolling.js';
import { EmptyState, ErrorAlert, LoadingSpinner, Pagination, StatCard } from '../components/common.jsx';
import { formatDateTime, formatDuration, formatTime, todayIst } from '../utils/format.js';
import { isoToIstInputs } from '../utils/istTime.js';

const RANGE_OPTIONS = [7, 30];
const STATE_OPTIONS = [
  { value: 'all', label: 'All bookings' },
  { value: 'upcoming', label: 'Upcoming' },
  { value: 'in_progress', label: 'In progress' },
  { value: 'past', label: 'Completed' },
  { value: 'cancelled', label: 'Cancelled' },
];
const EMPTY_FILTERS = { date_from: '', date_to: '', employee_id: '', slot_id: '', state: 'all' };
const PAGE_SIZE = 15;

export default function ReportsPage() {
  const [rangeDays, setRangeDays] = useState(7);
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [page, setPage] = useState(1);

  const summary = usePolling(() => reportApi.bookingSummary(rangeDays).then((r) => r.data), [rangeDays], 15000);
  const list = usePolling(
    () => reportApi.bookingList({ ...filters, page, page_size: PAGE_SIZE }).then((r) => r.data),
    [JSON.stringify(filters), page],
    15000,
  );

  function updateFilter(name, value) {
    setFilters((current) => ({ ...current, [name]: value }));
    setPage(1);
  }

  const counts = summary.data?.counts;
  const rows = list.data?.items || [];
  const dateRangeInvalid = filters.date_from && filters.date_to && filters.date_to < filters.date_from;

  return (
    <div>
      <div className="page-header">
        <div>
          <h2 className="page-title">Reports</h2>
          <p className="page-subtitle">Every booking in the office, with counts. Times are IST.</p>
        </div>
        <div className="btn-group btn-group-sm" role="group" aria-label="Summary range">
          {RANGE_OPTIONS.map((days) => (
            <button key={days} type="button" className={`btn ${rangeDays === days ? 'btn-primary' : 'btn-outline-primary'}`} onClick={() => setRangeDays(days)}>
              Last {days} days
            </button>
          ))}
        </div>
      </div>

      <ErrorAlert error={summary.error} onRetry={summary.refresh} />

      {summary.loading && !summary.data ? (
        <LoadingSpinner label="Loading booking summary..." />
      ) : summary.data && (
        <>
          <div className="row g-3 mb-4">
            <div className="col-6 col-xl"><StatCard label="Total bookings" value={summary.data.total} icon="bi-calendar2-check" tone="primary" hint={`Last ${rangeDays} days + next 14`} /></div>
            <div className="col-6 col-xl"><StatCard label="Upcoming" value={counts.upcoming} icon="bi-calendar-event" tone="info" hint="Not started yet" /></div>
            <div className="col-6 col-xl"><StatCard label="In progress" value={counts.in_progress} icon="bi-hourglass-split" tone="warning" hint="Running now" /></div>
            <div className="col-6 col-xl"><StatCard label="Completed" value={counts.past} icon="bi-check2-circle" tone="success" hint="Finished" /></div>
            <div className="col-6 col-xl"><StatCard label="Cancelled" value={counts.cancelled} icon="bi-x-circle" tone="danger" hint={`${summary.data.by_vehicle_type.Car} car · ${summary.data.by_vehicle_type.Bike} bike`} /></div>
          </div>

          <div className="row g-3 mb-4">
            <div className="col-lg-8">
              <div className="card h-100">
                <div className="card-body">
                  <h3 className="section-title">Bookings per day</h3>
                  <div style={{ width: '100%', height: 260 }}>
                    <ResponsiveContainer>
                      <BarChart data={summary.data.series} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} />
                        <XAxis dataKey="date" tickFormatter={(value) => value.slice(5)} tick={{ fontSize: 10 }} interval={2} />
                        <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                        <Tooltip />
                        <Legend />
                        <Bar dataKey="bookings" name="Bookings" fill="#0d6efd" radius={[4, 4, 0, 0]} />
                        <Bar dataKey="cancelled" name="Cancelled" fill="#dc3545" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </div>
            </div>
            <div className="col-lg-4">
              <div className="card h-100">
                <div className="card-body">
                  <h3 className="section-title">Most booked slots</h3>
                  {summary.data.top_slots.length === 0 ? (
                    <EmptyState icon="bi-p-square" title="No bookings in this range" />
                  ) : (
                    <table className="table table-sm small mb-0">
                      <thead><tr><th>Slot</th><th className="text-end">Bookings</th></tr></thead>
                      <tbody>
                        {summary.data.top_slots.map((slot) => (
                          <tr key={slot.slot_id}>
                            <td className="fw-semibold">{slot.slot_id}</td>
                            <td className="text-end">{slot.bookings}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              </div>
            </div>
          </div>
        </>
      )}

      <div className="card">
        <div className="card-body">
          <h3 className="section-title">All bookings</h3>
          <div className="row g-2 align-items-end mb-3">
            <div className="col-6 col-md-2">
              <label className="form-label small fw-semibold" htmlFor="report-from">From</label>
              <input id="report-from" type="date" className="form-control form-control-sm" value={filters.date_from} onChange={(e) => updateFilter('date_from', e.target.value)} />
            </div>
            <div className="col-6 col-md-2">
              <label className="form-label small fw-semibold" htmlFor="report-to">To</label>
              <input id="report-to" type="date" className="form-control form-control-sm" value={filters.date_to} onChange={(e) => updateFilter('date_to', e.target.value)} />
            </div>
            <div className="col-6 col-md-2">
              <label className="form-label small fw-semibold" htmlFor="report-employee">Employee ID</label>
              <input id="report-employee" className="form-control form-control-sm" placeholder="EMP001" value={filters.employee_id} onChange={(e) => updateFilter('employee_id', e.target.value)} />
            </div>
            <div className="col-6 col-md-2">
              <label className="form-label small fw-semibold" htmlFor="report-slot">Slot ID</label>
              <input id="report-slot" className="form-control form-control-sm" placeholder="G-C01" value={filters.slot_id} onChange={(e) => updateFilter('slot_id', e.target.value)} />
            </div>
            <div className="col-12 col-md-3">
              <label className="form-label small fw-semibold" htmlFor="report-state">Status</label>
              <select id="report-state" className="form-select form-select-sm" value={filters.state} onChange={(e) => updateFilter('state', e.target.value)}>
                {STATE_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
              </select>
            </div>
            <div className="col-12 col-md-1 text-md-end">
              <button type="button" className="btn btn-sm btn-outline-secondary" onClick={() => { setFilters(EMPTY_FILTERS); setPage(1); }}>Clear</button>
            </div>
          </div>
          {dateRangeInvalid && <div className="text-danger small mb-2">The To date must be on or after the From date.</div>}

          <ErrorAlert error={list.error} onRetry={list.refresh} />
          {list.loading && !list.data ? (
            <LoadingSpinner label="Loading bookings..." />
          ) : rows.length === 0 ? (
            <EmptyState icon="bi-search" title="No bookings match these filters" />
          ) : (
            <div className="table-responsive">
              <table className="table table-hover align-middle small mb-0 bookings-table">
                <thead>
                  <tr>
                    <th>Booking ID</th>
                    <th>Employee</th>
                    <th>Email</th>
                    <th>Vehicle</th>
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
                  {rows.map((row) => (
                    <tr key={row.id}>
                      <td className="font-monospace">{row.id.slice(-6).toUpperCase()}</td>
                      <td>
                        <div className="fw-semibold">{row.employee_name}</div>
                        <div className="text-muted">{row.employee_id}</div>
                      </td>
                      <td>{row.employee_email || '—'}</td>
                      <td>
                        <div>{row.vehicle_type}</div>
                        <div className="font-monospace text-muted">{row.vehicle_number}</div>
                      </td>
                      <td className="fw-semibold">{row.slot_id}</td>
                      <td>Floor {row.floor ?? '—'} · {row.location ?? '—'}</td>
                      <td>{isoToIstInputs(row.start_time).date}</td>
                      <td className="text-nowrap">{formatTime(row.start_time)} – {formatTime(row.end_time)}</td>
                      <td>{formatDuration(row.duration_minutes)}</td>
                      <td>{row.state.replace('_', ' ')}</td>
                      <td className="text-nowrap">{formatDateTime(row.created_at)}</td>
                      <td className="text-nowrap">{row.cancelled_at ? formatDateTime(row.cancelled_at) : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {list.data && (
            <div className="d-flex justify-content-between align-items-center mt-3">
              <span className="small text-muted">{list.data.total} booking(s) · today is {todayIst()}</span>
              <Pagination page={list.data.page} totalPages={list.data.total_pages} onChange={setPage} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
