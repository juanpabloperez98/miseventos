import { HttpTestingController } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { firstValueFrom } from 'rxjs';

import {
  cleanUpAuth,
  provideTestDependencies,
  signInAs,
  TEST_API_URL,
  TEST_USERS,
} from '../../../testing/test-helpers';
import { FlashMessageService } from '../services/flash-message.service';
import { AuthService, type SessionEndReason } from './auth.service';
import { TokenStorage } from './token-storage';

describe('AuthService', () => {
  let auth: AuthService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: provideTestDependencies() });
    auth = TestBed.inject(AuthService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => cleanUpAuth());

  it('should start anonymous', () => {
    expect(auth.user()).toBeNull();
    expect(auth.isAuthenticated()).toBeFalse();
    expect(auth.accessToken()).toBeNull();
  });

  it('should store the token and load the current user on login', () => {
    signInAs(TEST_USERS.organizer);

    expect(auth.user()).toEqual(TEST_USERS.organizer);
    expect(auth.isAuthenticated()).toBeTrue();
    expect(auth.accessToken()).toBe(`token-${TEST_USERS.organizer.id}`);
  });

  it('should send credentials without bearer token and keep the session anonymous on 401', () => {
    let failed = false;
    auth.login({ email: 'x@test.dev', password: 'wrong-password' }).subscribe({
      error: () => (failed = true),
    });

    const request = http.expectOne(`${TEST_API_URL}/auth/login`);
    expect(request.request.headers.has('Authorization')).toBeFalse();
    request.flush(
      { message: 'Invalid email or password' },
      { status: 401, statusText: 'Unauthorized' },
    );

    expect(failed).toBeTrue();
    expect(auth.isAuthenticated()).toBeFalse();
    expect(auth.accessToken()).toBeNull();
  });

  it('should clear the session on logout', () => {
    signInAs(TEST_USERS.admin);

    auth.logout();

    expect(auth.user()).toBeNull();
    expect(TestBed.inject(TokenStorage).read()).toBeNull();
  });

  it('should register through the public endpoint without a role', () => {
    auth.register({ name: 'Ana', email: 'ana@test.dev', password: 'password123' }).subscribe();

    const request = http.expectOne(`${TEST_API_URL}/auth/register`);
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual({
      name: 'Ana',
      email: 'ana@test.dev',
      password: 'password123',
    });
    request.flush(TEST_USERS.attendee, { status: 201, statusText: 'Created' });
  });

  describe('restoreSession', () => {
    beforeEach(() => {
      TestBed.inject(TokenStorage).save({
        access_token: 'stored-token',
        token_type: 'Bearer',
        expires_at: new Date(Date.now() + 60_000).toISOString(),
      });
    });

    it('should load the user of a stored token', async () => {
      const restored = firstValueFrom(auth.restoreSession());

      const request = http.expectOne(`${TEST_API_URL}/auth/me`);
      expect(request.request.headers.get('Authorization')).toBe('Bearer stored-token');
      request.flush(TEST_USERS.attendee);
      await restored;

      expect(auth.user()).toEqual(TEST_USERS.attendee);
    });

    it('should drop a token rejected by the API', async () => {
      const restored = firstValueFrom(auth.restoreSession());

      http
        .expectOne((req) => req.headers.has('Authorization'))
        .flush(
          { message: 'Invalid or expired token' },
          { status: 401, statusText: 'Unauthorized' },
        );
      // The interceptor retries the GET anonymously; the endpoint still requires a token.
      http
        .expectOne((req) => !req.headers.has('Authorization'))
        .flush({ message: 'Missing bearer token' }, { status: 401, statusText: 'Unauthorized' });
      await restored;

      expect(auth.user()).toBeNull();
      expect(TestBed.inject(TokenStorage).read()).toBeNull();
    });

    it('should keep the token when the backend is unreachable', async () => {
      const restored = firstValueFrom(auth.restoreSession());

      http.expectOne(`${TEST_API_URL}/auth/me`).error(new ProgressEvent('error'));
      await restored;

      expect(auth.user()).toBeNull();
      expect(TestBed.inject(TokenStorage).read()?.value).toBe('stored-token');
    });
  });

  describe('session end', () => {
    let reasons: SessionEndReason[];

    beforeEach(() => {
      reasons = [];
      auth.sessionEnded$.subscribe((reason) => reasons.push(reason));
    });

    it('should end the session when the token reaches its expiry time', () => {
      jasmine.clock().install();
      jasmine.clock().mockDate(new Date());
      try {
        signInAs(TEST_USERS.organizer);
        jasmine.clock().tick(60 * 60 * 1000 - 1000);
        expect(auth.isAuthenticated()).toBeTrue();

        jasmine.clock().tick(2000);

        expect(auth.user()).toBeNull();
        expect(auth.accessToken()).toBeNull();
        expect(reasons).toEqual(['expired']);
      } finally {
        jasmine.clock().uninstall();
      }
    });

    it('should notify a rejected session only once for concurrent 401 responses', () => {
      signInAs(TEST_USERS.attendee);

      auth.handleRejectedToken();
      auth.handleRejectedToken();
      auth.handleRejectedToken();

      expect(reasons).toEqual(['rejected']);
      expect(auth.isAuthenticated()).toBeFalse();
    });

    it('should report a logout and drop flash messages meant for the previous user', () => {
      signInAs(TEST_USERS.attendee);
      TestBed.inject(FlashMessageService).set('success', '¡Te damos la bienvenida, Ana!');

      auth.logout();

      expect(reasons).toEqual(['logout']);
      expect(TestBed.inject(FlashMessageService).consume()).toBeNull();
    });

    it('should not notify anything when there was no session', () => {
      auth.logout();
      auth.handleRejectedToken();

      expect(reasons).toEqual([]);
    });

    it('should start a clean session for the next account', () => {
      signInAs(TEST_USERS.organizer);
      auth.logout();

      signInAs(TEST_USERS.attendee);

      expect(auth.user()).toEqual(TEST_USERS.attendee);
      expect(auth.accessToken()).toBe(`token-${TEST_USERS.attendee.id}`);
    });
  });

  it('should ignore expired tokens', () => {
    TestBed.inject(TokenStorage).save({
      access_token: 'old-token',
      token_type: 'Bearer',
      expires_at: new Date(Date.now() - 1000).toISOString(),
    });

    expect(auth.accessToken()).toBeNull();
  });
});
