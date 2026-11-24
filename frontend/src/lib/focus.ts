import { announce } from '../a11y/announcements';

/**
 * Focuses the primary page heading (H1) and updates document title (FR10, NFR1).
 * Essential for screen reader route change notifications.
 */
export function setPageFocus(pageTitle: string) {
  document.title = `${pageTitle} | Nexis Accessible Authentication`;

  // Allow DOM to settle before moving focus
  setTimeout(() => {
    const heading = document.querySelector('h1') as HTMLElement | null;
    if (heading) {
      heading.setAttribute('tabindex', '-1');
      heading.focus();
    }
    announce(`${pageTitle} loaded.`, 'polite');
  }, 100);
}

/**
 * Shifts keyboard focus to the first invalid field or error summary (FR10).
 */
export function focusFirstError(containerId?: string) {
  setTimeout(() => {
    const container = containerId ? document.getElementById(containerId) : document;
    const errorSummary = container?.querySelector('[role="alert"]') as HTMLElement | null;
    if (errorSummary) {
      errorSummary.setAttribute('tabindex', '-1');
      errorSummary.focus();
      return;
    }

    const firstInvalid = container?.querySelector('[aria-invalid="true"]') as HTMLElement | null;
    if (firstInvalid) {
      firstInvalid.focus();
    }
  }, 50);
}
