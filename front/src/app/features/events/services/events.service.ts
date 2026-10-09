import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map, type Observable } from 'rxjs';

import { API_URL } from '../../../core/config/api-url.token';
import {
  type EventModel,
  type EventPage,
  type EventPayload,
  type EventQuery,
  type EventUpdatePayload,
} from '../models/event.model';
import { type EventSession } from '../models/session.model';

/** Access to the `/events` endpoints. Components never build API URLs themselves. */
@Injectable({ providedIn: 'root' })
export class EventsService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${inject(API_URL)}/events`;

  /** Server-side paginated catalog. */
  list(query: EventQuery): Observable<EventPage> {
    let params = new HttpParams().set('page', query.page).set('per_page', query.perPage);
    const search = query.search?.trim();
    if (search) {
      params = params.set('search', search);
    }
    if (query.status) {
      params = params.set('status', query.status);
    }
    return this.http.get<EventPage>(this.baseUrl, { params });
  }

  get(id: number): Observable<EventModel> {
    return this.http.get<EventModel>(`${this.baseUrl}/${id}`);
  }

  /** Sessions of the event, ordered by start time. Requested separately from the event. */
  getSessions(eventId: number): Observable<EventSession[]> {
    return this.http.get<EventSession[]>(`${this.baseUrl}/${eventId}/sessions`);
  }

  /** Creates a `DRAFT` event owned by the current user. */
  create(payload: EventPayload): Observable<EventModel> {
    return this.http.post<EventModel>(this.baseUrl, payload);
  }

  /** Replaces the editable fields (the backend has no `PATCH`). */
  update(id: number, payload: EventUpdatePayload): Observable<EventModel> {
    return this.http.put<EventModel>(`${this.baseUrl}/${id}`, payload);
  }

  /**
   * Drafts are deleted (`204`, emits `null`); published events are cancelled instead (`200`, emits
   * the cancelled event).
   */
  remove(id: number): Observable<EventModel | null> {
    return this.http
      .delete<EventModel>(`${this.baseUrl}/${id}`, { observe: 'response' })
      .pipe(map((response) => (response.status === 204 ? null : response.body)));
  }
}
