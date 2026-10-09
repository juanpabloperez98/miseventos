import { HttpTestingController } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import {
  cleanUpAuth,
  provideTestDependencies,
  signInAs,
  TEST_API_URL,
  TEST_USERS,
} from '../../../../testing/test-helpers';
import { type Speaker } from '../models/speaker.model';
import { SPEAKERS_CACHE_TTL_MS, SpeakersService } from './speakers.service';

const SPEAKERS: Speaker[] = [{ id: 1, name: 'Ada Lovelace', bio: null }];

describe('SpeakersService', () => {
  let service: SpeakersService;
  let http: HttpTestingController;

  const speakerRequests = () => http.match((req) => req.url === `${TEST_API_URL}/speakers`);
  const flushSpeakers = () =>
    speakerRequests()[0].flush({ items: SPEAKERS, total: 1, page: 1, per_page: 100, pages: 1 });

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: provideTestDependencies() });
    service = TestBed.inject(SpeakersService);
    http = TestBed.inject(HttpTestingController);
    jasmine.clock().install();
    jasmine.clock().mockDate(new Date('2030-05-10T15:00:00Z'));
  });

  afterEach(() => {
    jasmine.clock().uninstall();
    cleanUpAuth();
  });

  it('should request every page once and reuse the list for 60 seconds', () => {
    service.listAll().subscribe();
    const [first] = speakerRequests();
    expect(first.request.params.get('per_page')).toBe('100');
    first.flush({ items: SPEAKERS, total: 101, page: 1, per_page: 100, pages: 2 });
    const second = speakerRequests();
    expect(second.length).toBe(1);
    second[0].flush({ items: [], total: 101, page: 2, per_page: 100, pages: 2 });

    jasmine.clock().tick(SPEAKERS_CACHE_TTL_MS - 1);
    let reused: Speaker[] = [];
    service.listAll().subscribe((speakers) => (reused = speakers));
    expect(reused).toEqual(SPEAKERS);
    expect(speakerRequests().length).toBe(0);

    jasmine.clock().tick(1);
    service.listAll().subscribe();
    expect(speakerRequests().length).toBe(1);
  });

  it('should retry after a failed request instead of keeping the error', () => {
    service.listAll().subscribe({ error: () => undefined });
    speakerRequests()[0].flush(null, { status: 503, statusText: 'Unavailable' });

    let speakers: Speaker[] = [];
    service.listAll().subscribe((received) => (speakers = received));
    flushSpeakers();
    expect(speakers).toEqual(SPEAKERS);
  });

  it('should not share the list between sessions', () => {
    service.listAll().subscribe();
    flushSpeakers();
    signInAs(TEST_USERS.organizer);

    service.listAll().subscribe();
    expect(speakerRequests().length).toBe(1);
  });
});
