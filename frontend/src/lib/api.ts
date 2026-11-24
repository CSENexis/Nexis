// API client with built-in CSRF headers and accessible error translation (A31, FR8)

export interface ApiError {
  code: string;
  message: string;
}

export interface UserMe {
  status: 'authenticated' | 'mfa_pending' | 'unauthenticated';
  user_id?: string | null;
  email?: string | null;
  mfa_enabled: boolean;
}

export class NexisApiError extends Error {
  code: string;
  status: number;
  retryAfter?: number;

  constructor(status: number, code: string, message: string, retryAfter?: number) {
    super(message);
    this.name = 'NexisApiError';
    this.status = status;
    this.code = code;
    this.retryAfter = retryAfter;
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers || {});
  
  // Enforce CSRF header on state-changing requests (FR8)
  if (['POST', 'PUT', 'DELETE', 'PATCH'].includes(options.method || 'GET')) {
    headers.set('X-Requested-With', 'XMLHttpRequest');
  }

  if (options.body && typeof options.body === 'string') {
    headers.set('Content-Type', 'application/json');
  }

  const response = await fetch(endpoint, {
    ...options,
    headers,
    credentials: 'include', // Ensure HttpOnly session cookies are transmitted (FR8, A10)
  });

  const retryAfterHeader = response.headers.get('Retry-After');
  const retryAfter = retryAfterHeader ? parseInt(retryAfterHeader, 10) : undefined;

  if (!response.ok) {
    let errorData: { error?: ApiError } = {};
    try {
      errorData = await response.json();
    } catch {
      // Non-JSON response
    }

    const code = errorData.error?.code || 'REQUEST_FAILED';
    const message = errorData.error?.message || `Request failed with status ${response.status}. Please try again.`;

    throw new NexisApiError(response.status, code, message, retryAfter);
  }

  return response.json();
}

export const api = {
  auth: {
    register: (email: string, password: string) =>
      request<{ message: string }>('/api/auth/register', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      }),

    login: (email: string, password: string) =>
      request<{
        status: 'authenticated' | 'mfa_pending';
        message: string;
        email: string;
        mfa_enabled: boolean;
      }>('/api/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      }),

    logout: () =>
      request<{ message: string }>('/api/auth/logout', {
        method: 'POST',
      }),

    me: () => request<UserMe>('/api/auth/me'),
  },

  mfa: {
    startEnrol: () =>
      request<{
        secret: string;
        secret_grouped: string;
        otpauth_uri: string;
        qr_code_data_uri: string;
        message: string;
      }>('/api/mfa/enrol/start', {
        method: 'POST',
      }),

    confirmEnrol: (code: string) =>
      request<{
        message: string;
        recovery_codes: string[];
      }>('/api/mfa/enrol/confirm', {
        method: 'POST',
        body: JSON.stringify({ code }),
      }),

    verify: (code: string) =>
      request<{
        status: string;
        message: string;
      }>('/api/mfa/verify', {
        method: 'POST',
        body: JSON.stringify({ code }),
      }),
  },

  recovery: {
    start: (email: string, recovery_code: string) =>
      request<{
        message: string;
        recovery_token: string;
      }>('/api/recovery/start', {
        method: 'POST',
        body: JSON.stringify({ email, recovery_code }),
      }),

    complete: (recovery_token: string, new_password: string) =>
      request<{
        message: string;
      }>('/api/recovery/complete', {
        method: 'POST',
        body: JSON.stringify({ recovery_token, new_password }),
      }),

    regenerate: () =>
      request<{
        message: string;
        recovery_codes: string[];
      }>('/api/recovery/regenerate', {
        method: 'POST',
      }),
  },
};
