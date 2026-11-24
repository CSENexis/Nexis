import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api, UserMe, NexisApiError } from '../lib/api';
import { setPageFocus } from '../lib/focus';
import { announce } from '../a11y/announcements';
import { ErrorSummary } from '../components/ErrorSummary';

interface DashboardProps {
  user: UserMe | null;
  onLogout: () => void;
}

export const Dashboard: React.FC<DashboardProps> = ({ user, onLogout }) => {
  const [regenerating, setRegenerating] = useState(false);
  const [newCodes, setNewCodes] = useState<string[]>([]);
  const [errors, setErrors] = useState<string[]>([]);
  const [copied, setCopied] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    setPageFocus('Account Dashboard');
  }, []);

  const handleRegenerateCodes = async () => {
    setErrors([]);
    setRegenerating(true);
    try {
      const res = await api.recovery.regenerate();
      setNewCodes(res.recovery_codes);
      announce('10 new recovery codes generated. Previous codes have been invalidated.', 'polite');
    } catch (err) {
      const apiErr = err as NexisApiError;
      setErrors([apiErr.message]);
      announce(`Failed to regenerate recovery codes: ${apiErr.message}`, 'assertive');
    } finally {
      setRegenerating(false);
    }
  };

  const handleCopyNewCodes = async () => {
    try {
      const textToCopy = newCodes.join('\n');
      await navigator.clipboard.writeText(textToCopy);
      setCopied(true);
      announce('New recovery codes copied to clipboard.', 'polite');
      setTimeout(() => setCopied(false), 3000);
    } catch {
      announce('Unable to copy codes automatically.', 'assertive');
    }
  };

  const handleLogout = async () => {
    try {
      await api.auth.logout();
      onLogout();
      announce('Signed out successfully.', 'polite');
      navigate('/login');
    } catch {
      onLogout();
      navigate('/login');
    }
  };

  return (
    <div className="max-w-3xl mx-auto my-10 p-6 bg-white border border-slate-300 rounded-xl shadow-md text-left">
      <h1 className="text-2xl font-bold text-slate-900 mb-2 focus:outline-none">
        Account Dashboard
      </h1>
      <p className="text-sm text-slate-600 mb-6">
        Proves authenticated access control and server-side session authorization (FR8, NFR8).
      </p>

      <ErrorSummary errors={errors} />

      <section
        aria-labelledby="account-details-heading"
        className="p-5 bg-slate-50 border border-slate-300 rounded-lg mb-6"
      >
        <h2 id="account-details-heading" className="text-lg font-bold text-slate-900 mb-4">
          Account Status
        </h2>

        <dl className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
          <div>
            <dt className="font-semibold text-slate-600">Email Address</dt>
            <dd className="text-base font-bold text-slate-900 mt-0.5">{user?.email || 'N/A'}</dd>
          </div>

          <div>
            <dt className="font-semibold text-slate-600">Two-Factor Authentication (TOTP)</dt>
            <dd className="mt-1">
              {user?.mfa_enabled ? (
                <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-bold bg-green-100 text-green-900 border border-green-300">
                  Active & Enabled
                </span>
              ) : (
                <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-bold bg-yellow-100 text-yellow-900 border border-yellow-300">
                  Not Configured
                </span>
              )}
            </dd>
          </div>
        </dl>
      </section>

      {!user?.mfa_enabled ? (
        <div className="p-5 bg-blue-50 border-2 border-blue-400 rounded-lg mb-6">
          <h2 className="text-base font-bold text-blue-950 mb-1">
            Complete Security Setup
          </h2>
          <p className="text-sm text-blue-900 mb-4">
            Protect your account by enrolling in multi-factor authentication using your preferred authenticator app.
          </p>
          <Link
            to="/mfa-enrol"
            className="inline-block px-5 py-2.5 bg-blue-700 hover:bg-blue-800 text-white font-semibold rounded-md shadow-sm focus:outline-none focus:ring-4 focus:ring-blue-600 text-sm"
          >
            Enrol in Multi-Factor Authentication
          </Link>
        </div>
      ) : (
        <section aria-labelledby="mfa-management-heading" className="p-5 bg-white border border-slate-300 rounded-lg mb-6">
          <h2 id="mfa-management-heading" className="text-base font-bold text-slate-900 mb-2">
            Recovery Codes Management
          </h2>
          <p className="text-sm text-slate-600 mb-4">
            If you suspect your backup codes were compromised or have run low on unused codes, you can regenerate a fresh batch of 10 codes.
          </p>

          <button
            type="button"
            onClick={handleRegenerateCodes}
            disabled={regenerating}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-900 text-white font-semibold rounded-md shadow-sm focus:outline-none focus:ring-4 focus:ring-blue-600 text-sm disabled:opacity-50"
          >
            {regenerating ? 'Regenerating...' : 'Regenerate 10 New Recovery Codes'}
          </button>

          {newCodes.length > 0 && (
            <div className="mt-5 p-4 bg-yellow-50 border-2 border-yellow-600 rounded-md">
              <h3 className="font-bold text-yellow-950 text-sm mb-2">
                New Recovery Codes (Save these now):
              </h3>
              <ol className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-sm font-mono font-bold text-slate-900 mb-4">
                {newCodes.map((code, idx) => (
                  <li key={idx} className="bg-white p-2 border border-yellow-300 rounded">
                    {idx + 1}. {code}
                  </li>
                ))}
              </ol>
              <button
                type="button"
                onClick={handleCopyNewCodes}
                className="px-4 py-2 bg-yellow-800 hover:bg-yellow-900 text-white font-semibold rounded text-sm focus:outline-none focus:ring-4 focus:ring-blue-600"
              >
                {copied ? 'Copied to Clipboard!' : 'Copy New Codes'}
              </button>
            </div>
          )}
        </section>
      )}

      <div className="pt-4 border-t border-slate-200 flex justify-end">
        <button
          type="button"
          onClick={handleLogout}
          className="px-5 py-2.5 bg-red-700 hover:bg-red-800 text-white font-semibold rounded-md shadow-sm focus:outline-none focus:ring-4 focus:ring-red-600 text-sm"
        >
          Sign Out of Nexis
        </button>
      </div>
    </div>
  );
};
