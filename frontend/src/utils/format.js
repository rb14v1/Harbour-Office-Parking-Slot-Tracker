export const IST_TIME_ZONE = 'Asia/Kolkata';

export const SLOT_STATUS_META = {
  Available: { label: 'Available', badge: 'success', colorClass: 'slot-available', hex: '#198754' },
  Occupied: { label: 'Occupied', badge: 'danger', colorClass: 'slot-occupied', hex: '#dc3545' },
  Reserved: { label: 'Reserved', badge: 'warning', colorClass: 'slot-reserved', hex: '#ffc107' },
  Inactive: { label: 'Inactive', badge: 'secondary', colorClass: 'slot-inactive', hex: '#6c757d' },
};

/** Backend sends ISO strings with the +05:30 offset, so the browser shows IST without extra conversion. */
export function formatDateTime(isoString) {
  if (!isoString) return '—';
  return new Date(isoString).toLocaleString('en-IN', {
    timeZone: IST_TIME_ZONE,
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: true,
  });
}

export function formatTime(isoString) {
  if (!isoString) return '—';
  return new Date(isoString).toLocaleTimeString('en-IN', {
    timeZone: IST_TIME_ZONE,
    hour: '2-digit',
    minute: '2-digit',
    hour12: true,
  });
}

export function formatDuration(minutes) {
  if (minutes === null || minutes === undefined || Number.isNaN(Number(minutes))) return '—';
  const total = Math.round(Number(minutes));
  const hours = Math.floor(total / 60);
  const remainder = total % 60;
  if (hours === 0) return `${remainder} min`;
  return `${hours} h ${remainder} min`;
}

/** Returns today's date in IST as YYYY-MM-DD, the format date inputs and the API expect. */
export function todayIst() {
  return new Date().toLocaleDateString('en-CA', { timeZone: IST_TIME_ZONE });
}

export function errorMessage(error, fallback = 'Something went wrong. Please try again.') {
  return error?.message || fallback;
}
