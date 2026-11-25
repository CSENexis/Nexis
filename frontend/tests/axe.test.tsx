import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { axe } from 'jest-axe';
import { BrowserRouter } from 'react-router-dom';

import { Register } from '../src/pages/Register';
import { Login } from '../src/pages/Login';
import { MfaVerify } from '../src/pages/MfaVerify';
import { MfaEnrol } from '../src/pages/MfaEnrol';
import { RecoveryCodes } from '../src/pages/RecoveryCodes';
import { Recover } from '../src/pages/Recover';
import { Dashboard } from '../src/pages/Dashboard';

describe('WCAG 2.1 AA Automated Axe Audits on All Screens', () => {
  it('Register page has zero accessibility violations', async () => {
    const { container } = render(
      <BrowserRouter>
        <Register />
      </BrowserRouter>
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('Login page has zero accessibility violations', async () => {
    const { container } = render(
      <BrowserRouter>
        <Login onLoginSuccess={() => {}} />
      </BrowserRouter>
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('MfaVerify page has zero accessibility violations', async () => {
    const { container } = render(
      <BrowserRouter>
        <MfaVerify onVerificationSuccess={() => {}} />
      </BrowserRouter>
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('MfaEnrol page has zero accessibility violations', async () => {
    const { container } = render(
      <BrowserRouter>
        <MfaEnrol onEnrolSuccess={() => {}} />
      </BrowserRouter>
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('RecoveryCodes page has zero accessibility violations', async () => {
    const { container } = render(
      <BrowserRouter>
        <RecoveryCodes />
      </BrowserRouter>
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('Recover page has zero accessibility violations', async () => {
    const { container } = render(
      <BrowserRouter>
        <Recover />
      </BrowserRouter>
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('Dashboard page has zero accessibility violations', async () => {
    const user = {
      status: 'authenticated' as const,
      email: 'user@example.com',
      mfa_enabled: true,
      user_id: 'test-uuid-1234'
    };
    const { container } = render(
      <BrowserRouter>
        <Dashboard user={user} onLogout={() => {}} />
      </BrowserRouter>
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
