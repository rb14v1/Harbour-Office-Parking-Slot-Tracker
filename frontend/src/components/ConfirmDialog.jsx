export default function ConfirmDialog({
  show,
  title,
  message,
  confirmLabel = 'Confirm',
  variant = 'primary',
  busy = false,
  onConfirm,
  onCancel,
}) {
  if (!show) return null;
  return (
    <>
      <div className="modal d-block" tabIndex="-1" role="dialog" aria-modal="true" aria-labelledby="confirm-title">
        <div className="modal-dialog modal-dialog-centered">
          <div className="modal-content">
            <div className="modal-header">
              <h5 className="modal-title" id="confirm-title">{title}</h5>
              <button type="button" className="btn-close" aria-label="Close" onClick={onCancel} disabled={busy} />
            </div>
            <div className="modal-body">{message}</div>
            <div className="modal-footer">
              <button type="button" className="btn btn-outline-secondary" onClick={onCancel} disabled={busy}>
                Cancel
              </button>
              <button type="button" className={`btn btn-${variant}`} onClick={onConfirm} disabled={busy}>
                {busy && <span className="spinner-border spinner-border-sm me-2" />}
                {confirmLabel}
              </button>
            </div>
          </div>
        </div>
      </div>
      <div className="modal-backdrop show" />
    </>
  );
}
