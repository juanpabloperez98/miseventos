import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';

import {
  BlankPage,
  cleanUpAuth,
  provideTestDependencies,
  signInAs,
  TEST_USERS,
} from '../../../testing/test-helpers';
import { FlashMessageService } from '../services/flash-message.service';
import { authGuard, eventManagerGuard, guestGuard } from './auth.guards';

describe('auth guards', () => {
  let harness: RouterTestingHarness;
  let router: Router;

  beforeEach(async () => {
    TestBed.configureTestingModule({
      providers: provideTestDependencies([
        { path: 'events', component: BlankPage },
        { path: 'events/new', component: BlankPage, canActivate: [eventManagerGuard] },
        { path: 'private', component: BlankPage, canActivate: [authGuard] },
        { path: 'auth/login', component: BlankPage, canActivate: [guestGuard] },
      ]),
    });
    harness = await RouterTestingHarness.create();
    router = TestBed.inject(Router);
  });

  afterEach(() => cleanUpAuth());

  it('should send anonymous users to login with a return URL', async () => {
    await harness.navigateByUrl('/private');
    expect(router.url).toBe('/auth/login?returnUrl=%2Fprivate');
  });

  it('should send anonymous users trying to create events to login', async () => {
    await harness.navigateByUrl('/events/new');
    expect(router.url).toBe('/auth/login?returnUrl=%2Fevents%2Fnew');
  });

  it('should keep ATTENDEE out of the event creation route', async () => {
    signInAs(TEST_USERS.attendee);

    await harness.navigateByUrl('/events/new');

    expect(router.url).toBe('/events');
    expect(TestBed.inject(FlashMessageService).consume()?.type).toBe('error');
  });

  for (const role of ['admin', 'organizer'] as const) {
    it(`should let ${role.toUpperCase()} open the event creation route`, async () => {
      signInAs(TEST_USERS[role]);
      await harness.navigateByUrl('/events/new');
      expect(router.url).toBe('/events/new');
    });
  }

  it('should send authenticated users away from the login page', async () => {
    signInAs(TEST_USERS.attendee);
    await harness.navigateByUrl('/auth/login');
    expect(router.url).toBe('/events');
  });
});
