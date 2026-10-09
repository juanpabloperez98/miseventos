import { InjectionToken } from '@angular/core';

import { environment } from '../../../environments/environment';

/**
 * Base URL of the REST API (e.g. `http://localhost:5000/api`).
 *
 * Data-access services inject this token instead of importing `environment` directly, which keeps
 * them decoupled from the build configuration and lets tests provide a different value.
 */
export const API_URL = new InjectionToken<string>('API_URL', {
  providedIn: 'root',
  factory: () => environment.apiUrl,
});
