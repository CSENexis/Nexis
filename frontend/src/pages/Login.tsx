import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api, NexisApiError, UserMe } from '../lib/api';
import { setPageFocus, focusFirstError } from '../lib/focus';
import { announce } from '../a11y/announcements';
import { FormField } from '../components/FormField';
import { PasswordInput } from '../components/PasswordInput';
import { ErrorSummary } from '../components/ErrorSummary';

interface LoginProps {
  onLoginSuccess: (user: UserMe) => void;
}

export const Login: React.FC<LoginProps> = ({ onLoginSuccess }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [errors, setErrors] = useState<string[]>([]);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [lockoutRetryAfter, setLockoutRetryAfter] = useState<number | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    setPageFocus('Sign In');
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrors([]);
    setFieldErrors({});

    const currentFieldErrors: Record<string, string> = {};
    if (!email) currentFieldErrors.email = 'Email address is required.';
    if (!password) currentFieldErrors.password = 'Password is required.';

    if (Object.keys(currentFieldErrors).length > 0) {
      setFieldErrors(currentFieldErrors);
      setErrors(Object.values(currentFieldErrors));
      focusFirstError();
      announce('Sign in failed. Please review the errors.', 'assertive');
      return;
    }

    setLoading(true);
    try {
      const res = await api.auth.login(email, password);

      if (res.status === 'mfa_pending') {
        announce('Password verified. Multi-factor authentication step required.', 'polite');
        navigate('/mfa-verify');
      } else {
        announce('Sign in successful. Welcome to your account.', 'polite');
        const me = await api.auth.me();
        onLoginSuccess(me);
        if (!me.mfa_enabled) {
          navigate('/mfa-enrol');
        } else {
          navigate('/dashboard');
        }
      }
    } catch (err) {
      const apiErr = err as NexisApiError;
      setErrors([apiErr.message]);
      if (apiErr.code === 'ACCOUNT_LOCKED' && apiErr.retryAfter) {
        setLockoutRetryAfter(apiErr.retryAfter);
      }
      focusFirstError();
      announce(`Sign in failed: ${apiErr.message}`, 'assertive');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto my-10 p-6 bg-white border border-slate-300 rounded-xl shadow-md">
      <h1 className="text-2xl font-bold text-slate-900 mb-2 focus:outline-none">
        Sign In to Nexis
      </h1>
      <p className="text-sm text-slate-600 mb-6">
        Enter your credentials to access your protected account.
      </p>

      <ErrorSummary errors={errors} />

      {lockoutRetryAfter && (
        <div
          role="alert"
          className="mb-5 p-4 bg-yellow-50 border-2 border-yellow-600 text-yellow-950 rounded-md text-sm text-left"
        >
          <p className="font-bold">Temporary Account Lockout Active</p>
          <p className="mt-1">
            Too many consecutive failed sign-in attempts. For your security, this account is locked for approximately{' '}
            {Math.ceil(lockoutRetryAfter / 60)} minute(s).
          </p>
        </div>
      )}

      <form onSubmit={handleSubmit} noValidate>
        <FormField
          id="login-email"
          label="Email Address"
          type="email"
          autoComplete="username"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          error={fieldErrors.email}
        />

        <PasswordInput
          id="login-password"
          label="Password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          error={fieldErrors.password}
        />

        <button
          type="submit"
          disabled={loading}
          className="w-full py-3 px-4 bg-blue-700 hover:bg-blue-800 text-white font-semibold rounded-md shadow-sm focus:outline-none focus:ring-4 focus:ring-blue-600 focus:ring-offset-2 transition-colors disabled:opacity-50 text-base"
        >
          {loading ? 'Signing In...' : 'Sign In'}
        </button>

        <div className="mt-6 flex flex-col gap-2.5 text-sm text-slate-600">
          <div>
            <Link
              to="/recover"
              className="text-blue-700 font-semibold hover:underline focus:outline-none focus:ring-2 focus:ring-blue-600 rounded"
            >
              Lost access to your authenticator? Recover account
            </Link>
          </div>
          <div>
            Need an account?{' '}
            <Link
              to="/register"
              className="text-blue-700 font-semibold hover:underline focus:outline-none focus:ring-2 focus:ring-blue-600 rounded"
            >
              Register here
            </Link>
          </div>
        </div>
      </form>
    </div>
  );
};
