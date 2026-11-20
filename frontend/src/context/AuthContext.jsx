import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { adminApi } from '../api/services.js';
import {
  ADMIN_SESSION_ENDED_EVENT,
  IDENTITY_CLEARED_EVENT,
  adminTokenStorage,
  identityStorage,
} from '../api/client.js';

const SessionContext = createContext(null);

/**
 * Two separate sessions:
 * - identity: the employee's name, email and vehicle, saved in this browser (no password).
 * - admin: a session created by the administrator password, kept as a token.
 */
export function AuthProvider({ children }) {
  const [identity, setIdentity] = useState(() => identityStorage.get());
  const [isAdmin, setIsAdmin] = useState(() => Boolean(adminTokenStorage.get()));

  useEffect(() => {
    const clearIdentity = () => setIdentity(null);
    const endAdmin = () => setIsAdmin(false);
    window.addEventListener(IDENTITY_CLEARED_EVENT, clearIdentity);
    window.addEventListener(ADMIN_SESSION_ENDED_EVENT, endAdmin);
    return () => {
      window.removeEventListener(IDENTITY_CLEARED_EVENT, clearIdentity);
      window.removeEventListener(ADMIN_SESSION_ENDED_EVENT, endAdmin);
    };
  }, []);

  const saveIdentity = useCallback((details) => {
    identityStorage.set(details);
    setIdentity(details);
  }, []);

  const clearIdentity = useCallback(() => {
    identityStorage.clear();
    setIdentity(null);
  }, []);

  const adminLogin = useCallback(async (password) => {
    const response = await adminApi.login(password);
    adminTokenStorage.set(response.data.access_token);
    setIsAdmin(true);
    return response.message;
  }, []);

  const adminLogout = useCallback(() => {
    adminTokenStorage.clear();
    setIsAdmin(false);
  }, []);

  const value = useMemo(
    () => ({ identity, isAdmin, saveIdentity, clearIdentity, adminLogin, adminLogout }),
    [identity, isAdmin, saveIdentity, clearIdentity, adminLogin, adminLogout],
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useAuth() {
  const context = useContext(SessionContext);
  if (!context) {
    throw new Error('useAuth must be used inside AuthProvider');
  }
  return context;
}
