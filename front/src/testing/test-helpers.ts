import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import {
  ChangeDetectionStrategy,
  Component,
  type EnvironmentProviders,
  type Provider,
  provideZonelessChangeDetection,
} from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { provideRouter, type Routes, withComponentInputBinding } from '@angular/router';

import { type User } from '../app/core/auth/auth.models';
import { AuthService } from '../app/core/auth/auth.service';
import { provideSessionExpiryRedirect } from '../app/core/auth/session-expiry';
import { TokenStorage } from '../app/core/auth/token-storage';
import { API_URL } from '../app/core/config/api-url.token';
import { authInterceptor } from '../app/core/interceptors/auth.interceptor';
import { type EventModel, type EventPage } from '../app/features/events/models/event.model';
import { type EventSession } from '../app/features/events/models/session.model';

/** Placeholder routed component for destinations a test only navigates to. */
@Component({ template: '', changeDetection: ChangeDetectionStrategy.OnPush })
export class BlankPage {}

export const TEST_API_URL = 'http://api.test/api';

/**
 * Real HttpClient (with the auth interceptor) against `HttpTestingController`, real router and the
 * same session-expiry handling as the application.
 */
export function provideTestDependencies(routes: Routes = []): (Provider | EnvironmentProviders)[] {
  return [
    provideZonelessChangeDetection(),
    provideHttpClient(withInterceptors([authInterceptor])),
    provideHttpClientTesting(),
    provideRouter(routes, withComponentInputBinding()),
    { provide: API_URL, useValue: TEST_API_URL },
    // Same session-expiry behavior as the application (app.config.ts).
    provideSessionExpiryRedirect(),
  ];
}

export const TEST_USERS = {
  admin: { id: 1, name: 'Ada Admin', email: 'admin@test.dev', role: 'ADMIN' },
  organizer: { id: 2, name: 'Olga Organizer', email: 'organizer@test.dev', role: 'ORGANIZER' },
  otherOrganizer: { id: 3, name: 'Oscar Organizer', email: 'oscar@test.dev', role: 'ORGANIZER' },
  attendee: { id: 4, name: 'Ana Attendee', email: 'attendee@test.dev', role: 'ATTENDEE' },
} satisfies Record<string, User>;

/** Signs in through the real `AuthService`, answering the login and `/auth/me` requests. */
export function signInAs(user: User): void {
  const http = TestBed.inject(HttpTestingController);
  TestBed.inject(AuthService).login({ email: user.email, password: 'password123' }).subscribe();
  http.expectOne(`${TEST_API_URL}/auth/login`).flush({
    access_token: `token-${user.id}`,
    token_type: 'Bearer',
    expires_at: new Date(Date.now() + 60 * 60 * 1000).toISOString(),
  });
  http.expectOne(`${TEST_API_URL}/auth/me`).flush(user);
}

/** Clears the token persisted in `sessionStorage` and checks there are no unexpected requests. */
export function cleanUpAuth(): void {
  TestBed.inject(HttpTestingController).verify();
  TestBed.inject(TokenStorage).clear();
}

export function buildEvent(overrides: Partial<EventModel> = {}): EventModel {
  return {
    id: 10,
    name: 'Angular Summit',
    description: 'Charlas sobre Angular moderno.',
    location: 'Medellín',
    start_date: '2030-05-10T14:00:00+00:00',
    end_date: '2030-05-10T22:00:00+00:00',
    capacity: 120,
    status: 'PUBLISHED',
    created_by: TEST_USERS.organizer.id,
    ...overrides,
  };
}

export function buildPage(items: EventModel[], overrides: Partial<EventPage> = {}): EventPage {
  return { items, total: items.length, page: 1, per_page: 9, pages: 1, ...overrides };
}

export function buildSession(overrides: Partial<EventSession> = {}): EventSession {
  return {
    id: 100,
    event_id: 10,
    speaker_id: null,
    title: 'Signals en profundidad',
    description: null,
    start_time: '2030-05-10T15:00:00+00:00',
    end_time: '2030-05-10T16:00:00+00:00',
    capacity: 60,
    ...overrides,
  };
}

export function textOf(element: Element | null | undefined): string {
  return element?.textContent?.replace(/\s+/g, ' ').trim() ?? '';
}
