import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api, NexisApiError } from '../lib/api';
import { setPageFocus, focusFirstError } from '../lib/focus';
import { announce } from '../a11y/announcements';
import { SecretDisplay } from '../components/SecretDisplay';
import { CodeInput } from '../components/CodeInput';
import { ErrorSummary } from '../components/ErrorSummary';

interface MfaEnrolProps {
  onEnrolSuccess: (recoveryCodes: string[]) => void;
}

export const MfaEnrol: React.FC<MfaEnrolProps> = ({ onEnrolSuccess }) => {
  const [secret, setSecret] = useState<string>('');
  const [secretGrouped, setSecretGrouped] = useState<string>('');
  const [qrCodeUri, setQrCodeUri] = useState<string | undefined>(undefined);
  const [code, setCode] = useState<string>('');
  const [errors, setErrors] = useState<string[]>([]);
  const [codeError, setCodeError] = useState<string | undefined>(undefined);
  const [initialLoading, setInitialLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    setPageFocus('Set Up Multi-Factor Authentication');
    const initEnrolment = async () => {
      try {
        const res = await api.mfa.startEnrol();
        setSecret(res.secret);
        setSecretGrouped(res.secret_grouped);
        setQrCodeUri(res.qr_code_data_uri);
        announce('MFA setup key generated. Follow the manual entry instructions.', 'polite');
      } catch (err) {
        const apiErr = err as NexisApiError;
        setErrors([apiErr.message]);
        focusFirstError();
      } finally {
        setInitialLoading(false);
      }
    };

    initEnrolment();
  }, []);

  const handleConfirm = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrors([]);
    setCodeError(undefined);

    const cleanCode = code.replace(/\s+/g, '');
    if (!cleanCode || cleanCode.length < 6) {
      const err = 'Please enter all 6 digits of your authenticator app code.';
      setCodeError(err);
      setErrors([err]);
      focusFirstError();
      announce(err, 'assertive');
      return;
    }

    setSubmitting(true);
    try {
      const res = await api.mfa.confirmEnrol(cleanCode);
      announce('MFA verified and enabled. Please save your recovery codes.', 'polite');
      onEnrolSuccess(res.recovery_codes);
      navigate('/recovery-codes', { state: { recoveryCodes: res.recovery_codes } });
    } catch (err) {
      const apiErr = err as NexisApiError;
      setErrors([apiErr.message]);
      setCodeError(apiErr.message);
      focusFirstError();
      announce(`Confirmation failed: ${apiErr.message}`, 'assertive');
    } finally {
      setSubmitting(false);
    }
  };

  if (initialLoading) {
    return (
      <div className="max-w-xl mx-auto my-12 p-8 text-center" role="status">
        <p className="text-lg font-semibold text-slate-700">
          Generating secure multi-factor authentication secret...
        </p>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto my-10 p-6 bg-white border border-slate-300 rounded-xl shadow-md">
      <h1 className="text-2xl font-bold text-slate-900 mb-2 focus:outline-none">
        Set Up Multi-Factor Authentication
      </h1>
      <p className="text-sm text-slate-600 mb-6 text-left">
        Multi-factor authentication protects your account by requiring a 6-digit code from your authenticator app every time you sign in.
      </p>

      <ErrorSummary errors={errors} />

      {secret && (
        <SecretDisplay
          secret={secret}
          secretGrouped={secretGrouped}
          qrCodeDataUri={qrCodeUri}
        />
      )}

      <section
        aria-labelledby="confirm-setup-heading"
        className="p-5 bg-white border-2 border-slate-300 rounded-lg shadow-sm text-left"
      >
        <h2 id="confirm-setup-heading" className="text-lg font-bold text-slate-900 mb-2">
          Step 2: Confirm Setup
        </h2>
        <p className="text-sm text-slate-700 mb-4">
          Enter the 6-digit code currently shown in your authenticator app to verify that setup was successful.
        </p>

        <form onSubmit={handleConfirm} noValidate>
          <CodeInput
            id="totp-confirm-input"
            value={code}
            onChange={setCode}
            error={codeError}
            disabled={submitting}
          />

          <button
            type="submit"
            disabled={submitting}
            className="w-full py-3 px-4 bg-blue-700 hover:bg-blue-800 text-white font-semibold rounded-md shadow-sm focus:outline-none focus:ring-4 focus:ring-blue-600 focus:ring-offset-2 transition-colors disabled:opacity-50 text-base"
          >
            {submitting ? 'Verifying Code...' : 'Confirm and Enable MFA'}
          </button>
        </form>
      </section>
    </div>
  );
};
