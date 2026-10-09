import { HttpTestingController } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';

import { routes } from '../../../../app.routes';
import { type User } from '../../../../core/auth/auth.models';
import { MainLayout } from '../../../../layout/layouts/main-layout/main-layout';
import {
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

const EVENT = buildEvent({
  id: 10,
  start_date: new Date('2030-05-10T10:00').toISOString(),
  end_date: new Date('2030-05-10T18:00').toISOString(),
});
const SPEAKERS = {
  items: [{ id: 1, name: 'Ada Lovelace', bio: null }],
  total: 1,
  page: 1,
  per_page: 100,
  pages: 1,
};

describe('SessionFormPage', () => {
  let harness: RouterTestingHarness;
  let http: HttpTestingController;
  let router: Router;

  const page = () => harness.routeNativeElement as HTMLElement;
  const speakersRequest = () => http.expectOne((req) => req.url === `${TEST_API_URL}/speakers`);

  async function open(url: string, event: EventModel = EVENT, user: User = TEST_USERS.organizer) {
    signInAs(user);
    await harness.navigateByUrl(url, MainLayout);
    TestBed.tick();
    http.expectOne(`${TEST_API_URL}/events/${event.id}`).flush(event);
  }

  function fill(label: string, value: string): void {
    const found = [...page().querySelectorAll('app-form-field')].find((candidate) =>
      textOf(candidate.querySelector('label')).startsWith(label),
    );
    const control = found?.querySelector<HTMLInputElement>('input, textarea, select');
    control!.value = value;
    control!.dispatchEvent(new Event(control instanceof HTMLSelectElement ? 'change' : 'input'));
  }

  async function fillValidForm(): Promise<void> {
    fill('Título', 'Keynote');
    fill('Inicio', '2030-05-10T11:00');
    fill('Finalización', '2030-05-10T12:00');
    fill('Capacidad', '40');
    fill('Ponente', '1');
    page().querySelector<HTMLButtonElement>('button[type="submit"]')?.click();
    await harness.fixture.whenStable();
  }

  /** Answers the requests of the event detail page shown after saving. */
  async function flushEventDetail(): Promise<void> {
    await harness.fixture.whenStable();
    TestBed.tick();
    for (const pending of http.match(() => true)) {
      pending.flush(pending.request.url === `${TEST_API_URL}/events/10` ? EVENT : []);
    }
    await harness.fixture.whenStable();
  }

  beforeEach(async () => {
    TestBed.configureTestingModule({ providers: provideTestDependencies(routes) });
    harness = await RouterTestingHarness.create();
    http = TestBed.inject(HttpTestingController);
    router = TestBed.inject(Router);
  });

  afterEach(() => cleanUpAuth());

  it('should create a session and go back to the event with a confirmation', async () => {
    await open('/events/10/sessions/new');
    speakersRequest().flush(SPEAKERS);
    await harness.fixture.whenStable();
    expect(textOf(page().querySelector('h1'))).toBe('Nueva sesión');

    await fillValidForm();

    const request = http.expectOne(`${TEST_API_URL}/events/10/sessions`);
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual(
      jasmine.objectContaining({ title: 'Keynote', capacity: 40, speaker_id: 1 }),
    );
    request.flush(buildSession(), { status: 201, statusText: 'Created' });
    await flushEventDetail();

    expect(router.url).toBe('/events/10');
    expect(textOf(page().querySelector('app-alert'))).toBe('Sesión creada.');
  });

  it('should load the session to edit and save it with PUT', async () => {
    await open('/events/10/sessions/100/edit');
    http
      .expectOne(`${TEST_API_URL}/sessions/100`)
      .flush(buildSession({ id: 100, event_id: 10, title: 'Signals', speaker_id: 1 }));
    speakersRequest().flush(SPEAKERS);
    await harness.fixture.whenStable();

    expect(textOf(page().querySelector('h1'))).toBe('Editar sesión');
    expect(page().querySelector<HTMLSelectElement>('select')?.value).toBe('1');

    await fillValidForm();
    const request = http.expectOne(`${TEST_API_URL}/sessions/100`);
    expect(request.request.method).toBe('PUT');
    request.flush(buildSession({ id: 100 }));
    await flushEventDetail();

    expect(router.url).toBe('/events/10');
    expect(textOf(page().querySelector('app-alert'))).toBe(
      'Los cambios de la sesión se guardaron.',
    );
  });

  it('should show backend validation and conflicts without leaving the form', async () => {
    await open('/events/10/sessions/new');
    speakersRequest().flush(SPEAKERS);
    await harness.fixture.whenStable();

    await fillValidForm();
    http
      .expectOne(`${TEST_API_URL}/events/10/sessions`)
      .flush(
        { message: 'Session must take place within the event schedule' },
        { status: 422, statusText: 'Unprocessable Entity' },
      );
    await harness.fixture.whenStable();

    expect(textOf(page().querySelector('app-alert'))).toBe(
      'La sesión debe estar dentro del horario del evento.',
    );
    expect(router.url).toBe('/events/10/sessions/new');
    expect(page().querySelector<HTMLButtonElement>('button[type="submit"]')?.disabled).toBeFalse();
  });

  it('should show the backend rejection of a capacity above the event capacity', async () => {
    await open('/events/10/sessions/new');
    speakersRequest().flush(SPEAKERS);
    await harness.fixture.whenStable();

    await fillValidForm();
    http
      .expectOne(`${TEST_API_URL}/events/10/sessions`)
      .flush(
        { message: 'Session capacity cannot exceed the event capacity' },
        { status: 422, statusText: 'Unprocessable Entity' },
      );
    await harness.fixture.whenStable();

    expect(textOf(page().querySelector('app-alert'))).toBe(
      'La capacidad de la sesión no puede superar la capacidad del evento.',
    );
    expect(router.url).toBe('/events/10/sessions/new');
  });

  it('should report a session that belongs to another event as not found', async () => {
    await open('/events/10/sessions/100/edit');
    speakersRequest().flush(SPEAKERS);
    http.expectOne(`${TEST_API_URL}/sessions/100`).flush(buildSession({ id: 100, event_id: 99 }));
    await harness.fixture.whenStable();

    expect(textOf(page().querySelector('app-empty-state'))).toContain('Sesión no encontrada');
    expect(page().querySelector('app-session-form')).toBeNull();
  });

  it('should not show the form to an organizer who does not own the event', async () => {
    await open('/events/10/sessions/new', EVENT, TEST_USERS.otherOrganizer);
    speakersRequest().flush(SPEAKERS);
    await harness.fixture.whenStable();

    expect(textOf(page().querySelector('app-error-state'))).toContain(
      'No puedes gestionar estas sesiones',
    );
    expect(page().querySelector('app-session-form')).toBeNull();
  });

  it('should not show the form when the speakers cannot be loaded, and allow retrying', async () => {
    await open('/events/10/sessions/new');
    speakersRequest().flush(
      { message: 'Internal server error' },
      { status: 500, statusText: 'Error' },
    );
    await harness.fixture.whenStable();

    expect(page().querySelector('app-session-form')).toBeNull();
    page().querySelector<HTMLButtonElement>('app-error-state button')?.click();
    TestBed.tick();
    http.expectOne(`${TEST_API_URL}/events/10`).flush(EVENT);
    speakersRequest().flush(SPEAKERS);
    await harness.fixture.whenStable();

    expect(page().querySelector('app-session-form')).not.toBeNull();
  });

  describe('route protection', () => {
    it('should send anonymous users to login with the session route as return URL', async () => {
      await harness.navigateByUrl('/events/10/sessions/new', MainLayout);

      expect(router.url).toBe('/auth/login?returnUrl=%2Fevents%2F10%2Fsessions%2Fnew');
    });

    it('should show access denied to attendees', async () => {
      signInAs(TEST_USERS.attendee);
      await harness.navigateByUrl('/events/10/sessions/100/edit', MainLayout);

      expect(page().querySelector('app-forbidden-page')).not.toBeNull();
      http.expectNone((req) => req.url.includes('/sessions'));
    });

    it('should treat non-numeric session ids as unknown pages', async () => {
      signInAs(TEST_USERS.organizer);
      await harness.navigateByUrl('/events/10/sessions/abc/edit', MainLayout);

      expect(page().querySelector('app-not-found-page')).not.toBeNull();
    });
  });
});
