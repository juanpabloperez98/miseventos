import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { type Observable } from 'rxjs';

import { API_URL } from '../../core/config/api-url.token';
import type { EventModel } from '../events';
import { type Registration } from './registration.model';

/**
 * Registrations of the authenticated user. The bearer token is added by the interceptor; the user
 * is always taken from the token by the backend, never sent by the client.
 */
@Injectable({ providedIn: 'root' })
export class RegistrationsService {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = inject(API_URL);

  /**
   * `GET /me/registrations`: the events the authenticated user is registered to (`EventSchema[]`),
   * ordered by start date, including events cancelled or completed after registering.
   */
  listMyEvents(): Observable<EventModel[]> {
    return this.http.get<EventModel[]>(`${this.apiUrl}/me/registrations`);
  }

  /**
   * `POST /events/{id}/registrations` with an empty body. Errors: 401 (no session), 404 (event not
   * visible), 409 (already registered, event not published or full).
   */
  register(eventId: number): Observable<Registration> {
    return this.http.post<Registration>(`${this.apiUrl}/events/${eventId}/registrations`, null);
  }
}
