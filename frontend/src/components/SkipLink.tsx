import React from 'react';

/**
 * Skip link for keyboard users (WCAG 2.1 Success Criterion 2.4.1 Bypass Blocks).
 * Remains hidden until focused via the Tab key.
 */
export const SkipLink: React.FC = () => {
  return (
    <a
      href="#main-content"
      className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-50 focus:px-6 focus:py-3 focus:bg-blue-900 focus:text-white focus:font-semibold focus:rounded-md focus:shadow-xl focus:ring-4 focus:ring-yellow-400 focus:outline-none"
    >
      Skip to main content
    </a>
  );
};
