import React, { useState, useEffect, useCallback } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom';
import { api, UserMe } from './lib/api';
import { announce } from './a11y/announcements';
import { SkipLink } from './components/SkipLink';
import { LiveRegion } from './components/LiveRegion';
import { Header } from './components/Header';
import { Register } from './pages/Register';
import { Login } from './pages/Login';
import { MfaVerify } from './pages/MfaVerify';
import { MfaEnrol } from './pages/MfaEnrol';
import { RecoveryCodes } from './pages/RecoveryCodes';
import { Recover } from './pages/Recover';
import { Dashboard } from './pages/Dashboard';

export const AppContent: React.FC = () => {
  const [user, setUser] = useState<UserMe | null>(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  const location = useLocation();

  const refreshUser = useCallback(async () => {
    try {
      const me = await api.auth.me();
      setUser(me);
      return me;
    } catch {
      setUser({ status: 'unauthenticated', mfa_enabled: false });
      return null;
    }
  }, []);

  useEffect(() => {
    const init = async () => {
      await refreshUser();
      setLoading(false);
    };
    init();
  }, [refreshUser]);

  // Session expiry / revocation handler: intercept 401s
  useEffect(() => {
    const originalFetch = window.fetch;
    window.fetch = async (...args) => {
      const response = await originalFetch(...args);
      if (response.status === 401 && !location.pathname.startsWith('/login') && !location.pathname.startsWith('/register')) {
        setUser({ status: 'unauthenticated', mfa_enabled: false });
        announce('Your session ended. Please sign in again.', 'assertive');
        navigate('/login');
      }
      return response;
    };
    return () => {
      window.fetch = originalFetch;
    };
  }, [navigate, location]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50" role="status">
        <p className="text-lg font-semibold text-slate-800">Loading Nexis accessible authentication...</p>
      </div>
    );
  }

  const isAuthenticated = user?.status === 'authenticated';
  const isMfaPending = user?.status === 'mfa_pending';

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 text-slate-900 font-sans">
      <SkipLink />
      <Header
        user={user}
        onLogout={() => setUser({ status: 'unauthenticated', mfa_enabled: false })}
      />

      <main id="main-content" className="flex-1 max-w-5xl w-full mx-auto px-4 py-8">
        <Routes>
          <Route
            path="/"
            element={
              isAuthenticated ? (
                <Navigate to="/dashboard" replace />
              ) : isMfaPending ? (
                <Navigate to="/mfa-verify" replace />
              ) : (
                <Navigate to="/login" replace />
              )
            }
          />

          <Route
            path="/register"
            element={
              isAuthenticated ? <Navigate to="/dashboard" replace /> : <Register />
            }
          />

          <Route
            path="/login"
            element={
              isAuthenticated ? (
                <Navigate to="/dashboard" replace />
              ) : isMfaPending ? (
                <Navigate to="/mfa-verify" replace />
              ) : (
                <Login onLoginSuccess={(u) => setUser(u)} />
              )
            }
          />

          <Route
            path="/mfa-verify"
            element={<MfaVerify onVerificationSuccess={(u) => setUser(u)} />}
          />

          <Route
            path="/mfa-enrol"
            element={
              !isAuthenticated ? (
                <Navigate to="/login" replace />
              ) : (
                <MfaEnrol onEnrolSuccess={() => refreshUser()} />
              )
            }
          />

          <Route
            path="/recovery-codes"
            element={
              !isAuthenticated ? (
                <Navigate to="/login" replace />
              ) : (
                <RecoveryCodes />
              )
            }
          />

          <Route path="/recover" element={<Recover />} />

          <Route
            path="/dashboard"
            element={
              !isAuthenticated ? (
                <Navigate to="/login" replace />
              ) : (
                <Dashboard
                  user={user}
                  onLogout={() => setUser({ status: 'unauthenticated', mfa_enabled: false })}
                />
              )
            }
          />

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>

      <footer className="bg-slate-900 border-t border-slate-800 text-slate-400 py-6 text-sm text-center">
        <div className="max-w-5xl mx-auto px-4">
          <p>
            Nexis Multi-Factor Authentication System for Visually Impaired Users.
          </p>
          <p className="mt-1 text-xs text-slate-500">
            Conforms to WCAG 2.1 AA, NIST SP 800-63B, OWASP Cheat Sheets, and RFC 6238.
          </p>
        </div>
      </footer>

      <LiveRegion />
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <AppContent />
    </BrowserRouter>
  );
};

export default App;
