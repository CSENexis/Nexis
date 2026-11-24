import React from 'react';

interface CodeInputProps {
  id: string;
  value: string;
  onChange: (value: string) => void;
  label?: string;
  hint?: string;
  error?: string;
  disabled?: boolean;
}

/**
 * Accessible 6-digit TOTP code input (FR5, NFR1).
 * Features inputMode="numeric", autocomplete="one-time-code", space-tolerant input.
 */
export const CodeInput: React.FC<CodeInputProps> = ({
  id,
  value,
  onChange,
  label = '6-Digit Verification Code',
  hint = 'Enter the 6 digits displayed in your authenticator app (e.g. 123 456). Spaces are permitted.',
  error,
  disabled = false,
}) => {
  const hintId = `${id}-hint`;
  const errorId = error ? `${id}-error` : undefined;
  const describedBy = [hintId, errorId].filter(Boolean).join(' ');

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    // Keep raw numeric input, stripping non-digit characters for state
    const clean = e.target.value.replace(/[^0-9]/g, '').slice(0, 6);
    onChange(clean);
  };

  return (
    <div className="mb-6 text-left">
      <label
        htmlFor={id}
        className="block text-base font-semibold text-slate-900 mb-1.5"
      >
        {label}
        <span className="text-red-700 ml-1" aria-hidden="true">*</span>
        <span className="sr-only"> (required)</span>
      </label>

      <p id={hintId} className="text-sm text-slate-600 mb-3">
        {hint}
      </p>

      <input
        id={id}
        type="text"
        inputMode="numeric"
        autoComplete="one-time-code"
        pattern="[0-9]*"
        maxLength={8}
        value={value}
        onChange={handleChange}
        disabled={disabled}
        aria-required="true"
        aria-invalid={error ? 'true' : 'false'}
        aria-describedby={describedBy}
        placeholder="123456"
        className={`w-full max-w-xs text-center text-3xl tracking-widest font-mono py-3 px-4 bg-white border-2 ${
          error ? 'border-red-600 focus:border-red-700' : 'border-slate-400 focus:border-blue-700'
        } rounded-md text-slate-900 shadow-sm focus:outline-none focus:ring-4 focus:ring-blue-600`}
      />

      {error && (
        <p
          id={errorId}
          className="mt-2 text-sm font-semibold text-red-700 flex items-center gap-1"
        >
          <span className="sr-only">Error: </span>
          {error}
        </p>
      )}
    </div>
  );
};
