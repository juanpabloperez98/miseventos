import {
  DestroyRef,
  type EnvironmentProviders,
  inject,
  Injectable,
  provideEnvironmentInitializer,
} from '@angular/core';
import { type ActivatedRouteSnapshot, Router } from '@angular/router';
import { filter } from 'rxjs';

import { authGuard, eventManagerGuard } from '../guards/auth.guards';
import { FlashMessageService } from '../services/flash-message.service';
import { AuthService } from './auth.service';

// `unknown`: route configs may also hold legacy (class/token) guards, which never match.
const PROTECTING_GUARDS: readonly unknown[] = [authGuard, eventManagerGuard];

/**
 * Leaves protected pages when the session ends on its own (token expired or rejected with 401):
 * the user is sent to the login page once, with a return URL, instead of staying on a page they
 * can no longer use. A voluntary logout is handled by the header, which navigates to the catalog.
 *
 * `AuthService.sessionEnded$` emits once per session, so concurrent 401 responses produce a single
 * redirect, and the login page never triggers authenticated requests, so there is no loop.
 */
@Injectable({ providedIn: 'root' })
export class SessionExpiryRedirect {
  private readonly router = inject(Router);
  private readonly flashMessages = inject(FlashMessageService);

  constructor() {
    const subscription = inject(AuthService)
      .sessionEnded$.pipe(filter((reason) => reason !== 'logout'))
      .subscribe(() => this.leaveProtectedPage());
    inject(DestroyRef).onDestroy(() => subscription.unsubscribe());
  }

  private leaveProtectedPage(): void {
    if (!isProtected(this.router.routerState.snapshot.root)) {
      return;
    }
    this.flashMessages.set('info', 'Tu sesión ha expirado. Inicia sesión de nuevo para continuar.');
    void this.router.navigate(['/auth/login'], { queryParams: { returnUrl: this.router.url } });
  }
}

function isProtected(root: ActivatedRouteSnapshot): boolean {
  for (let route: ActivatedRouteSnapshot | null = root; route; route = route.firstChild) {
    if (route.routeConfig?.canActivate?.some((guard) => PROTECTING_GUARDS.includes(guard))) {
      return true;
    }
  }
  return false;
}

export function provideSessionExpiryRedirect(): EnvironmentProviders {
  return provideEnvironmentInitializer(() => inject(SessionExpiryRedirect));
}
