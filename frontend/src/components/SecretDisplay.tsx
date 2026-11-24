import React, { useState } from 'react';
import { announce } from '../a11y/announcements';

interface SecretDisplayProps {
  secret: string;
  secretGrouped: string;
  qrCodeDataUri?: string;
}

/**
 * Accessible TOTP Secret Display (FR3, A14).
 * Emphasizes manual text entry first for visually impaired users.
 * QR code is treated as an optional secondary visual aid.
 */
export const SecretDisplay: React.FC<SecretDisplayProps> = ({
  secret,
  secretGrouped,
  qrCodeDataUri,
}) => {
  const [copySuccess, setCopySuccess] = useState(false);
  const [groupedView, setGroupedView] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(secret);
      setCopySuccess(true);
      announce('Secret key copied to clipboard.', 'polite');
      setTimeout(() => setCopySuccess(false), 3000);
    } catch {
      announce('Failed to copy automatically. Please select and copy the text key manually.', 'assertive');
    }
  };

  return (
    <section
      aria-labelledby="mfa-setup-secret-heading"
      className="p-5 bg-white border-2 border-slate-300 rounded-lg shadow-sm mb-6 text-left"
    >
      <h2
        id="mfa-setup-secret-heading"
        className="text-lg font-bold text-slate-900 mb-2"
      >
        Step 1: Add Account to Your Authenticator App
      </h2>

      <p className="text-sm text-slate-700 mb-4">
        Enter the secret key below manually into your authenticator app (such as Google Authenticator, Microsoft Authenticator, or 2FAS).
      </p>

      {/* Primary accessible text secret */}
      <div className="bg-slate-100 p-4 rounded-md border border-slate-300 mb-4">
        <label
          htmlFor="totp-secret-key"
          className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1"
        >
          Setup Secret Key (Text)
        </label>
        
        <div className="flex flex-wrap items-center gap-3">
          <code
            id="totp-secret-key"
            className="text-lg md:text-xl font-mono font-bold text-blue-900 bg-white px-3 py-2 rounded border border-slate-300 break-all select-all focus:outline-none focus:ring-2 focus:ring-blue-600"
            tabIndex={0}
            aria-label={`Authenticator setup secret: ${groupedView ? secretGrouped : secret}`}
          >
            {groupedView ? secretGrouped : secret}
          </code>

          <button
            type="button"
            onClick={handleCopy}
            className="px-4 py-2 bg-blue-700 hover:bg-blue-800 text-white font-medium rounded-md shadow-sm focus:outline-none focus:ring-4 focus:ring-blue-600 focus:ring-offset-1 text-sm flex items-center gap-1.5"
            aria-label="Copy secret key to clipboard"
          >
            {copySuccess ? 'Copied!' : 'Copy Secret'}
          </button>

          <button
            type="button"
            onClick={() => {
              const next = !groupedView;
              setGroupedView(next);
              announce(next ? 'Secret displayed in 4-character blocks.' : 'Secret displayed as continuous text.', 'polite');
            }}
            className="px-3 py-2 bg-slate-200 hover:bg-slate-300 text-slate-800 font-medium rounded-md border border-slate-400 text-sm focus:outline-none focus:ring-2 focus:ring-blue-600"
            aria-pressed={groupedView}
          >
            {groupedView ? 'Show Continuous' : 'Show in Groups of 4'}
          </button>
        </div>

        {copySuccess && (
          <p className="text-sm text-green-800 font-semibold mt-2" role="status">
            Secret key copied to clipboard.
          </p>
        )}
      </div>

      {/* Step by step manual setup instructions */}
      <div className="mb-5 bg-blue-50 border border-blue-200 p-4 rounded-md">
        <h3 className="text-sm font-bold text-blue-950 mb-2">
          Manual Entry Instructions for Common Authenticator Apps:
        </h3>
        <ol className="list-decimal list-inside text-sm text-blue-900 space-y-1.5">
          <li>Open your authenticator app on your phone or device.</li>
          <li>Choose <strong>Add account (+)</strong> and select <strong>Enter a setup key</strong> or <strong>Manual entry</strong>.</li>
          <li>Account Name: Enter <strong>Nexis</strong> (or your email).</li>
          <li>Your Key: Paste or type the secret key shown above.</li>
          <li>Type of key: Ensure <strong>Time-based</strong> (30 seconds) is selected.</li>
          <li>Save the account. The app will now generate a 6-digit code every 30 seconds.</li>
        </ol>
      </div>

      {/* Optional QR Code section */}
      {qrCodeDataUri && (
        <details className="mt-4 border-t border-slate-200 pt-3">
          <summary className="text-sm font-semibold text-slate-800 cursor-pointer hover:text-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-600 rounded px-1 py-1">
            Optional: View QR code for visual scanning
          </summary>
          <div className="mt-3 p-4 bg-slate-50 border border-slate-200 rounded text-center">
            <p className="text-sm text-slate-600 mb-3">
              Scanning this QR code is optional. The manual secret key above provides identical setup.
            </p>
            <div className="inline-block p-2 bg-white border border-slate-300 rounded shadow-sm">
              <img
                src={qrCodeDataUri}
                alt="Optional QR code for authenticator setup. The text secret above provides identical functionality."
                className="w-48 h-48 mx-auto"
              />
            </div>
          </div>
        </details>
      )}
    </section>
  );
};
