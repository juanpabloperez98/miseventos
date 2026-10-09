import { HttpErrorResponse, type HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, throwError } from 'rxjs';

import { AuthService } from '../auth/auth.service';
import { API_URL } from '../config/api-url.token';

/** Endpoints that must never receive a bearer token. */
const CREDENTIAL_ENDPOINTS = ['/auth/login', '/auth/register'];

/**
 * Adds `Authorization: Bearer <token>` to requests sent to the configured API only, so the JWT never
 * reaches other domains.
 *
 * A 401 on a request that carried the token means the session is no longer valid: it is cleared. The
 * backend rejects invalid tokens even on public endpoints, so safe `GET` requests are retried once
 * anonymously. A 403 does not end the session: the user is authenticated but not allowed.
 */
export const authInterceptor: HttpInterceptorFn = (request, next) => {
  const apiUrl = inject(API_URL);
  const auth = inject(AuthService);

  if (!isApiRequest(request.url, apiUrl) || isCredentialRequest(request.url, apiUrl)) {
    return next(request);
  }

  const token = auth.accessToken();
  if (!token) {
    return next(request);
  }

  const authorized = request.clone({ setHeaders: { Authorization: `Bearer ${token}` } });
  return next(authorized).pipe(
    catchError((error: unknown) => {
      if (!(error instanceof HttpErrorResponse) || error.status !== 401) {
        return throwError(() => error);
      }
      auth.handleRejectedToken();
      return request.method === 'GET' ? next(request) : throwError(() => error);
    }),
  );
};

function isApiRequest(url: string, apiUrl: string): boolean {
  return url === apiUrl || url.startsWith(`${apiUrl}/`) || url.startsWith(`${apiUrl}?`);
}

function isCredentialRequest(url: string, apiUrl: string): boolean {
  return CREDENTIAL_ENDPOINTS.some((endpoint) => url.startsWith(`${apiUrl}${endpoint}`));
}
