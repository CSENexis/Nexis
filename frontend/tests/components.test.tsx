import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { FormField } from '../src/components/FormField';
import { PasswordInput } from '../src/components/PasswordInput';
import { CodeInput } from '../src/components/CodeInput';
import { SecretDisplay } from '../src/components/SecretDisplay';
import { SkipLink } from '../src/components/SkipLink';

describe('Accessible UI Components', () => {
  it('FormField associates label with input and announces errors with aria-describedby', () => {
    render(
      <FormField
        id="email-input"
        label="Email Address"
        hint="Enter your work email"
        error="Invalid email format"
        value=""
        onChange={() => {}}
      />
    );

    const input = screen.getByLabelText(/Email Address/i);
    expect(input).toBeInTheDocument();
    expect(input).toHaveAttribute('aria-invalid', 'true');
    expect(input).toHaveAttribute('aria-describedby', 'email-input-hint email-input-error');

    expect(screen.getByText('Enter your work email')).toBeInTheDocument();
    expect(screen.getByText('Invalid email format')).toBeInTheDocument();
  });

  it('PasswordInput toggles password visibility and updates aria-pressed', () => {
    render(
      <PasswordInput
        id="pwd-input"
        label="Account Password"
        value="Secret123!"
        onChange={() => {}}
      />
    );

    const input = screen.getByLabelText(/Account Password/i) as HTMLInputElement;
    const toggleBtn = screen.getByRole('button', { name: /Show password as plain text/i });

    expect(input.type).toBe('password');
    expect(toggleBtn).toHaveAttribute('aria-pressed', 'false');

    // Click toggle
    fireEvent.click(toggleBtn);
    expect(input.type).toBe('text');
    expect(toggleBtn).toHaveAttribute('aria-pressed', 'true');
    expect(toggleBtn).toHaveAttribute('aria-label', 'Hide password');
  });

  it('CodeInput sanitizes non-numeric characters and enforces 6-digit maximum', () => {
    const handleChange = vi.fn();
    render(
      <CodeInput
        id="totp-input"
        value=""
        onChange={handleChange}
      />
    );

    const input = screen.getByRole('textbox', { name: /6-Digit Verification Code/i });
    expect(input).toHaveAttribute('inputMode', 'numeric');
    expect(input).toHaveAttribute('autoComplete', 'one-time-code');

    // Type code with spaces and letters
    fireEvent.change(input, { target: { value: '12 3ab 456' } });
    expect(handleChange).toHaveBeenCalledWith('123456');
  });

  it('SecretDisplay shows text secret first with copy button and grouped view', () => {
    const secret = 'JBSWY3DPEHPK3PXP';
    const grouped = 'JBSW Y3DP EHPK 3PXP';

    render(
      <SecretDisplay
        secret={secret}
        secretGrouped={grouped}
        qrCodeDataUri="data:image/png;base64,mockqr"
      />
    );

    // Assert text secret is prominently shown
    const codeElem = screen.getByText(secret);
    expect(codeElem).toBeInTheDocument();

    // Toggle grouped view
    const groupBtn = screen.getByRole('button', { name: /Show in Groups of 4/i });
    fireEvent.click(groupBtn);
    expect(screen.getByText(grouped)).toBeInTheDocument();

    // Verify copy button exists with label
    const copyBtn = screen.getByRole('button', { name: /Copy secret key to clipboard/i });
    expect(copyBtn).toBeInTheDocument();
  });

  it('SkipLink targets #main-content and has accessible label', () => {
    render(<SkipLink />);
    const link = screen.getByRole('link', { name: /Skip to main content/i });
    expect(link).toHaveAttribute('href', '#main-content');
  });
});
