import React, { useState, useEffect } from 'react';
import { registerLiveRegionDispatchers } from '../a11y/announcements';

/**
 * Persistent ARIA Live Regions for dynamic screen reader announcements (FR10, A29).
 * Contains both polite (status updates) and assertive (critical errors/alerts) channels.
 */
export const LiveRegion: React.FC = () => {
  const [politeMessage, setPoliteMessage] = useState<string>('');
  const [assertiveMessage, setAssertiveMessage] = useState<string>('');

  useEffect(() => {
    registerLiveRegionDispatchers(
      (msg) => {
        // Clear then update to ensure screen readers re-announce identical consecutive messages
        setPoliteMessage('');
        setTimeout(() => setPoliteMessage(msg), 50);
      },
      (msg) => {
        setAssertiveMessage('');
        setTimeout(() => setAssertiveMessage(msg), 50);
      }
    );
  }, []);

  return (
    <>
      <div
        role="status"
        aria-live="polite"
        aria-atomic="true"
        className="sr-only"
        id="aria-polite-region"
      >
        {politeMessage}
      </div>
      <div
        role="alert"
        aria-live="assertive"
        aria-atomic="true"
        className="sr-only"
        id="aria-assertive-region"
      >
        {assertiveMessage}
      </div>
    </>
  );
};
