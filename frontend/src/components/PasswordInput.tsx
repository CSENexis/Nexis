import React, { useState } from 'react';
import { announce } from '../a11y/announcements';

interface PasswordInputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  id: string;
  label: string;
  hint?: string;
  error?: string;
}

/**
 * Accessible password field with accessible toggle button (NFR1).
 */
export const PasswordInput: React.FC<PasswordInputProps> = ({
  id,
  label,
  hint,
  error,
  className = '',
  required,
  ...inputProps
}) => {
  const [showPassword, setShowPassword] = useState(false);
  const hintId = hint ? `${id}-hint` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  const describedBy = [hintId, errorId].filter(Boolean).join(' ') || undefined;

  const toggleVisibility = () => {
    const nextState = !showPassword;
    setShowPassword(nextState);
    announce(nextState ? 'Password revealed as plain text.' : 'Password hidden.', 'polite');
  };

  return (
    <div className="mb-5 text-left">
      <label
        htmlFor={id}
        className="block text-sm font-semibold text-slate-800 mb-1.5"
      >
        {label}
        {required && <span className="text-red-700 ml-1" aria-hidden="true">*</span>}
        {required && <span className="sr-only"> (required)</span>}
      </label>

      {hint && (
        <p id={hintId} className="text-sm text-slate-600 mb-2">
          {hint}
        </p>
      )}

      <div className="relative">
        <input
          id={id}
          type={showPassword ? 'text' : 'password'}
          required={required}
          aria-invalid={error ? 'true' : 'false'}
          aria-describedby={describedBy}
          className={`w-full px-3.5 py-2.5 pr-28 bg-white border-2 ${
            error ? 'border-red-600 focus:border-red-700' : 'border-slate-300 focus:border-blue-700'
          } rounded-md text-slate-900 text-base shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-600 ${className}`}
          {...inputProps}
        />

        <button
          type="button"
          onClick={toggleVisibility}
          aria-pressed={showPassword}
          aria-label={showPassword ? 'Hide password' : 'Show password as plain text'}
          className="absolute inset-y-1 right-1 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-sm font-medium rounded border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-600"
        >
          {showPassword ? 'Hide' : 'Show'}
        </button>
      </div>

      {error && (
        <p
          id={errorId}
          className="mt-1.5 text-sm font-medium text-red-700 flex items-center gap-1"
        >
          <span className="sr-only">Error: </span>
          {error}
        </p>
      )}
    </div>
  );
};
