import { HttpErrorResponse } from '@angular/common/http';

import { describeApiError, toApiError } from './api-error';

describe('api-error', () => {
  it('should extract message and field errors from the backend error shape', () => {
    const error = new HttpErrorResponse({
      status: 422,
      error: {
        message: 'Request validation failed',
        errors: { json: { email: ['Not a valid email address.'], role: ['Unknown field.'] } },
      },
    });

    expect(toApiError(error)).toEqual({
      status: 422,
      serverMessage: 'Request validation failed',
      fieldErrors: { email: ['Not a valid email address.'], role: ['Unknown field.'] },
    });
  });

  it('should treat non HTTP errors as unreachable server', () => {
    expect(toApiError(new Error('boom')).status).toBe(0);
  });

  it('should translate known backend messages', () => {
    const error = toApiError(
      new HttpErrorResponse({ status: 409, error: { message: 'Email is already registered' } }),
    );
    expect(describeApiError(error)).toBe('Este correo ya está registrado.');
  });

  it('should fall back to a message per status', () => {
    expect(describeApiError({ status: 403, serverMessage: null, fieldErrors: {} })).toContain(
      'No tienes permiso',
    );
    expect(describeApiError({ status: 0, serverMessage: null, fieldErrors: {} })).toContain(
      'No se pudo conectar',
    );
    expect(describeApiError({ status: 503, serverMessage: null, fieldErrors: {} })).toContain(
      'error en el servidor',
    );
  });
});
