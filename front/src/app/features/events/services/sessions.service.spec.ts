import { HttpTestingController } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import {
  buildSession,
  cleanUpAuth,
  provideTestDependencies,
  signInAs,
  TEST_API_URL,
  TEST_USERS,
} from '../../../../testing/test-helpers';
import { type SessionPayload } from '../models/session.model';
import { SessionsService } from './sessions.service';
import { SpeakersService } from './speakers.service';

const PAYLOAD: SessionPayload = {
  title: 'Signals',
  description: null,
  start_time: '2030-05-10T15:00:00.000Z',
  end_time: '2030-05-10T16:00:00.000Z',
  capacity: 50,
  speaker_id: 2,
};

describe('SessionsService', () => {
  let service: SessionsService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: provideTestDependencies() });
    service = TestBed.inject(SessionsService);
    http = TestBed.inject(HttpTestingController);
    signInAs(TEST_USERS.organizer);
  });

  afterEach(() => cleanUpAuth());

  it('should read a session', () => {
    service.get(100).subscribe();
    const request = http.expectOne(`${TEST_API_URL}/sessions/100`);
    expect(request.request.method).toBe('GET');
    request.flush(buildSession());
  });

  it('should create a session in the event with the bearer token', () => {
    service.create(10, PAYLOAD).subscribe();

    const request = http.expectOne(`${TEST_API_URL}/events/10/sessions`);
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual(PAYLOAD);
    expect(request.request.headers.has('Authorization')).toBeTrue();
    request.flush(buildSession(), { status: 201, statusText: 'Created' });
  });

  it('should replace a session with PUT', () => {
    service.update(100, { ...PAYLOAD, speaker_id: null }).subscribe();

    const request = http.expectOne(`${TEST_API_URL}/sessions/100`);
    expect(request.request.method).toBe('PUT');
    expect(request.request.body.speaker_id).toBeNull();
    request.flush(buildSession());
  });

  it('should delete a session (204)', () => {
    let done = false;
    service.remove(100).subscribe(() => (done = true));

    const request = http.expectOne(`${TEST_API_URL}/sessions/100`);
    expect(request.request.method).toBe('DELETE');
    request.flush(null, { status: 204, statusText: 'No Content' });

    expect(done).toBeTrue();
  });
});

describe('SpeakersService', () => {
  let service: SpeakersService;
  let http: HttpTestingController;

  const speaker = (id: number) => ({ id, name: `Speaker ${id}`, bio: null });
  const pageOf = (ids: number[], page: number, pages: number) => ({
    items: ids.map(speaker),
    total: 0,
    page,
    per_page: 100,
    pages,
  });

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: provideTestDependencies() });
    service = TestBed.inject(SpeakersService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => cleanUpAuth());

  it('should load the catalog with a single request when it fits in one page', () => {
    let names: string[] = [];
    service.listAll().subscribe((list) => (names = list.map((item) => item.name)));

    const request = http.expectOne((req) => req.url === `${TEST_API_URL}/speakers`);
    expect(request.request.params.get('page')).toBe('1');
    expect(request.request.params.get('per_page')).toBe('100');
    request.flush(pageOf([1, 2], 1, 1));

    expect(names).toEqual(['Speaker 1', 'Speaker 2']);
  });

  it('should request the remaining pages when there are more than 100 speakers', () => {
    let ids: number[] = [];
    service.listAll().subscribe((list) => (ids = list.map((item) => item.id)));

    http.expectOne((req) => req.params.get('page') === '1').flush(pageOf([1], 1, 3));
    http.expectOne((req) => req.params.get('page') === '2').flush(pageOf([2], 2, 3));
    http.expectOne((req) => req.params.get('page') === '3').flush(pageOf([3], 3, 3));

    expect(ids).toEqual([1, 2, 3]);
  });
});
