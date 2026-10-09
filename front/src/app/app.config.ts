import { registerLocaleData } from '@angular/common';
import { provideHttpClient, withFetch, withInterceptors } from '@angular/common/http';
import localeEsCo from '@angular/common/locales/es-CO';
import {
  type ApplicationConfig,
  inject,
  LOCALE_ID,
  provideAppInitializer,
  provideBrowserGlobalErrorListeners,
  provideZonelessChangeDetection,
} from '@angular/core';
import { provideRouter, withComponentInputBinding, withInMemoryScrolling } from '@angular/router';

import { routes } from './app.routes';
import { AuthService } from './core/auth/auth.service';
import { provideSessionExpiryRedirect } from './core/auth/session-expiry';
import { authInterceptor } from './core/interceptors/auth.interceptor';
import { APP_LOCALE } from './shared/utils/date-time';

registerLocaleData(localeEsCo);

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideZonelessChangeDetection(),
    provideRouter(
      routes,
      // Route params, query params and resolved data are bound to component inputs.
      withComponentInputBinding(),
      withInMemoryScrolling({ scrollPositionRestoration: 'enabled', anchorScrolling: 'enabled' }),
    ),
    provideHttpClient(withFetch(), withInterceptors([authInterceptor])),
    { provide: LOCALE_ID, useValue: APP_LOCALE },
    // Restore the session of this tab before the first navigation, so guards see the real state.
    provideAppInitializer(() => inject(AuthService).restoreSession()),
    // Sends the user to the login page if the session ends while on a protected page.
    provideSessionExpiryRedirect(),
  ],
};
