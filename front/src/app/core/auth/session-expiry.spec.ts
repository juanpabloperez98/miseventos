import { HttpClient } from '@angular/common/http';
import { HttpTestingController } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';

import {
  BlankPage,
  cleanUpAuth,
  provideTestDependencies,
  signInAs,
  TEST_API_URL,
  TEST_USERS,
} from '../../../testing/test-helpers';
import { authGuard, eventManagerGuard } from '../guards/auth.guards';
import { FlashMessageService } from '../services/flash-message.service';
import { AuthService } from './auth.service';

describe('SessionExpiryRedirect', () => {
  let harness: RouterTestingHarness;
  let router: Router;
  let http: HttpTestingController;

  beforeEach(async () => {
    TestBed.configureTestingModule({
      providers: provideTestDependencies([
        { path: 'events', component: BlankPage },
        { path: 'events/new', component: BlankPage, canActivate: [eventManagerGuard] },
        { path: 'private', component: BlankPage, canActivate: [authGuard] },
        { path: 'auth/login', component: BlankPage },
      ]),
    });
    harness = await RouterTestingHarness.create();
    router = TestBed.inject(Router);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => cleanUpAuth());

  function rejectTwoConcurrentRequests(): void {
    const client = TestBed.inject(HttpClient);
    client.post(`${TEST_API_URL}/events`, {}).subscribe({ error: () => undefined });
    client.put(`${TEST_API_URL}/events/1`, {}).subscribe({ error: () => undefined });
    for (const request of http.match(() => true)) {
      request.flush(
        { message: 'Invalid or expired token' },
        { status: 401, statusText: 'Unauthorized' },
      );
    }
  }

  it('should send the user from a protected page to login once, with a return URL', async () => {
    signInAs(TEST_USERS.organizer);
    await harness.navigateByUrl('/events/new');
    const navigate = spyOn(router, 'navigate').and.callThrough();

    rejectTwoConcurrentRequests();
    await harness.fixture.whenStable();

    expect(navigate).toHaveBeenCalledTimes(1);
    expect(router.url).toBe('/auth/login?returnUrl=%2Fevents%2Fnew');
    expect(TestBed.inject(FlashMessageService).consume()?.type).toBe('info');
  });

  it('should also leave the page when the token expires on its own', async () => {
    jasmine.clock().install();
    jasmine.clock().mockDate(new Date());
    try {
      signInAs(TEST_USERS.attendee);
      await harness.navigateByUrl('/private');

      jasmine.clock().tick(60 * 60 * 1000 + 1);
      await harness.fixture.whenStable();

      expect(router.url).toBe('/auth/login?returnUrl=%2Fprivate');
    } finally {
      jasmine.clock().uninstall();
    }
  });

  it('should stay on public pages and only update the session state', async () => {
    signInAs(TEST_USERS.attendee);
    await harness.navigateByUrl('/events');

    TestBed.inject(AuthService).handleRejectedToken();
    await harness.fixture.whenStable();

    expect(router.url).toBe('/events');
    expect(TestBed.inject(AuthService).isAuthenticated()).toBeFalse();
    expect(TestBed.inject(FlashMessageService).consume()).toBeNull();
  });

  it('should not redirect on a voluntary logout (the header navigates instead)', async () => {
    signInAs(TEST_USERS.attendee);
    await harness.navigateByUrl('/private');
    const navigate = spyOn(router, 'navigate').and.callThrough();

    TestBed.inject(AuthService).logout();
    await harness.fixture.whenStable();

    expect(navigate).not.toHaveBeenCalled();
  });
});
