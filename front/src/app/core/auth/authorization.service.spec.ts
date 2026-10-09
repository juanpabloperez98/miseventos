import { TestBed } from '@angular/core/testing';

import {
  cleanUpAuth,
  provideTestDependencies,
  signInAs,
  TEST_USERS,
} from '../../../testing/test-helpers';
import { AuthorizationService } from './authorization.service';

describe('AuthorizationService', () => {
  let authorization: AuthorizationService;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: provideTestDependencies() });
    authorization = TestBed.inject(AuthorizationService);
  });

  afterEach(() => cleanUpAuth());

  describe('canCreateEvents', () => {
    it('should be false for anonymous users', () => {
      expect(authorization.canCreateEvents()).toBeFalse();
    });

    it('should be true for ADMIN', () => {
      signInAs(TEST_USERS.admin);
      expect(authorization.canCreateEvents()).toBeTrue();
    });

    it('should be true for ORGANIZER', () => {
      signInAs(TEST_USERS.organizer);
      expect(authorization.canCreateEvents()).toBeTrue();
    });

    it('should be false for ATTENDEE', () => {
      signInAs(TEST_USERS.attendee);
      expect(authorization.canCreateEvents()).toBeFalse();
    });
  });

  describe('canManageEvent', () => {
    const ownerId = TEST_USERS.organizer.id;

    it('should let ADMIN manage any event', () => {
      signInAs(TEST_USERS.admin);
      expect(authorization.canManageEvent(ownerId)).toBeTrue();
    });

    it('should let an ORGANIZER manage only their own events', () => {
      signInAs(TEST_USERS.organizer);
      expect(authorization.canManageEvent(ownerId)).toBeTrue();
      expect(authorization.canManageEvent(TEST_USERS.otherOrganizer.id)).toBeFalse();
    });

    it('should never let ATTENDEE or anonymous users manage events', () => {
      expect(authorization.canManageEvent(ownerId)).toBeFalse();
      signInAs({ ...TEST_USERS.attendee, id: ownerId });
      expect(authorization.canManageEvent(ownerId)).toBeFalse();
    });
  });
});
