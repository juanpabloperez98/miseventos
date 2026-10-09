import { HttpTestingController } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import {
  buildEvent,
  buildPage,
  cleanUpAuth,
  provideTestDependencies,
  signInAs,
  TEST_API_URL,
  TEST_USERS,
} from '../../../../testing/test-helpers';
import { EVENT_LIST_CACHE_TTL_MS, EventsService } from './events.service';

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

  describe('catalog cache', () => {
    const query = { page: 1, perPage: 9 };
    const listRequests = () => http.match((req) => req.url === `${TEST_API_URL}/events`);
    const page = buildPage([buildEvent()]);
    const { id, name, description, location, start_date, end_date, capacity } = buildEvent();
    const payload = { name, description, location, start_date, end_date, capacity };

    /** Loads the catalog once, so the next identical request can come from the cache. */
    function loadCatalog(): void {
      service.list(query).subscribe();
      const [request] = listRequests();
      request.flush(page);
    }

    beforeEach(() => {
      jasmine.clock().install();
      jasmine.clock().mockDate(new Date('2030-05-10T15:00:00Z'));
    });

    afterEach(() => jasmine.clock().uninstall());

    it('should send a single request for identical concurrent calls', () => {
      const received: unknown[] = [];
      service.list(query).subscribe((value) => received.push(value));
      service.list({ ...query, search: '' }).subscribe((value) => received.push(value));

      const requests = listRequests();
      expect(requests.length).toBe(1);
      requests[0].flush(page);
      expect(received).toEqual([page, page]);
    });

    it('should reuse the response for 60 seconds and then request it again', () => {
      loadCatalog();

      jasmine.clock().tick(EVENT_LIST_CACHE_TTL_MS - 1);
      let reused: unknown;
      service.list(query).subscribe((value) => (reused = value));
      expect(reused).toEqual(page);
      expect(listRequests().length).toBe(0);

      jasmine.clock().tick(1);
      service.list(query).subscribe();
      expect(listRequests().length).toBe(1);
    });

    it('should request different pages and searches separately', () => {
      loadCatalog();
      service.list({ ...query, page: 2 }).subscribe();
      service.list({ ...query, search: 'angular' }).subscribe();

      expect(listRequests().length).toBe(2);
    });

    it('should not keep a failed response', () => {
      service.list(query).subscribe({ error: () => undefined });
      listRequests()[0].flush(null, { status: 500, statusText: 'Server Error' });

      service.list(query).subscribe();
      expect(listRequests().length).toBe(1);
    });

    it('should not share the catalog between sessions', () => {
      loadCatalog();
      signInAs(TEST_USERS.organizer);

      service.list(query).subscribe();
      expect(listRequests().length).toBe(1);
    });

    const changes: [string, () => void][] = [
      [
        'creating',
        () => {
          service.create(payload).subscribe();
          http.expectOne({ method: 'POST', url: `${TEST_API_URL}/events` }).flush(buildEvent());
        },
      ],
      [
        'editing',
        () => {
          service.update(id, payload).subscribe();
          http.expectOne(`${TEST_API_URL}/events/${id}`).flush(buildEvent());
        },
      ],
      [
        'deleting',
        () => {
          service.remove(id).subscribe();
          http
            .expectOne(`${TEST_API_URL}/events/${id}`)
            .flush(null, { status: 204, statusText: 'No Content' });
        },
      ],
    ];
    for (const [change, perform] of changes) {
      it(`should request the catalog again after ${change} an event`, () => {
        loadCatalog();
        perform();

        service.list(query).subscribe();
        expect(listRequests().length).toBe(1);
      });
    }

    it('should keep the catalog when a change fails', () => {
      loadCatalog();
      service.update(id, payload).subscribe({ error: () => undefined });
      http
        .expectOne(`${TEST_API_URL}/events/${id}`)
        .flush({ message: 'Conflict' }, { status: 409, statusText: 'Conflict' });

      service.list(query).subscribe();
      expect(listRequests().length).toBe(0);
    });
  });
});
