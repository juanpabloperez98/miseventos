import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map, type Observable } from 'rxjs';

import { API_URL } from '../../../core/config/api-url.token';
import { type EventSession, type SessionPayload } from '../models/session.model';

@Injectable({ providedIn: 'root' })
export class SessionsService {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = inject(API_URL);

  get(sessionId: number): Observable<EventSession> {
    return this.http.get<EventSession>(`${this.apiUrl}/sessions/${sessionId}`);
  }

  create(eventId: number, payload: SessionPayload): Observable<EventSession> {
    return this.http.post<EventSession>(`${this.apiUrl}/events/${eventId}/sessions`, payload);
  }

  update(sessionId: number, payload: SessionPayload): Observable<EventSession> {
    return this.http.put<EventSession>(`${this.apiUrl}/sessions/${sessionId}`, payload);
  }

  remove(sessionId: number): Observable<void> {
    return this.http.delete(`${this.apiUrl}/sessions/${sessionId}`).pipe(map(() => undefined));
  }
}
