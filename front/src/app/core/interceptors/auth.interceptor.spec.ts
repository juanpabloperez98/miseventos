import { HttpClient } from '@angular/common/http';
import { HttpTestingController } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import {
  cleanUpAuth,
  provideTestDependencies,
  signInAs,
  TEST_API_URL,
  TEST_USERS,
} from '../../../testing/test-helpers';
import { AuthService } from '../auth/auth.service';

describe('authInterceptor', () => {
  let http: HttpClient;
  let backend: HttpTestingController;
  let auth: AuthService;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: provideTestDependencies() });
    http = TestBed.inject(HttpClient);
    backend = TestBed.inject(HttpTestingController);
    auth = TestBed.inject(AuthService);
    signInAs(TEST_USERS.organizer);
  });

  afterEach(() => cleanUpAuth());

  it('should add the bearer token to API requests', () => {
    http.get(`${TEST_API_URL}/events`).subscribe();

    const request = backend.expectOne(`${TEST_API_URL}/events`);
    expect(request.request.headers.get('Authorization')).toBe('Bearer token-2');
    request.flush({});
  });

  it('should never send the token to other domains', () => {
    http.get('https://cdn.example.com/data.json').subscribe();
    http.get('http://api.test/apix/events').subscribe();

    expect(
      backend.expectOne('https://cdn.example.com/data.json').request.headers.has('Authorization'),
    ).toBeFalse();
    expect(
      backend.expectOne('http://api.test/apix/events').request.headers.has('Authorization'),
    ).toBeFalse();
  });

  it('should end the session and retry public reads anonymously on 401', () => {
    let body: unknown;
    http.get(`${TEST_API_URL}/events`).subscribe((response) => (body = response));

    backend
      .expectOne((req) => req.headers.has('Authorization'))
      .flush({ message: 'Invalid or expired token' }, { status: 401, statusText: 'Unauthorized' });
    backend.expectOne((req) => !req.headers.has('Authorization')).flush({ items: [] });

    expect(auth.isAuthenticated()).toBeFalse();
    expect(body).toEqual({ items: [] });
  });

  it('should not retry mutations after a 401', () => {
    let status = 0;
    http
      .post(`${TEST_API_URL}/events`, {})
      .subscribe({ error: (error) => (status = error.status) });

    backend
      .expectOne(`${TEST_API_URL}/events`)
      .flush({ message: 'Invalid or expired token' }, { status: 401, statusText: 'Unauthorized' });

    expect(status).toBe(401);
    expect(auth.isAuthenticated()).toBeFalse();
  });

  it('should keep the session on 403', () => {
    let status = 0;
    http
      .post(`${TEST_API_URL}/events`, {})
      .subscribe({ error: (error) => (status = error.status) });

    backend
      .expectOne(`${TEST_API_URL}/events`)
      .flush({ message: 'Forbidden' }, { status: 403, statusText: 'Forbidden' });

    expect(status).toBe(403);
    expect(auth.isAuthenticated()).toBeTrue();
  });
});
