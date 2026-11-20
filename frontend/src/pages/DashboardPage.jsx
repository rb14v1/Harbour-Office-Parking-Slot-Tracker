import { Link } from 'react-router-dom';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { parkingApi, reportApi, slotApi } from '../api/services.js';
import { useAuth } from '../context/AuthContext.jsx';
import { usePolling } from '../hooks/usePolling.js';
import { EmptyState, ErrorAlert, LoadingSpinner, StatCard, StatusBadge, StatusLegend } from '../components/common.jsx';
import { SLOT_STATUS_META, formatDateTime, formatDuration } from '../utils/format.js';

export default function DashboardPage() {
  const { identity, isAdmin } = useAuth();
  const stats = usePolling(() => reportApi.dashboard().then((r) => r.data));
  const canSeeSlots = Boolean(identity || isAdmin);
  const slots = usePolling(
    () => (canSeeSlots ? slotApi.list().then((r) => r.data.slots) : Promise.resolve([])),
    [canSeeSlots, identity?.email],
  );
  const mine = usePolling(
    () => (identity ? parkingApi.myAllocation().then((r) => r.data) : Promise.resolve(null)),
    [identity?.email],
  );
  const trends = usePolling(
    () => (isAdmin ? reportApi.trends(7).then((r) => r.data.series) : Promise.resolve([])),
    [isAdmin],
  );

  if (stats.loading && !stats.data) return <LoadingSpinner label="Loading dashboard..." />;
  if (stats.error && !stats.data) return <ErrorAlert error={stats.error} onRetry={stats.refresh} />;

  const summary = stats.data.slots;
  const occupancy = summary.occupancy_percentage;

  return (
    <div>
      <div className="page-header">
        <div>
          <h2 className="page-title">Dashboard</h2>
          <p className="page-subtitle">Live parking availability across all floors. Refreshes every 5 seconds.</p>
        </div>
        <span className="live-pill"><span className="live-dot" /> Live</span>
      </div>

      <ErrorAlert error={stats.error} onRetry={stats.refresh} />

      {!identity && !isAdmin && (
        <div className="alert alert-info small d-flex justify-content-between align-items-center gap-2">
          <span><i className="bi bi-info-circle me-2" />Enter your name and email to see slot availability and your allocation.</span>
          <Link to="/my-parking" className="btn btn-sm btn-primary">Enter details</Link>
        </div>
      )}

      <div className="row g-3 mb-4">
        <div className="col-6 col-xl-3"><StatCard label="Total slots" value={summary.total_slots} icon="bi-p-square" tone="primary" hint={`${summary.inactive} inactive`} /></div>
        <div className="col-6 col-xl-3"><StatCard label="Available" value={summary.available} icon="bi-check-circle" tone="success" hint="Ready to occupy" /></div>
        <div className="col-6 col-xl-3"><StatCard label="Occupied" value={summary.occupied} icon="bi-car-front" tone="danger" hint={`${stats.data.active_sessions} active sessions`} /></div>
        <div className="col-6 col-xl-3"><StatCard label="Reserved" value={summary.reserved} icon="bi-bookmark-star" tone="warning" hint="Not open for booking" /></div>
      </div>

      <div className="row g-3 mb-4">
        <div className="col-lg-5">
          <div className="card h-100">
            <div className="card-body">
              <div className="d-flex justify-content-between align-items-center mb-2">
                <h3 className="section-title mb-0">Current occupancy</h3>
                <span className="fw-bold fs-5">{occupancy}%</span>
              </div>
              <div className="progress occupancy-progress mb-3" role="progressbar" aria-valuenow={occupancy} aria-valuemin="0" aria-valuemax="100">
                <div className="progress-bar" style={{ width: `${occupancy}%` }} />
              </div>
              <div className="row text-center g-2 small">
                <div className="col-6"><div className="text-muted">Entries today</div><div className="fw-bold fs-5">{stats.data.entries_today}</div></div>
                <div className="col-6"><div className="text-muted">Exits today</div><div className="fw-bold fs-5">{stats.data.exits_today}</div></div>
              </div>
              <hr />
              <div className="small">
                <div className="fw-semibold mb-1">Your allocation</div>
                {mine.data ? (
                  <div>
                    Slot <strong>{mine.data.slot?.slot_id}</strong> on floor {mine.data.slot?.floor}, parked since {formatDateTime(mine.data.allocation.entry_time)}.
                  </div>
                ) : (
                  <div className="text-muted">You have no active parking slot.</div>
                )}
                <div className="d-flex flex-wrap gap-2 mt-3">
                  <Link to="/slots" className="btn btn-sm btn-primary"><i className="bi bi-plus-circle me-1" />Find a slot</Link>
                  <Link to="/my-parking" className="btn btn-sm btn-outline-primary"><i className="bi bi-car-front me-1" />My parking</Link>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="col-lg-7">
          <div className="card h-100">
            <div className="card-body">
              <div className="d-flex justify-content-between align-items-center mb-3">
                <h3 className="section-title mb-0">Visual overview</h3>
                <StatusLegend />
              </div>
              {slots.loading && !slots.data ? (
                <LoadingSpinner label="Loading slots..." />
              ) : (
                <div className="mini-slot-grid">
                  {(slots.data || []).map((slot) => (
                    <Link
                      key={slot.slot_id}
                      to="/slots"
                      className={`mini-slot ${SLOT_STATUS_META[slot.status]?.colorClass || ''}`}
                      title={`${slot.slot_id} · ${slot.status}`}
                    >
                      {slot.slot_id}
                    </Link>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="row g-3">
        <div className={isAdmin ? 'col-lg-7' : 'col-12'}>
          <div className="card h-100">
            <div className="card-body">
              <h3 className="section-title">Recent parking activity</h3>
              {stats.data.recent_activity.length === 0 ? (
                <EmptyState icon="bi-clock-history" title="No parking activity yet" />
              ) : (
                <div className="table-responsive">
                  <table className="table table-hover align-middle mb-0 small">
                    <thead>
                      <tr>
                        <th>Slot</th>
                        {isAdmin && <th>Employee</th>}
                        <th>Entry</th>
                        <th>Exit</th>
                        <th>Duration</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {stats.data.recent_activity.map((row) => (
                        <tr key={row.id}>
                          <td className="fw-semibold">{row.slot_id}</td>
                          {isAdmin && <td>{row.employee_name} <span className="text-muted">({row.employee_id})</span></td>}
                          <td>{formatDateTime(row.entry_time)}</td>
                          <td>{formatDateTime(row.exit_time)}</td>
                          <td>{formatDuration(row.duration_minutes)}</td>
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
            </div>
          </div>
        </div>

        {isAdmin && (
          <div className="col-lg-5">
            <div className="card h-100">
              <div className="card-body">
                <h3 className="section-title">Entries, last 7 days</h3>
                {trends.data && trends.data.length ? (
                  <div style={{ width: '100%', height: 240 }}>
                    <ResponsiveContainer>
                      <BarChart data={trends.data} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} />
                        <XAxis dataKey="date" tickFormatter={(value) => value.slice(5)} tick={{ fontSize: 11 }} />
                        <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                        <Tooltip />
                        <Bar dataKey="entries" name="Entries" fill="#0d6efd" radius={[4, 4, 0, 0]} />
                        <Bar dataKey="exits" name="Exits" fill="#20c997" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                ) : (
                  <EmptyState icon="bi-bar-chart" title="No trend data yet" />
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
