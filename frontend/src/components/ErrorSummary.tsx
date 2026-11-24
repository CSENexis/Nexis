import React from 'react';

interface ErrorSummaryProps {
  title?: string;
  errors: string[];
}

/**
 * Accessible Error Summary for form submissions (WCAG 2.1 Success Criterion 3.3.1 Error Identification).
 * Receives programmatic keyboard focus on submit failure.
 */
export const ErrorSummary: React.FC<ErrorSummaryProps> = ({
  title = 'There was a problem with your submission',
  errors,
}) => {
  if (errors.length === 0) return null;

  return (
    <div
      role="alert"
      tabIndex={-1}
      aria-labelledby="error-summary-heading"
      className="p-4 mb-6 bg-red-50 border-2 border-red-600 rounded-lg text-left shadow-sm focus:outline-none focus:ring-4 focus:ring-red-600"
      id="error-summary"
    >
      <h2
        id="error-summary-heading"
        className="text-base font-bold text-red-900 mb-2 flex items-center gap-2"
      >
        <span aria-hidden="true" className="font-mono text-xl font-bold">!</span>
        {title}
      </h2>

      <ul className="list-disc list-inside text-sm font-medium text-red-800 space-y-1">
        {errors.map((error, idx) => (
          <li key={idx}>{error}</li>
        ))}
      </ul>
    </div>
  );
};
