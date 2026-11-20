import { SLOT_STATUS_META } from '../utils/format.js';

export function LoadingSpinner({ label = 'Loading...', fullPage = false }) {
  return (
    <div className={`loading-state ${fullPage ? 'full-page' : ''}`} role="status">
      <div className="spinner-border text-primary" />
      <div className="mt-2 text-muted small">{label}</div>
    </div>
  );
}

export function StatCard({ label, value, icon, tone = 'primary', hint }) {
  return (
    <div className="card stat-card h-100">
      <div className="card-body d-flex align-items-center gap-3">
        <div className={`stat-icon tone-${tone}`}>
          <i className={`bi ${icon}`} />
        </div>
        <div>
          <div className="stat-label">{label}</div>
          <div className="stat-value">{value}</div>
          {hint && <div className="stat-hint">{hint}</div>}
        </div>
      </div>
    </div>
  );
}

export function StatusBadge({ status }) {
  const meta = SLOT_STATUS_META[status] || { label: status, badge: 'secondary' };
  return <span className={`badge rounded-pill text-bg-${meta.badge}`}>{meta.label}</span>;
}

export function StatusLegend() {
  return (
    <div className="d-flex flex-wrap gap-3 small" aria-label="Status legend">
      {Object.entries(SLOT_STATUS_META).map(([status, meta]) => (
        <span key={status} className="d-inline-flex align-items-center gap-2">
          <span className="legend-dot" style={{ background: meta.hex }} />
          {meta.label}
        </span>
      ))}
    </div>
  );
}

export function EmptyState({ icon = 'bi-inbox', title, message }) {
  return (
    <div className="empty-state text-center py-5">
      <i className={`bi ${icon} display-6 text-muted`} />
      <div className="fw-semibold mt-2">{title}</div>
      {message && <div className="text-muted small">{message}</div>}
    </div>
  );
}

export function ErrorAlert({ error, onRetry }) {
  if (!error) return null;
  return (
    <div className="alert alert-danger d-flex justify-content-between align-items-center gap-2" role="alert">
      <span><i className="bi bi-exclamation-triangle-fill me-2" />{error.message || 'Something went wrong.'}</span>
      {onRetry && (
        <button type="button" className="btn btn-sm btn-outline-danger" onClick={onRetry}>Retry</button>
      )}
    </div>
  );
}

export function Pagination({ page, totalPages, onChange }) {
  if (totalPages <= 1) return null;
  return (
    <nav aria-label="Pagination" className="d-flex justify-content-end">
      <ul className="pagination pagination-sm mb-0">
        <li className={`page-item ${page <= 1 ? 'disabled' : ''}`}>
          <button type="button" className="page-link" onClick={() => onChange(page - 1)}>Previous</button>
        </li>
        <li className="page-item disabled"><span className="page-link">Page {page} of {totalPages}</span></li>
        <li className={`page-item ${page >= totalPages ? 'disabled' : ''}`}>
          <button type="button" className="page-link" onClick={() => onChange(page + 1)}>Next</button>
        </li>
      </ul>
    </nav>
  );
}
