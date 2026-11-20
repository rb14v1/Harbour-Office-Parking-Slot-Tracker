import { api } from './client.js';

// Every function resolves to the backend envelope: { success, message, data }.
const unwrap = (promise) => promise.then((response) => response.data);

export const adminApi = {
  login: (password) => unwrap(api.post('/auth/admin/login', { password })),
  me: () => unwrap(api.get('/auth/admin/me')),
};

export const identityApi = {
  save: (details) => unwrap(api.post('/identity', details)),
  me: () => unwrap(api.get('/identity/me')),
};

export const slotApi = {
  list: (filters = {}) => unwrap(api.get('/slots', { params: cleanParams(filters) })),
  available: (vehicleType) => unwrap(api.get('/slots/available', { params: cleanParams({ vehicle_type: vehicleType }) })),
  floors: () => unwrap(api.get('/slots/floors')),
  create: (payload) => unwrap(api.post('/slots', payload)),
  update: (slotId, payload) => unwrap(api.patch(`/slots/${slotId}`, payload)),
  deactivate: (slotId) => unwrap(api.post(`/slots/${slotId}/deactivate`)),
};

export const parkingApi = {
  occupy: (slotId) => unwrap(api.post('/parking/occupy', { slot_id: slotId })),
  release: (slotId) => unwrap(api.post('/parking/release', slotId ? { slot_id: slotId } : undefined)),
  myAllocation: () => unwrap(api.get('/parking/me')),
  occupancy: () => unwrap(api.get('/parking/occupancy')),
  history: (params) => unwrap(api.get('/parking/history', { params: cleanParams(params) })),
};

export const bookingApi = {
  list: (params) => unwrap(api.get('/bookings', { params: cleanParams(params) })),
  availableSlots: (startIso, endIso, vehicleType) =>
    unwrap(api.get('/bookings/available-slots', { params: { start_time: startIso, end_time: endIso, vehicle_type: vehicleType } })),
  create: (payload) => unwrap(api.post('/bookings', payload)),
  update: (bookingId, payload) => unwrap(api.patch(`/bookings/${bookingId}`, payload)),
  cancel: (bookingId) => unwrap(api.post(`/bookings/${bookingId}/cancel`)),
};

export const employeeApi = {
  list: (filters = {}) => unwrap(api.get('/employees', { params: cleanParams(filters) })),
  create: (payload) => unwrap(api.post('/employees', payload)),
  update: (employeeId, payload) => unwrap(api.patch(`/employees/${employeeId}`, payload)),
  setActive: (employeeId, active) =>
    unwrap(api.post(`/employees/${employeeId}/${active ? 'activate' : 'deactivate'}`)),
};

export const reportApi = {
  dashboard: () => unwrap(api.get('/dashboard/stats')),
  daily: (date) => unwrap(api.get('/reports/daily', { params: cleanParams({ date }) })),
  trends: (days) => unwrap(api.get('/reports/trends', { params: { days } })),
  peakHours: (days) => unwrap(api.get('/reports/peak-hours', { params: { days } })),
  mostUsedSlots: (days, limit = 5) => unwrap(api.get('/reports/most-used-slots', { params: { days, limit } })),
  summary: (days) => unwrap(api.get('/reports/summary', { params: { days } })),
  bookingSummary: (days) => unwrap(api.get('/reports/bookings/summary', { params: { days } })),
  bookingList: (params) => unwrap(api.get('/reports/bookings', { params: cleanParams(params) })),
};

/** Drops empty filter values so they are not sent as query strings. */
function cleanParams(params) {
  return Object.fromEntries(
    Object.entries(params || {}).filter(([, value]) => value !== '' && value !== null && value !== undefined),
  );
}
