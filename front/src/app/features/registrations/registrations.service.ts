import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { type Observable } from 'rxjs';

import { API_URL } from '../../core/config/api-url.token';
import type { EventModel } from '../events';
import { type Registration } from './registration.model';

@Injectable({ providedIn: 'root' })
export class RegistrationsService {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = inject(API_URL);

  listMyEvents(): Observable<EventModel[]> {
    return this.http.get<EventModel[]>(`${this.apiUrl}/me/registrations`);
  }

  register(eventId: number): Observable<Registration> {
    return this.http.post<Registration>(`${this.apiUrl}/events/${eventId}/registrations`, null);
  }
}
