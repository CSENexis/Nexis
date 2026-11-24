// Global ARIA Live Region Announcement Dispatcher (FR10, A29)
type AnnouncementPriority = 'polite' | 'assertive';

let politeDispatcher: ((msg: string) => void) | null = null;
let assertiveDispatcher: ((msg: string) => void) | null = null;

export function registerLiveRegionDispatchers(
  polite: (msg: string) => void,
  assertive: (msg: string) => void
) {
  politeDispatcher = polite;
  assertiveDispatcher = assertive;
}

export function announce(message: string, priority: AnnouncementPriority = 'polite') {
  if (priority === 'assertive' && assertiveDispatcher) {
    assertiveDispatcher(message);
  } else if (politeDispatcher) {
    politeDispatcher(message);
  }
}
