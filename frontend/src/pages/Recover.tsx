import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api, NexisApiError } from '../lib/api';
import { setPageFocus, focusFirstError } from '../lib/focus';
import { announce } from '../a11y/announcements';
import { FormField } from '../components/FormField';
import { PasswordInput } from '../components/PasswordInput';
import { ErrorSummary } from '../components/ErrorSummary';

export const Recover: React.FC = () => {
  const [step, setStep] = useState<1 | 2>(1);
  const [email, setEmail] = useState('');
  const [recoveryCode, setRecoveryCode] = useState('');
  const [recoveryToken, setRecoveryToken] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [errors, setErrors] = useState<string[]>([]);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    setPageFocus('Account Recovery');
  }, [step]);

  const handleStep1Submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrors([]);
    setFieldErrors({});

    const currentErrors: Record<string, string> = {};
    if (!email) currentErrors.email = 'Email address is required.';
    if (!recoveryCode) currentErrors.recoveryCode = 'Recovery code is required.';

    if (Object.keys(currentErrors).length > 0) {
      setFieldErrors(currentErrors);
      setErrors(Object.values(currentErrors));
      focusFirstError();
      announce('Account recovery failed. Please check the entered fields.', 'assertive');
      return;
    }

    setLoading(true);
    try {
      const res = await api.recovery.start(email, recoveryCode);
      setRecoveryToken(res.recovery_token);
      setStep(2);
      announce('Recovery code accepted. Step 2: Choose a new password.', 'polite');
    } catch (err) {
      const apiErr = err as NexisApiError;
      setErrors([apiErr.message]);
      focusFirstError();
      announce(`Recovery failed: ${apiErr.message}`, 'assertive');
    } finally {
      setLoading(false);
    }
  };

  const handleStep2Submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrors([]);
    setFieldErrors({});

    const currentErrors: Record<string, string> = {};
    if (!newPassword) {
      currentErrors.newPassword = 'New password is required.';
    } else if (newPassword.length < 8) {
      currentErrors.newPassword = 'Password must be at least 8 characters long.';
    }
    if (newPassword !== confirmPassword) {
      currentErrors.confirmPassword = 'Passwords do not match.';
    }

    if (Object.keys(currentErrors).length > 0) {
      setFieldErrors(currentErrors);
      setErrors(Object.values(currentErrors));
      focusFirstError();
      announce('Password reset failed. Please review errors.', 'assertive');
      return;
    }

    setLoading(true);
    try {
      const res = await api.recovery.complete(recoveryToken, newPassword);
      setSuccessMessage(res.message);
      announce(res.message, 'polite');
      setTimeout(() => {
        navigate('/login');
      }, 4000);
    } catch (err) {
      const apiErr = err as NexisApiError;
      setErrors([apiErr.message]);
      focusFirstError();
      announce(`Password reset failed: ${apiErr.message}`, 'assertive');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto my-10 p-6 bg-white border border-slate-300 rounded-xl shadow-md text-left">
      <h1 className="text-2xl font-bold text-slate-900 mb-2 focus:outline-none">
        Account Recovery
      </h1>
      <p className="text-sm text-slate-600 mb-6">
        {step === 1
          ? 'Use one of your 10 one-time recovery codes to regain access to your account.'
          : 'Step 2: Choose a new password. Multi-factor authentication will be reset for your security.'}
      </p>

      <ErrorSummary errors={errors} />

      {successMessage ? (
        <div
          role="status"
          className="p-4 bg-green-50 border-2 border-green-600 text-green-950 rounded-md font-medium"
        >
          <p>{successMessage}</p>
          <p className="mt-3 text-sm">
            Redirecting to sign in...{' '}
            <Link to="/login" className="underline font-bold focus:ring-2 focus:ring-blue-600 rounded">
              Sign In Now
            </Link>
          </p>
        </div>
      ) : step === 1 ? (
        <form onSubmit={handleStep1Submit} noValidate>
          <FormField
            id="recover-email"
            label="Account Email Address"
            type="email"
            autoComplete="username"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            error={fieldErrors.email}
          />

          <FormField
            id="recover-code"
            label="One-Time Recovery Code"
            type="text"
            required
            value={recoveryCode}
            onChange={(e) => setRecoveryCode(e.target.value)}
            error={fieldErrors.recoveryCode}
            placeholder="XXXX-XXXX-XXXX"
            hint="Enter any one of your unused 12-character recovery codes (e.g. 7K2M-9P4Q-3W5R). Spaces or hyphens are permitted."
          />

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 px-4 bg-blue-700 hover:bg-blue-800 text-white font-semibold rounded-md shadow-sm focus:outline-none focus:ring-4 focus:ring-blue-600 focus:ring-offset-2 transition-colors disabled:opacity-50 text-base"
          >
            {loading ? 'Verifying Recovery Code...' : 'Verify Recovery Code'}
          </button>

          <p className="mt-6 text-sm text-slate-600 text-center">
            Remember your credentials?{' '}
            <Link
              to="/login"
              className="text-blue-700 font-semibold hover:underline focus:outline-none focus:ring-2 focus:ring-blue-600 rounded"
            >
              Back to Sign In
            </Link>
          </p>
        </form>
      ) : (
        <form onSubmit={handleStep2Submit} noValidate>
          <div className="mb-5 p-3.5 bg-blue-50 border border-blue-300 rounded text-sm text-blue-950">
            <p className="font-semibold mb-1">MFA Reset Notice</p>
            <p>
              Completing password reset will clear your previous authenticator configuration. You will enrol in MFA again upon your next sign in.
            </p>
          </div>

          <PasswordInput
            id="recover-new-password"
            label="New Password"
            autoComplete="new-password"
            required
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            error={fieldErrors.newPassword}
            hint="Minimum 8 characters. Passphrases are permitted."
          />

          <PasswordInput
            id="recover-confirm-password"
            label="Confirm New Password"
            autoComplete="new-password"
            required
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            error={fieldErrors.confirmPassword}
          />

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 px-4 bg-green-700 hover:bg-green-800 text-white font-semibold rounded-md shadow-sm focus:outline-none focus:ring-4 focus:ring-green-600 focus:ring-offset-2 transition-colors disabled:opacity-50 text-base"
          >
            {loading ? 'Updating Password...' : 'Update Password & Reset MFA'}
          </button>
        </form>
      )}
    </div>
  );
};
