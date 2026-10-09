import { HttpTestingController } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import {
  buildEvent,
  cleanUpAuth,
  provideTestDependencies,
  TEST_API_URL,
} from '../../../../testing/test-helpers';
import { EventsService } from './events.service';

describe('EventsService', () => {
  let service: EventsService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: provideTestDependencies() });
    service = TestBed.inject(EventsService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => cleanUpAuth());

  it('should request a page with the backend pagination parameters', () => {
    service.list({ page: 2, perPage: 9, search: '  angular ' }).subscribe();

    const request = http.expectOne((req) => req.url === `${TEST_API_URL}/events`);
    expect(request.request.params.get('page')).toBe('2');
    expect(request.request.params.get('per_page')).toBe('9');
    expect(request.request.params.get('search')).toBe('angular');
    request.flush({ items: [], total: 0, page: 2, per_page: 9, pages: 0 });
  });

  it('should omit an empty search', () => {
    service.list({ page: 1, perPage: 9, search: '   ' }).subscribe();

    const request = http.expectOne((req) => req.url === `${TEST_API_URL}/events`);
    expect(request.request.params.has('search')).toBeFalse();
    request.flush({ items: [], total: 0, page: 1, per_page: 9, pages: 0 });
  });

  it('should load sessions from the event sessions endpoint', () => {
    service.getSessions(10).subscribe();
    http.expectOne(`${TEST_API_URL}/events/10/sessions`).flush([]);
  });

  it('should update with PUT', () => {
    const { id, name, description, location, start_date, end_date, capacity } = buildEvent();
    service.update(id, { name, description, location, start_date, end_date, capacity }).subscribe();

    const request = http.expectOne(`${TEST_API_URL}/events/${id}`);
    expect(request.request.method).toBe('PUT');
    request.flush(buildEvent());
  });

  it('should emit null when a draft is deleted (204)', () => {
    let result: unknown = 'pending';
    service.remove(10).subscribe((value) => (result = value));

    http
      .expectOne(`${TEST_API_URL}/events/10`)
      .flush(null, { status: 204, statusText: 'No Content' });

    expect(result).toBeNull();
  });

  it('should emit the cancelled event when a published event is removed (200)', () => {
    const cancelled = buildEvent({ status: 'CANCELLED' });
    let result: unknown;
    service.remove(10).subscribe((value) => (result = value));

    http.expectOne(`${TEST_API_URL}/events/10`).flush(cancelled);

    expect(result).toEqual(cancelled);
  });
});
