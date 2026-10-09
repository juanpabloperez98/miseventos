import { HttpTestingController } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import {
  buildEvent,
  cleanUpAuth,
  provideTestDependencies,
  signInAs,
  TEST_API_URL,
  TEST_USERS,
} from '../../../testing/test-helpers';
import { type EventModel } from '../events';
import { RegistrationsService } from './registrations.service';

describe('RegistrationsService', () => {
  let service: RegistrationsService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: provideTestDependencies() });
    service = TestBed.inject(RegistrationsService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => cleanUpAuth());

  it('should load the events of the authenticated user with the bearer token', () => {
    signInAs(TEST_USERS.attendee);
    const events = [buildEvent({ id: 1 }), buildEvent({ id: 2, status: 'CANCELLED' })];
    let result: EventModel[] | undefined;

    service.listMyEvents().subscribe((value) => (result = value));

    const request = http.expectOne(`${TEST_API_URL}/me/registrations`);
    expect(request.request.method).toBe('GET');
    expect(request.request.headers.get('Authorization')).toBe(
      `Bearer token-${TEST_USERS.attendee.id}`,
    );
    request.flush(events);

    expect(result).toEqual(events);
  });

  it('should register the authenticated user with an empty body', () => {
    signInAs(TEST_USERS.attendee);
    const registration = {
      id: 1,
      event_id: 10,
      user_id: TEST_USERS.attendee.id,
      registered_at: '2030-01-01T10:00:00+00:00',
    };
    let result: unknown;

    service.register(10).subscribe((value) => (result = value));

    const request = http.expectOne(`${TEST_API_URL}/events/10/registrations`);
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toBeNull();
    expect(request.request.headers.get('Authorization')).toBe(
      `Bearer token-${TEST_USERS.attendee.id}`,
    );
    request.flush(registration, { status: 201, statusText: 'Created' });

    expect(result).toEqual(registration);
  });
});
