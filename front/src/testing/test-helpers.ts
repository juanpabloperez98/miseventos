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
import {
  type EventImage,
  type EventModel,
  type EventPage,
} from '../app/features/events/models/event.model';
import { type EventSession } from '../app/features/events/models/session.model';

@Component({ template: '', changeDetection: ChangeDetectionStrategy.OnPush })
export class BlankPage {}

export const TEST_API_URL = 'http://api.test/api';

export function provideTestDependencies(routes: Routes = []): (Provider | EnvironmentProviders)[] {
  return [
    provideZonelessChangeDetection(),
    provideHttpClient(withInterceptors([authInterceptor])),
    provideHttpClientTesting(),
    provideRouter(routes, withComponentInputBinding()),
    { provide: API_URL, useValue: TEST_API_URL },
    provideSessionExpiryRedirect(),
  ];
}

export const TEST_USERS = {
  admin: { id: 1, name: 'Ada Admin', email: 'admin@test.dev', role: 'ADMIN' },
  organizer: { id: 2, name: 'Olga Organizer', email: 'organizer@test.dev', role: 'ORGANIZER' },
  otherOrganizer: { id: 3, name: 'Oscar Organizer', email: 'oscar@test.dev', role: 'ORGANIZER' },
  attendee: { id: 4, name: 'Ana Attendee', email: 'attendee@test.dev', role: 'ATTENDEE' },
} satisfies Record<string, User>;

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
    speaker_name: null,
    title: 'Signals en profundidad',
    description: null,
    start_time: '2030-05-10T15:00:00+00:00',
    end_time: '2030-05-10T16:00:00+00:00',
    capacity: 60,
    ...overrides,
  };
}

export function fillDateTime(container: Element, value: string): void {
  const host = container.querySelector('app-date-time-input');
  const date = host?.querySelector('input');
  const [hour, minute, period] = [...(host?.querySelectorAll('select') ?? [])];
  if (!date || !hour || !minute || !period) {
    throw new Error('Date and time input not found');
  }
  const [day, time] = value.split('T');
  const [hours, minutes] = time.split(':').map(Number);
  date.value = day;
  date.dispatchEvent(new Event('input'));
  const choose = (select: HTMLSelectElement, option: string) => {
    select.value = option;
    select.dispatchEvent(new Event('change'));
  };
  choose(hour, String(hours % 12 === 0 ? 12 : hours % 12));
  choose(minute, String(minutes).padStart(2, '0'));
  choose(period, hours < 12 ? 'AM' : 'PM');
}

export function buildImage(overrides: Partial<EventImage> = {}): EventImage {
  return {
    public_id: 'mis-eventos/events/10/0123456789abcdef0123456789abcdef',
    secure_url:
      'https://res.cloudinary.com/demo/image/upload/v1/mis-eventos/events/10/0123456789abcdef0123456789abcdef.jpg',
    width: 1600,
    height: 900,
    format: 'jpg',
    ...overrides,
  };
}

export function imageFile(name = 'cover.jpg', type = 'image/jpeg', size = 1024): File {
  return new File([new Uint8Array(size)], name, { type });
}

export function selectFile(input: HTMLInputElement, file: File): void {
  const transfer = new DataTransfer();
  transfer.items.add(file);
  input.files = transfer.files;
  input.dispatchEvent(new Event('change'));
}

export function textOf(element: Element | null | undefined): string {
  return element?.textContent?.replace(/\s+/g, ' ').trim() ?? '';
}
