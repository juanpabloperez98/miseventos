import { inject } from '@angular/core';
import { type CanActivateFn, Router } from '@angular/router';

import { AuthService } from '../auth/auth.service';
import { AuthorizationService } from '../auth/authorization.service';
import { FlashMessageService } from '../services/flash-message.service';

const LOGIN_URL = '/auth/login';
const HOME_URL = '/events';

/** Only authenticated users. Anonymous users go to the login page and come back afterwards. */
export const authGuard: CanActivateFn = (_route, state) => {
  if (inject(AuthService).isAuthenticated()) {
    return true;
  }
  return inject(Router).createUrlTree([LOGIN_URL], { queryParams: { returnUrl: state.url } });
};

/** Only users allowed to create and manage events (ADMIN, ORGANIZER). */
export const eventManagerGuard: CanActivateFn = (route, state) => {
  const authenticated = authGuard(route, state);
  if (authenticated !== true) {
    return authenticated;
  }
  if (inject(AuthorizationService).canCreateEvents()) {
    return true;
  }
  inject(FlashMessageService).set('error', 'Tu cuenta no tiene permiso para gestionar eventos.');
  return inject(Router).createUrlTree([HOME_URL]);
};

/** Login and registration pages are only for anonymous users. */
export const guestGuard: CanActivateFn = () => {
  if (!inject(AuthService).isAuthenticated()) {
    return true;
  }
  return inject(Router).createUrlTree([HOME_URL]);
};
