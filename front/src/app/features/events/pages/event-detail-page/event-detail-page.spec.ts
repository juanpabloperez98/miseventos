import { HttpTestingController } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';

import { type User } from '../../../../core/auth/auth.models';
import { AuthService } from '../../../../core/auth/auth.service';
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
    myEvents: EventModel[] = [],
  ): Promise<void> {
    if (user) {
      signInAs(user);
    }
    await harness.navigateByUrl(`/events/${event.id}`, EventDetailPage);
    TestBed.tick();
    http.expectOne(`${TEST_API_URL}/events/${event.id}`).flush(event);
    http.expectOne(`${TEST_API_URL}/events/${event.id}/sessions`).flush(sessions);
    if (user) {
      // Signed-in users: membership check for the registration panel.
      http.expectOne(`${TEST_API_URL}/me/registrations`).flush(myEvents);
    }
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

  it('should show the event and session schedules as dd/MM/yyyy and AM/PM in Colombia time', async () => {
    await open(
      // 9:00 AM on May 10 to 11:30 PM on May 10 in Bogotá (the end is May 11 in UTC).
      buildEvent({
        start_date: '2030-05-10T14:00:00+00:00',
        end_date: '2030-05-11T04:30:00+00:00',
      }),
      [
        buildSession({
          id: 1,
          start_time: '2030-05-10T15:00:00+00:00',
          end_time: '2030-05-10T16:30:00+00:00',
        }),
        buildSession({
          id: 2,
          start_time: '2030-05-11T03:00:00+00:00',
          end_time: '2030-05-11T04:30:00+00:00',
        }),
      ],
    );

    expect(textOf(page().querySelector('.facts'))).toContain('10/05/2030 · 9:00 AM – 11:30 PM');
    const times = [...page().querySelectorAll('.session__time')].map((time) => textOf(time));
    expect(times).toEqual(['10/05/2030 · 10:00 AM – 11:30 AM', '10/05/2030 · 10:00 PM – 11:30 PM']);
    expect(page().querySelector('.session__time time')?.getAttribute('datetime')).toBe(
      '2030-05-10T15:00:00+00:00',
    );
  });

  it('should show a loading state until the event arrives', async () => {
    await harness.navigateByUrl('/events/10', EventDetailPage);
    TestBed.tick();

    expect(textOf(page().querySelector('app-loading'))).toContain('Cargando evento');

    http.expectOne(`${TEST_API_URL}/events/10`).flush(buildEvent());
    http.expectOne(`${TEST_API_URL}/events/10/sessions`).flush([]);
    await harness.fixture.whenStable();

    expect(page().querySelector('app-loading')).toBeNull();
    expect(textOf(page().querySelector('h1'))).toBe('Angular Summit');
  });

  it('should reset the removal confirmation and notice when another event is shown', async () => {
    TestBed.inject(FlashMessageService).set('success', 'Evento creado como borrador.');
    await open(buildEvent({ status: 'DRAFT' }), [], TEST_USERS.organizer);
    expect(textOf(page().querySelector('app-alert'))).toContain('Evento creado');

    page().querySelector<HTMLButtonElement>('.event__actions button')?.click();
    await harness.fixture.whenStable();
    expect(page().querySelector('.confirm')).not.toBeNull();

    await harness.navigateByUrl('/events/11', EventDetailPage);
    TestBed.tick();
    http.expectOne(`${TEST_API_URL}/events/11`).flush(buildEvent({ id: 11, status: 'DRAFT' }));
    http.expectOne(`${TEST_API_URL}/events/11/sessions`).flush([]);
    http.expectOne(`${TEST_API_URL}/me/registrations`).flush([]);
    await harness.fixture.whenStable();

    expect(page().querySelector('.confirm')).toBeNull();
    expect(page().querySelector('app-alert')).toBeNull();
  });

  it('should show the event of the current URL and never the previous one while loading', async () => {
    await open(buildEvent({ id: 10, name: 'Angular Summit' }), [
      buildSession({ title: 'Signals' }),
    ]);
    expect(textOf(page().querySelector('h1'))).toBe('Angular Summit');

    await harness.navigateByUrl('/events/11', EventDetailPage);
    TestBed.tick();
    await harness.fixture.whenStable();

    // While event 11 loads, nothing from event 10 is displayed.
    expect(page().querySelector('app-loading')).not.toBeNull();
    expect(textOf(page())).not.toContain('Angular Summit');
    expect(textOf(page())).not.toContain('Signals');

    http.expectOne(`${TEST_API_URL}/events/11`).flush(buildEvent({ id: 11, name: 'PyCon' }));
    http.expectOne(`${TEST_API_URL}/events/11/sessions`).flush([]);
    await harness.fixture.whenStable();

    expect(textOf(page().querySelector('h1'))).toBe('PyCon');
  });

  it('should reload anonymously after logout and hide a private draft of the previous user', async () => {
    await open(buildEvent({ status: 'DRAFT', name: 'Borrador privado' }), [], TEST_USERS.organizer);
    expect(textOf(page().querySelector('h1'))).toBe('Borrador privado');

    TestBed.inject(AuthService).logout();
    await harness.fixture.whenStable();

    expect(textOf(page())).not.toContain('Borrador privado');
    expect(page().querySelector('.event__actions')).toBeNull();
    const event = http.expectOne(`${TEST_API_URL}/events/10`);
    expect(event.request.headers.has('Authorization')).toBeFalse();
    event.flush({ message: 'Event not found' }, { status: 404, statusText: 'Not Found' });
    http
      .expectOne(`${TEST_API_URL}/events/10/sessions`)
      .flush({ message: 'Event not found' }, { status: 404, statusText: 'Not Found' });
    await harness.fixture.whenStable();

    expect(textOf(page().querySelector('app-empty-state'))).toContain('Evento no encontrado');
    expect(textOf(page())).not.toContain('Borrador privado');
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

  describe('registration', () => {
    const panel = () => page().querySelector('app-registration-panel') as HTMLElement;
    const registerButton = () =>
      [...panel().querySelectorAll<HTMLButtonElement>('button')].find(
        (button) => textOf(button) === 'Inscribirme',
      );
    const registrationRequest = () => http.expectOne(`${TEST_API_URL}/events/10/registrations`);
    const conflict = (message: string) =>
      [{ message }, { status: 409, statusText: 'Conflict' }] as const;

    it('should invite anonymous users to sign in and come back to the event', async () => {
      await open(buildEvent(), []);

      const link = panel().querySelector('a');
      expect(link?.getAttribute('href')).toBe('/auth/login?returnUrl=%2Fevents%2F10');
      expect(registerButton()).toBeUndefined();
      http.expectNone(`${TEST_API_URL}/me/registrations`);
    });

    it('should register once and show the confirmation without reloading the list', async () => {
      await open(buildEvent(), [], TEST_USERS.attendee);

      registerButton()?.click();
      registerButton()?.click();
      await harness.fixture.whenStable();

      const request = registrationRequest();
      expect(request.request.method).toBe('POST');
      expect(request.request.body).toBeNull();
      expect(panel().querySelector('button')?.disabled).toBeTrue();
      request.flush(
        { id: 3, event_id: 10, user_id: 4, registered_at: '2030-01-01T10:00:00+00:00' },
        { status: 201, statusText: 'Created' },
      );
      await harness.fixture.whenStable();

      expect(textOf(panel())).toContain('Estás inscrito en este evento');
      expect(panel().querySelector('a[href="/profile"]')).not.toBeNull();
      expect(registerButton()).toBeUndefined();
      expect(textOf(page().querySelector('app-alert'))).toBe('Te has inscrito en el evento.');
      // No extra GET /me/registrations: verified by HttpTestingController in afterEach.
    });

    it('should show users already registered as such, without the button', async () => {
      await open(buildEvent(), [], TEST_USERS.attendee, [buildEvent()]);

      expect(textOf(panel())).toContain('Estás inscrito en este evento');
      expect(registerButton()).toBeUndefined();
    });

    it('should treat a duplicate registration (409) as already registered', async () => {
      await open(buildEvent(), [], TEST_USERS.attendee);

      registerButton()?.click();
      registrationRequest().flush(...conflict('User is already registered to this event'));
      await harness.fixture.whenStable();

      expect(textOf(panel())).toContain('Estás inscrito en este evento');
      expect(textOf(page().querySelector('app-alert'))).toBe('Ya estabas inscrito en este evento.');
    });

    it('should explain a full event (409) and let the user try again', async () => {
      await open(buildEvent(), [], TEST_USERS.attendee);

      registerButton()?.click();
      registrationRequest().flush(...conflict('Event has reached its capacity'));
      await harness.fixture.whenStable();

      expect(textOf(panel().querySelector('app-alert'))).toBe(
        'El evento ha alcanzado su capacidad máxima.',
      );
      expect(registerButton()?.disabled).toBeFalse();
    });

    it('should report an event that is no longer visible (404)', async () => {
      await open(buildEvent(), [], TEST_USERS.attendee);

      registerButton()?.click();
      registrationRequest().flush(
        { message: 'Event not found' },
        { status: 404, statusText: 'Not Found' },
      );
      await harness.fixture.whenStable();

      expect(textOf(panel().querySelector('app-alert'))).toBe(
        'El evento no existe o no está disponible.',
      );
    });

    it('should fall back to the sign-in invitation when the session was rejected (401)', async () => {
      await open(buildEvent(), [], TEST_USERS.attendee);

      registerButton()?.click();
      registrationRequest().flush(
        { message: 'Invalid or expired token' },
        { status: 401, statusText: 'Unauthorized' },
      );
      await harness.fixture.whenStable();
      // The page reloads the event and its sessions for the anonymous user.
      http.expectOne(`${TEST_API_URL}/events/10`).flush(buildEvent());
      http.expectOne(`${TEST_API_URL}/events/10/sessions`).flush([]);
      await harness.fixture.whenStable();

      expect(TestBed.inject(AuthService).isAuthenticated()).toBeFalse();
      expect(panel().querySelector('a')?.getAttribute('href')).toBe(
        '/auth/login?returnUrl=%2Fevents%2F10',
      );
    });

    it('should not offer registration for events that are not published', async () => {
      await open(buildEvent({ status: 'DRAFT' }), [], TEST_USERS.organizer);

      expect(textOf(panel())).toContain('Este evento no admite inscripciones');
      expect(registerButton()).toBeUndefined();
    });

    it('should keep the button available if the membership check fails', async () => {
      signInAs(TEST_USERS.attendee);
      await harness.navigateByUrl('/events/10', EventDetailPage);
      TestBed.tick();
      http.expectOne(`${TEST_API_URL}/events/10`).flush(buildEvent());
      http.expectOne(`${TEST_API_URL}/events/10/sessions`).flush([]);
      http
        .expectOne(`${TEST_API_URL}/me/registrations`)
        .flush({ message: 'Internal server error' }, { status: 500, statusText: 'Error' });
      await harness.fixture.whenStable();

      expect(registerButton()?.disabled).toBeFalse();
    });
  });

  describe('sessions', () => {
    const sessionItems = () => page().querySelectorAll('.session');
    const buttonIn = (root: Element, text: string) =>
      [...root.querySelectorAll<HTMLButtonElement>('button')].find(
        (button) => textOf(button) === text,
      );

    it('should show the speaker name from the API, or "Sin asignar" without a speaker', async () => {
      await open(buildEvent(), [
        buildSession({ id: 1, speaker_id: 3, speaker_name: 'Andrés Rojas' }),
        buildSession({ id: 2 }),
      ]);

      const speakers = [...sessionItems()].map((item) => item.querySelector('.session__speaker'));
      expect(textOf(speakers[0])).toBe('Ponente: Andrés Rojas');
      expect(speakers[0]?.classList).not.toContain('session__speaker--none');
      expect(textOf(speakers[1])).toBe('Ponente: Sin asignar');
      expect(speakers[1]?.classList).toContain('session__speaker--none');
      // Never a bare id, and no extra request to resolve names.
      expect(textOf(sessionItems()[0])).not.toContain('Ponente: 3');
      http.expectNone((req) => req.url.startsWith(`${TEST_API_URL}/speakers`));
    });

    it('should keep the order: schedule, title, speaker, description, capacity', async () => {
      await open(buildEvent(), [
        buildSession({ speaker_id: 3, speaker_name: 'Andrés Rojas', description: 'Taller' }),
      ]);

      const classes = [...sessionItems()[0].children].map((child) => child.className);
      expect(classes.slice(0, 5)).toEqual([
        'session__time',
        'session__title',
        'session__speaker',
        'session__description',
        'session__capacity',
      ]);
    });

    it('should not offer session management to attendees', async () => {
      await open(buildEvent(), [buildSession()], TEST_USERS.attendee);

      expect(page().querySelector('a[href="/events/10/sessions/new"]')).toBeNull();
      expect(sessionItems()[0].querySelector('.session__actions')).toBeNull();
    });

    it('should let the owner add, edit and delete sessions after confirming', async () => {
      await open(
        buildEvent(),
        [buildSession({ id: 1, title: 'Apertura' }), buildSession({ id: 2, title: 'Cierre' })],
        TEST_USERS.organizer,
      );

      expect(page().querySelector('a[href="/events/10/sessions/new"]')).not.toBeNull();
      expect(
        sessionItems()[0].querySelector('a[href="/events/10/sessions/1/edit"]'),
      ).not.toBeNull();

      buttonIn(sessionItems()[0], 'Eliminar')?.click();
      await harness.fixture.whenStable();
      expect(textOf(sessionItems()[0])).toContain('¿Eliminar esta sesión?');
      http.expectNone(`${TEST_API_URL}/sessions/1`);

      buttonIn(sessionItems()[0], 'Sí, eliminar')?.click();
      const request = http.expectOne(`${TEST_API_URL}/sessions/1`);
      expect(request.request.method).toBe('DELETE');
      request.flush(null, { status: 204, statusText: 'No Content' });
      await harness.fixture.whenStable();

      // Removed locally, without reloading the list.
      expect(sessionItems().length).toBe(1);
      expect(textOf(sessionItems()[0])).toContain('Cierre');
      expect(textOf(page().querySelector('app-alert'))).toBe('Se eliminó la sesión «Apertura».');
    });

    it('should keep the session and explain why when the deletion is rejected', async () => {
      await open(buildEvent(), [buildSession({ id: 1 })], TEST_USERS.organizer);

      buttonIn(sessionItems()[0], 'Eliminar')?.click();
      await harness.fixture.whenStable();
      buttonIn(sessionItems()[0], 'Sí, eliminar')?.click();
      http
        .expectOne(`${TEST_API_URL}/sessions/1`)
        .flush(
          { message: 'Cancelled or completed events cannot be modified' },
          { status: 409, statusText: 'Conflict' },
        );
      await harness.fixture.whenStable();

      expect(sessionItems().length).toBe(1);
      expect(textOf(page().querySelector('.sessions app-alert'))).toBe(
        'Los eventos cancelados o finalizados no se pueden modificar.',
      );
    });

    it('should not offer session management for final events', async () => {
      await open(buildEvent({ status: 'COMPLETED' }), [buildSession()], TEST_USERS.admin);

      expect(page().querySelector('a[href="/events/10/sessions/new"]')).toBeNull();
      expect(sessionItems()[0].querySelector('.session__actions')).toBeNull();
    });
  });

  describe('sessions section visibility (why "Añadir sesión" may be missing)', () => {
    const section = () => page().querySelector('section.sessions') as HTMLElement;
    const addLinks = () => section().querySelectorAll('a[href="/events/10/sessions/new"]');
    const note = () => textOf(section().querySelector('.sessions__note'));

    it('should always show the "Sesiones del evento" section, even to anonymous users', async () => {
      await open(buildEvent(), [buildSession()]);

      expect(textOf(section().querySelector('h2'))).toBe('Sesiones del evento');
      expect(addLinks().length).toBe(0);
      expect(note()).toBe('');
    });

    it('should offer adding the first session from the empty state to the owner', async () => {
      await open(buildEvent(), [], TEST_USERS.organizer);

      const emptyAction = section().querySelector('app-empty-state a');
      expect(textOf(emptyAction)).toBe('Añadir la primera sesión');
      expect(emptyAction?.getAttribute('href')).toBe('/events/10/sessions/new');
      expect(addLinks().length).toBe(2);
    });

    it('should let ADMIN manage sessions of any open event', async () => {
      await open(buildEvent({ created_by: 999 }), [buildSession()], TEST_USERS.admin);

      expect(addLinks().length).toBe(1);
      expect(note()).toBe('');
    });

    it('should explain to an organizer why they cannot manage sessions of an event of someone else', async () => {
      await open(buildEvent(), [], TEST_USERS.otherOrganizer);

      expect(addLinks().length).toBe(0);
      expect(note()).toBe(
        'Solo quien creó este evento o un administrador puede gestionar sus sesiones.',
      );
    });

    for (const [status, text] of [
      ['COMPLETED', 'El evento ha finalizado'],
      ['CANCELLED', 'El evento está cancelado'],
    ] as const) {
      it(`should explain that sessions of a ${status} event cannot be changed`, async () => {
        await open(buildEvent({ status }), [buildSession()], TEST_USERS.admin);

        expect(addLinks().length).toBe(0);
        expect(note()).toContain(text);
        expect(section().querySelector('.session__actions')).toBeNull();
      });
    }

    it('should not show management notes or actions to attendees', async () => {
      await open(buildEvent({ status: 'COMPLETED' }), [], TEST_USERS.attendee);

      expect(addLinks().length).toBe(0);
      expect(note()).toBe('');
      expect(section().querySelector('app-empty-state a')).toBeNull();
    });
  });
});
