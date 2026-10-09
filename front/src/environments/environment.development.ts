import type { Environment } from './environment.model';

/**
 * Development configuration. Replaces `environment.ts` when building with
 * `--configuration development` (the default for `ng serve`). See `fileReplacements` in angular.json.
 *
 * Values here are PUBLIC: they end up in the browser bundle.
 */
export const environment: Environment = {
  production: false,
  apiUrl: 'http://localhost:5000/api',
};
