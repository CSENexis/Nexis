import React from 'react';

interface FormFieldProps extends React.InputHTMLAttributes<HTMLInputElement> {
  id: string;
  label: string;
  hint?: string;
  error?: string;
}

/**
 * Accessible form field with explicit label association and aria-describedby linkage (NFR1, FR10).
 */
export const FormField: React.FC<FormFieldProps> = ({
  id,
  label,
  hint,
  error,
  className = '',
  required,
  ...inputProps
}) => {
  const hintId = hint ? `${id}-hint` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  const describedBy = [hintId, errorId].filter(Boolean).join(' ') || undefined;

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

      <input
        id={id}
        required={required}
        aria-invalid={error ? 'true' : 'false'}
        aria-describedby={describedBy}
        className={`w-full px-3.5 py-2.5 bg-white border-2 ${
          error ? 'border-red-600 focus:border-red-700' : 'border-slate-300 focus:border-blue-700'
        } rounded-md text-slate-900 text-base shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-600 ${className}`}
        {...inputProps}
      />

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
