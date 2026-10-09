import type { Environment } from './environment.model';

/**
 * Production build configuration.
 *
 * Everything in this file is embedded in the JavaScript bundle and is therefore PUBLIC.
 * Never put secrets, credentials or tokens here.
 */
export const environment: Environment = {
  production: true,
  /** Relative so the app and the API can share an origin behind a reverse proxy. */
  apiUrl: '/api',
};
