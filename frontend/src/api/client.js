import axios from 'axios';

const IDENTITY_KEY = 'parking_identity';
const ADMIN_TOKEN_KEY = 'parking_admin_token';

export const IDENTITY_CLEARED_EVENT = 'parking:identity-cleared';
export const ADMIN_SESSION_ENDED_EVENT = 'parking:admin-session-ended';

/** Small wrapper so a blocked or private browser window cannot crash the app. */
function createStorage(key) {
  return {
    get() {
      try {
        return window.localStorage.getItem(key);
      } catch {
        return null;
      }
    },
    set(value) {
      try {
        window.localStorage.setItem(key, value);
      } catch {
        // Storage blocked: the value lasts for this page only.
      }
    },
    clear() {
      try {
        window.localStorage.removeItem(key);
      } catch {
        // Nothing to clear.
      }
    },
  };
}

export const adminTokenStorage = createStorage(ADMIN_TOKEN_KEY);

/** Employee details saved in this browser. Name, email, vehicle type and vehicle number. */
export const identityStorage = {
  get() {
    const raw = createStorage(IDENTITY_KEY).get();
    try {
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  },
  set(details) {
    createStorage(IDENTITY_KEY).set(JSON.stringify(details));
  },
  clear() {
    createStorage(IDENTITY_KEY).clear();
  },
};

/** Converts any Axios failure into one shape the UI can display. */
export function normaliseError(error) {
  if (!error?.response) {
    return {
      status: 0,
      code: 'NETWORK_ERROR',
      message: 'Cannot reach the parking server. Check that the backend is running.',
      details: null,
    };
  }
  const body = error.response.data || {};
  return {
    status: error.response.status,
    code: body.error?.code || 'HTTP_ERROR',
    message: body.message || 'The request failed. Please try again.',
    details: body.error?.details ?? null,
  };
}

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((config) => {
  const adminToken = adminTokenStorage.get();
  if (adminToken) {
    config.headers.Authorization = `Bearer ${adminToken}`;
  }
  const identity = identityStorage.get();
  if (identity?.email) {
    config.headers['X-Employee-Email'] = identity.email;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const code = error.response?.data?.error?.code;
    if (code === 'IDENTITY_REQUIRED') {
      identityStorage.clear();
      window.dispatchEvent(new CustomEvent(IDENTITY_CLEARED_EVENT));
    }
    if (code === 'INVALID_TOKEN' || code === 'SESSION_EXPIRED') {
      adminTokenStorage.clear();
      window.dispatchEvent(new CustomEvent(ADMIN_SESSION_ENDED_EVENT));
    }
    return Promise.reject(normaliseError(error));
  },
);
