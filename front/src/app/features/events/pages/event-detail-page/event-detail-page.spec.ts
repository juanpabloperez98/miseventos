import { HttpTestingController } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';

import { type User } from '../../../../core/auth/auth.models';
import { FlashMessageService } from '../../../../core/services/flash-message.service';
import {
  BlankPage,
  buildEvent,
  buildSession,
  cleanUpAuth,
  provideTestDependencies,
  signInAs,
  TEST_API_URL,
  TEST_USERS,
  textOf,
} from '../../../../../testing/test-helpers';
import { type EventModel } from '../../models/event.model';
import { type EventSession } from '../../models/session.model';
import { EventDetailPage } from './event-detail-page';

describe('EventDetailPage', () => {
  let harness: RouterTestingHarness;
  let http: HttpTestingController;

  const page = () => harness.routeNativeElement as HTMLElement;
  const editLink = () => page().querySelector('a[href="/events/10/edit"]');

  async function open(
    event: EventModel = buildEvent(),
    sessions: EventSession[] = [buildSession()],
    user?: User,
  ): Promise<void> {
    if (user) {
      signInAs(user);
    }
    await harness.navigateByUrl(`/events/${event.id}`, EventDetailPage);
    TestBed.tick();
    http.expectOne(`${TEST_API_URL}/events/${event.id}`).flush(event);
    http.expectOne(`${TEST_API_URL}/events/${event.id}/sessions`).flush(sessions);
    await harness.fixture.whenStable();
  }

  beforeEach(async () => {
    TestBed.configureTestingModule({
      providers: provideTestDependencies([
        { path: 'events', component: BlankPage },
        { path: 'events/:id', component: EventDetailPage },
      ]),
    });
    harness = await RouterTestingHarness.create();
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => cleanUpAuth());

  it('should render the event and its sessions from separate requests', async () => {
    await open(buildEvent(), [
      buildSession({ id: 1, title: 'Apertura' }),
      buildSession({ id: 2, title: 'Signals', description: 'Taller práctico' }),
    ]);

    expect(textOf(page().querySelector('h1'))).toBe('Angular Summit');
    expect(textOf(page().querySelector('.facts'))).toContain('Medellín');
    expect(textOf(page().querySelector('.facts'))).toContain('120 personas');
    expect(textOf(page().querySelector('app-event-status-badge'))).toBe('Publicado');
    const sessions = page().querySelectorAll('.session');
    expect(sessions.length).toBe(2);
    expect(textOf(sessions[1])).toContain('Taller práctico');
    expect(page().querySelector('a[href="/events"]')).not.toBeNull();
  });

  it('should show an empty state when the event has no sessions', async () => {
    await open(buildEvent(), []);
    expect(textOf(page().querySelector('.sessions app-empty-state'))).toContain(
      'Sin sesiones programadas',
    );
  });

  it('should show a not found state for hidden or missing events', async () => {
    await harness.navigateByUrl('/events/99', EventDetailPage);
    TestBed.tick();
    http
      .expectOne(`${TEST_API_URL}/events/99`)
      .flush({ message: 'Event not found' }, { status: 404, statusText: 'Not Found' });
    http
      .expectOne(`${TEST_API_URL}/events/99/sessions`)
      .flush({ message: 'Event not found' }, { status: 404, statusText: 'Not Found' });
    await harness.fixture.whenStable();

    expect(textOf(page().querySelector('app-empty-state'))).toContain('Evento no encontrado');
  });

  describe('management actions', () => {
    it('should be hidden for anonymous users and attendees', async () => {
      await open(buildEvent(), [], TEST_USERS.attendee);
      expect(editLink()).toBeNull();
      expect(page().querySelector('.event__actions')).toBeNull();
    });

    it('should be shown to the organizer who owns the event', async () => {
      await open(buildEvent(), [], TEST_USERS.organizer);
      expect(editLink()).not.toBeNull();
      expect(textOf(page().querySelector('.event__actions'))).toContain('Cancelar evento');
    });

    it('should be hidden for an organizer who does not own the event', async () => {
      await open(buildEvent(), [], TEST_USERS.otherOrganizer);
      expect(editLink()).toBeNull();
    });

    it('should be shown to ADMIN for any event', async () => {
      await open(buildEvent({ created_by: 999 }), [], TEST_USERS.admin);
      expect(editLink()).not.toBeNull();
    });

    it('should not offer editing for final events', async () => {
      await open(buildEvent({ status: 'COMPLETED' }), [], TEST_USERS.admin);
      expect(editLink()).toBeNull();
      expect(page().querySelector('.event__actions')).toBeNull();
    });
  });

  it('should delete a draft after confirmation and go back to the list', async () => {
    await open(buildEvent({ status: 'DRAFT' }), [], TEST_USERS.organizer);

    page().querySelector<HTMLButtonElement>('.event__actions button')?.click();
    await harness.fixture.whenStable();
    page().querySelector<HTMLButtonElement>('.confirm button.btn--danger')?.click();

    const request = http.expectOne(`${TEST_API_URL}/events/10`);
    expect(request.request.method).toBe('DELETE');
    request.flush(null, { status: 204, statusText: 'No Content' });
    await harness.fixture.whenStable();

    expect(TestBed.inject(Router).url).toBe('/events');
    expect(TestBed.inject(FlashMessageService).consume()?.type).toBe('success');
  });

  it('should show the cancelled event returned by the API', async () => {
    await open(buildEvent(), [], TEST_USERS.organizer);

    page().querySelector<HTMLButtonElement>('.event__actions button')?.click();
    await harness.fixture.whenStable();
    page().querySelector<HTMLButtonElement>('.confirm button.btn--danger')?.click();
    http.expectOne(`${TEST_API_URL}/events/10`).flush(buildEvent({ status: 'CANCELLED' }));
    await harness.fixture.whenStable();

    expect(textOf(page().querySelector('app-event-status-badge'))).toBe('Cancelado');
    expect(textOf(page().querySelector('app-alert'))).toContain('cancelado');
    expect(editLink()).toBeNull();
  });
});
