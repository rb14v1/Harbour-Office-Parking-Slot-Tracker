import { createContext, useCallback, useContext, useMemo, useRef, useState } from 'react';

const ToastContext = createContext(null);
const TOAST_DURATION_MS = 4000;

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const nextId = useRef(1);

  const dismiss = useCallback((id) => {
    setToasts((current) => current.filter((toast) => toast.id !== id));
  }, []);

  const notify = useCallback(
    (message, type = 'success') => {
      const id = nextId.current++;
      setToasts((current) => [...current, { id, message, type }]);
      window.setTimeout(() => dismiss(id), TOAST_DURATION_MS);
    },
    [dismiss],
  );

  const value = useMemo(
    () => ({
      success: (message) => notify(message, 'success'),
      error: (message) => notify(message, 'danger'),
      info: (message) => notify(message, 'info'),
    }),
    [notify],
  );

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="toast-stack" aria-live="polite">
        {toasts.map((toast) => (
          <div key={toast.id} className={`toast-item alert alert-${toast.type} shadow-sm mb-2`} role="alert">
            <div className="d-flex align-items-start gap-2">
              <i className={`bi ${toast.type === 'success' ? 'bi-check-circle-fill' : toast.type === 'danger' ? 'bi-exclamation-octagon-fill' : 'bi-info-circle-fill'}`} />
              <span className="flex-grow-1">{toast.message}</span>
              <button type="button" className="btn-close btn-sm" aria-label="Dismiss" onClick={() => dismiss(toast.id)} />
            </div>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used inside ToastProvider');
  }
  return context;
}
