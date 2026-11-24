import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { setPageFocus } from '../lib/focus';
import { announce } from '../a11y/announcements';

interface LocationState {
  recoveryCodes?: string[];
}

export const RecoveryCodes: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const state = location.state as LocationState | undefined;
  const codes = state?.recoveryCodes || [];

  const [hasSaved, setHasSaved] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    setPageFocus('Save Your Recovery Codes');
    if (codes.length === 0) {
      announce('No active recovery codes to display. Redirecting to dashboard.', 'polite');
      navigate('/dashboard');
    }
  }, [codes, navigate]);

  const handleCopyAll = async () => {
    try {
      const textToCopy = [
        'NEXIS MFA RECOVERY CODES',
        'Store these codes in a secure location. Each code can be used only once to recover your account.',
        '',
        ...codes.map((code, idx) => `${idx + 1}. ${code}`),
      ].join('\n');

      await navigator.clipboard.writeText(textToCopy);
      setCopied(true);
      announce('All 10 recovery codes copied to clipboard.', 'polite');
      setTimeout(() => setCopied(false), 4000);
    } catch {
      announce('Unable to copy automatically. Please copy the codes manually.', 'assertive');
    }
  };

  const handleDownload = () => {
    const fileContent = [
      'NEXIS MFA RECOVERY CODES',
      'Store these codes in a secure location. Each code can be used only once to recover your account.',
      '',
      ...codes.map((code, idx) => `${idx + 1}. ${code}`),
    ].join('\n');

    const blob = new Blob([fileContent], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'nexis-recovery-codes.txt';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    announce('Recovery codes downloaded as nexis-recovery-codes.txt.', 'polite');
  };

  return (
    <div className="max-w-2xl mx-auto my-10 p-6 bg-white border border-slate-300 rounded-xl shadow-md text-left">
      <h1 className="text-2xl font-bold text-slate-900 mb-2 focus:outline-none">
        Save Your Recovery Codes
      </h1>

      <div
        role="alert"
        className="mb-6 p-4 bg-yellow-50 border-2 border-yellow-600 text-yellow-950 rounded-md text-sm font-medium"
      >
        <p className="font-bold text-base mb-1">Important: Save these codes now</p>
        <p>
          These 10 one-time recovery codes are your backup method if you lose access to your authenticator app.
          Each code can be used exactly once. <strong>This is the only time they will be shown.</strong>
        </p>
      </div>

      <section aria-label="Generated Recovery Codes" className="mb-6">
        <ol className="grid grid-cols-1 sm:grid-cols-2 gap-3 bg-slate-50 p-4 border border-slate-300 rounded-md">
          {codes.map((code, idx) => (
            <li
              key={idx}
              className="p-2.5 bg-white border border-slate-300 rounded text-center font-mono text-base font-bold text-slate-900 select-all"
            >
              <span className="sr-only">Recovery code {idx + 1}: </span>
              {code}
            </li>
          ))}
        </ol>
      </section>

      <div className="flex flex-wrap gap-4 mb-6">
        <button
          type="button"
          onClick={handleCopyAll}
          className="px-4 py-2.5 bg-blue-700 hover:bg-blue-800 text-white font-semibold rounded-md shadow-sm focus:outline-none focus:ring-4 focus:ring-blue-600 text-sm"
        >
          {copied ? 'All Codes Copied!' : 'Copy All Codes'}
        </button>

        <button
          type="button"
          onClick={handleDownload}
          className="px-4 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-800 font-semibold border border-slate-400 rounded-md shadow-sm focus:outline-none focus:ring-4 focus:ring-blue-600 text-sm"
        >
          Download as .txt File
        </button>
      </div>

      <div className="mb-8 pt-4 border-t border-slate-200">
        <div className="flex items-start gap-3">
          <input
            id="saved-codes-checkbox"
            type="checkbox"
            checked={hasSaved}
            onChange={(e) => setHasSaved(e.target.checked)}
            required
            className="w-5 h-5 mt-0.5 text-blue-600 border-2 border-slate-400 rounded focus:ring-2 focus:ring-blue-600 cursor-pointer"
          />
          <label
            htmlFor="saved-codes-checkbox"
            className="text-sm font-semibold text-slate-800 cursor-pointer select-none"
          >
            I have securely saved my 10 recovery codes in a safe place.
          </label>
        </div>
      </div>

      <button
        type="button"
        disabled={!hasSaved}
        onClick={() => {
          announce('MFA setup complete. Welcome to your account dashboard.', 'polite');
          navigate('/dashboard');
        }}
        className="w-full py-3 px-4 bg-green-700 hover:bg-green-800 text-white font-semibold rounded-md shadow-sm focus:outline-none focus:ring-4 focus:ring-green-600 focus:ring-offset-2 transition-colors disabled:opacity-40 disabled:cursor-not-allowed text-base"
      >
        Continue to Dashboard
      </button>
    </div>
  );
};
