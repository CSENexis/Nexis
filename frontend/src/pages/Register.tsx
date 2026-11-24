import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api, NexisApiError } from '../lib/api';
import { setPageFocus, focusFirstError } from '../lib/focus';
import { announce } from '../a11y/announcements';
import { FormField } from '../components/FormField';
import { PasswordInput } from '../components/PasswordInput';
import { ErrorSummary } from '../components/ErrorSummary';

export const Register: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [errors, setErrors] = useState<string[]>([]);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    setPageFocus('Create an Account');
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrors([]);
    setFieldErrors({});

    const currentFieldErrors: Record<string, string> = {};
    if (!email) {
      currentFieldErrors.email = 'Email address is required.';
    }
    if (!password) {
      currentFieldErrors.password = 'Password is required.';
    } else if (password.length < 8) {
      currentFieldErrors.password = 'Password must be at least 8 characters long.';
    }
    if (password !== confirmPassword) {
      currentFieldErrors.confirmPassword = 'Passwords do not match.';
    }

    if (Object.keys(currentFieldErrors).length > 0) {
      setFieldErrors(currentFieldErrors);
      setErrors(Object.values(currentFieldErrors));
      focusFirstError();
      announce('Registration failed. Please review the form errors.', 'assertive');
      return;
    }

    setLoading(true);
    try {
      const res = await api.auth.register(email, password);
      setSuccessMessage(res.message);
      announce(res.message, 'polite');
      setTimeout(() => {
        navigate('/login');
      }, 3000);
    } catch (err) {
      const apiErr = err as NexisApiError;
      setErrors([apiErr.message]);
      focusFirstError();
      announce(`Registration error: ${apiErr.message}`, 'assertive');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto my-10 p-6 bg-white border border-slate-300 rounded-xl shadow-md">
      <h1 className="text-2xl font-bold text-slate-900 mb-2 focus:outline-none">
        Create an Account
      </h1>
      <p className="text-sm text-slate-600 mb-6">
        Register an account to explore accessible multi-factor authentication.
      </p>

      <ErrorSummary errors={errors} />

      {successMessage ? (
        <div
          role="status"
          className="p-4 bg-green-50 border border-green-600 text-green-900 rounded-md font-medium text-left"
        >
          <p>{successMessage}</p>
          <p className="mt-2 text-sm">
            Redirecting to sign-in page...{' '}
            <Link to="/login" className="underline font-bold focus:ring-2 focus:ring-blue-600 rounded">
              Sign In Now
            </Link>
          </p>
        </div>
      ) : (
        <form onSubmit={handleSubmit} noValidate>
          <FormField
            id="register-email"
            label="Email Address"
            type="email"
            autoComplete="username"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            error={fieldErrors.email}
            hint="We will never share your email address."
          />

          <PasswordInput
            id="register-password"
            label="Password"
            autoComplete="new-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            error={fieldErrors.password}
            hint="Minimum 8 characters. Passphrases are permitted. No arbitrary character rules required."
          />

          <PasswordInput
            id="register-confirm-password"
            label="Confirm Password"
            autoComplete="new-password"
            required
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            error={fieldErrors.confirmPassword}
          />

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 px-4 bg-blue-700 hover:bg-blue-800 text-white font-semibold rounded-md shadow-sm focus:outline-none focus:ring-4 focus:ring-blue-600 focus:ring-offset-2 transition-colors disabled:opacity-50 text-base"
          >
            {loading ? 'Creating Account...' : 'Create Account'}
          </button>

          <p className="mt-6 text-sm text-slate-600">
            Already have an account?{' '}
            <Link
              to="/login"
              className="text-blue-700 font-semibold hover:underline focus:outline-none focus:ring-2 focus:ring-blue-600 rounded"
            >
              Sign In
            </Link>
          </p>
        </form>
      )}
    </div>
  );
};
