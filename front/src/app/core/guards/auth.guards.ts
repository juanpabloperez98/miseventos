import { inject } from '@angular/core';
import { type CanActivateFn, type CanMatchFn, RedirectCommand, Router } from '@angular/router';

import { AuthService } from '../auth/auth.service';
import { AuthorizationService } from '../auth/authorization.service';
import { FlashMessageService } from '../services/flash-message.service';

const LOGIN_URL = '/auth/login';
const HOME_URL = '/events';
const FORBIDDEN_URL = '/forbidden';

/** Only authenticated users. Anonymous users go to the login page and come back afterwards. */
export const authGuard: CanActivateFn = (_route, state) => {
  if (inject(AuthService).isAuthenticated()) {
    return true;
  }
  return inject(Router).createUrlTree([LOGIN_URL], { queryParams: { returnUrl: state.url } });
};

/**
 * Only users allowed to create and manage events (ADMIN, ORGANIZER).
 *
 * Authentication is checked first (anonymous → login with return URL); only then the role.
 * An authenticated user without permission keeps their session and sees the access-denied page.
 * `skipLocationChange` leaves the address bar untouched (on direct access it keeps the requested
 * URL) instead of rewriting it to /forbidden or the catalog. The backend still authorizes every
 * operation.
 */
export const eventManagerGuard: CanActivateFn = (route, state) => {
  const authenticated = authGuard(route, state);
  if (authenticated !== true) {
    return authenticated;
  }
  if (inject(AuthorizationService).canCreateEvents()) {
    return true;
  }
  inject(FlashMessageService).set('error', 'Tu cuenta no tiene permiso para gestionar eventos.');
  const router = inject(Router);
  return new RedirectCommand(router.parseUrl(FORBIDDEN_URL), { skipLocationChange: true });
};

/**
 * Route matching by permission: the event management pages only match for ADMIN and ORGANIZER.
 * Otherwise the router falls through to a sibling route with the same URL that renders "access
 * denied" behind `authGuard` (anonymous users → login with return URL). See events.routes.ts.
 */
export const canManageEventsMatch: CanMatchFn = () =>
  inject(AuthorizationService).canCreateEvents();

/** Login and registration pages are only for anonymous users. */
export const guestGuard: CanActivateFn = () => {
  if (!inject(AuthService).isAuthenticated()) {
    return true;
  }
  return inject(Router).createUrlTree([HOME_URL]);
};
