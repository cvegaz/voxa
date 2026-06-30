import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { Contact } from './Contact';
import { LanguageProvider } from '../i18n/LanguageContext';

// Mock the API module so no real network call happens.
vi.mock('../services/contactApi', () => ({
  submitContact: vi.fn(),
  ContactApiError: class extends Error {},
}));

import { submitContact } from '../services/contactApi';

function renderContact() {
  return render(
    <LanguageProvider>
      <Contact />
    </LanguageProvider>
  );
}

describe('Contact form', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it('shows validation errors and does not submit when empty', async () => {
    const user = userEvent.setup();
    renderContact();

    await user.click(screen.getByRole('button', { name: /Enviar mensaje/i }));

    expect(screen.getByText('Escribe tu nombre.')).toBeInTheDocument();
    expect(screen.getByText('Escribe un correo válido.')).toBeInTheDocument();
    expect(screen.getByText('Escribe un mensaje.')).toBeInTheDocument();
    expect(submitContact).not.toHaveBeenCalled();
  });

  it('submits a valid form and shows the success message', async () => {
    (submitContact as ReturnType<typeof vi.fn>).mockResolvedValue({
      id: 'abc',
      status: 'received',
    });
    const user = userEvent.setup();
    renderContact();

    await user.type(screen.getByLabelText('Nombre'), 'Carlos');
    await user.type(screen.getByLabelText('Correo'), 'carlos@example.com');
    await user.type(screen.getByLabelText('Mensaje'), 'Quiero adaptar Voxa.');
    await user.click(screen.getByRole('button', { name: /Enviar mensaje/i }));

    await waitFor(() => {
      expect(screen.getByText(/Mensaje recibido/i)).toBeInTheDocument();
    });

    expect(submitContact).toHaveBeenCalledTimes(1);
    const payload = (submitContact as ReturnType<typeof vi.fn>).mock.calls[0][0];
    expect(payload).toMatchObject({
      name: 'Carlos',
      email: 'carlos@example.com',
      message: 'Quiero adaptar Voxa.',
      sourceLang: 'es',
      website: '',
    });
  });

  it('shows an error message when the API call fails', async () => {
    (submitContact as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('boom'));
    const user = userEvent.setup();
    renderContact();

    await user.type(screen.getByLabelText('Nombre'), 'Carlos');
    await user.type(screen.getByLabelText('Correo'), 'carlos@example.com');
    await user.type(screen.getByLabelText('Mensaje'), 'Hola');
    await user.click(screen.getByRole('button', { name: /Enviar mensaje/i }));

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
    });
    expect(screen.getByText(/No se pudo enviar el mensaje/i)).toBeInTheDocument();
  });
});
