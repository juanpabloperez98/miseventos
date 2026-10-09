import { HttpTestingController } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';

import { type User } from '../../../../core/auth/auth.models';
import { FlashMessageService } from '../../../../core/services/flash-message.service';
import {
  BlankPage,
  buildEvent,
  cleanUpAuth,
  provideTestDependencies,
  signInAs,
  TEST_API_URL,
  TEST_USERS,
  textOf,
} from '../../../../../testing/test-helpers';
import { type EventModel } from '../../models/event.model';
import { EventEditPage } from './event-edit-page';

describe('EventEditPage', () => {
  let harness: RouterTestingHarness;
  let http: HttpTestingController;

  const page = () => harness.routeNativeElement as HTMLElement;

  async function open(user: User, event: EventModel = buildEvent()): Promise<void> {
    signInAs(user);
    await harness.navigateByUrl(`/events/${event.id}/edit`, EventEditPage);
    TestBed.tick();
    http.expectOne(`${TEST_API_URL}/events/${event.id}`).flush(event);
    await harness.fixture.whenStable();
  }

  async function submit(): Promise<void> {
    page().querySelector<HTMLButtonElement>('button[type="submit"]')?.click();
    await harness.fixture.whenStable();
  }

  beforeEach(async () => {
    TestBed.configureTestingModule({
      providers: provideTestDependencies([
        { path: 'events/:id', component: BlankPage },
        { path: 'events/:id/edit', component: EventEditPage },
      ]),
    });
    harness = await RouterTestingHarness.create();
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => cleanUpAuth());

  it('should not show the form to an organizer who does not own the event', async () => {
    await open(TEST_USERS.otherOrganizer);

    expect(page().querySelector('app-event-form')).toBeNull();
    expect(textOf(page().querySelector('app-error-state'))).toContain(
      'No puedes editar este evento',
    );
  });

  it('should not show the form for final events', async () => {
    await open(TEST_USERS.admin, buildEvent({ status: 'CANCELLED' }));
    expect(page().querySelector('app-event-form')).toBeNull();
  });

  it('should save with PUT and go back to the detail with a confirmation', async () => {
    await open(TEST_USERS.organizer);
    await submit();

    const request = http.expectOne(`${TEST_API_URL}/events/10`);
    expect(request.request.method).toBe('PUT');
    expect(request.request.body.name).toBe('Angular Summit');
    expect('status' in request.request.body).toBeFalse();
    request.flush(buildEvent());
    await harness.fixture.whenStable();

    expect(TestBed.inject(Router).url).toBe('/events/10');
    expect(TestBed.inject(FlashMessageService).consume()?.type).toBe('success');
  });

  it('should show conflicts returned by the backend and allow retrying', async () => {
    await open(TEST_USERS.organizer);
    await submit();

    http
      .expectOne(`${TEST_API_URL}/events/10`)
      .flush(
        { message: 'Capacity cannot be lower than the number of registered attendees' },
        { status: 409, statusText: 'Conflict' },
      );
    await harness.fixture.whenStable();

    expect(textOf(page().querySelector('app-alert'))).toBe(
      'La capacidad no puede ser menor que el número de personas inscritas.',
    );
    expect(page().querySelector<HTMLButtonElement>('button[type="submit"]')?.disabled).toBeFalse();
  });
});
