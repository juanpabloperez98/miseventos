import { HttpTestingController, type TestRequest } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';

import { AuthService } from '../../../../core/auth/auth.service';
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
import { PROFILE_ROUTES } from '../../profile.routes';

describe('ProfilePage', () => {
  let harness: RouterTestingHarness;
  let http: HttpTestingController;
  let router: Router;

  const page = () => harness.routeNativeElement as HTMLElement;
  const settle = () => harness.fixture.whenStable();
  const registrationsRequest = (): TestRequest => {
    TestBed.tick();
    return http.expectOne(`${TEST_API_URL}/me/registrations`);
  };

  async function openAsAttendee(): Promise<void> {
    signInAs(TEST_USERS.attendee);
    await harness.navigateByUrl('/profile');
  }

  beforeEach(async () => {
    TestBed.configureTestingModule({
      providers: provideTestDependencies([
        { path: 'profile', children: PROFILE_ROUTES },
        { path: 'events', component: BlankPage },
        { path: 'events/:id', component: BlankPage },
        { path: 'auth/login', component: BlankPage },
      ]),
    });
    harness = await RouterTestingHarness.create();
    http = TestBed.inject(HttpTestingController);
    router = TestBed.inject(Router);
  });

  afterEach(() => cleanUpAuth());

  it('should send anonymous users to login and keep /profile as return URL', async () => {
    await harness.navigateByUrl('/profile');

    expect(router.url).toBe('/auth/login?returnUrl=%2Fprofile');
    http.expectNone(`${TEST_API_URL}/me/registrations`);
  });

  it('should show the user data and a loading state while requesting registrations', async () => {
    await openAsAttendee();
    const request = registrationsRequest();

    expect(textOf(page().querySelector('h1'))).toBe('Mi perfil');
    expect(textOf(page().querySelector('.profile__data'))).toContain('Ana Attendee');
    expect(textOf(page().querySelector('.profile__data'))).toContain('attendee@test.dev');
    expect(textOf(page().querySelector('.profile__data'))).toContain('Asistente');
    expect(page().querySelector('app-loading')).not.toBeNull();

    request.flush([]);
  });

  it('should list the registered events with a link to each detail', async () => {
    await openAsAttendee();
    registrationsRequest().flush([
      buildEvent({ id: 7, name: 'Angular Summit' }),
      buildEvent({ id: 8, name: 'PyCon', status: 'CANCELLED' }),
    ]);
    await settle();

    const cards = page().querySelectorAll('app-event-card');
    expect(cards.length).toBe(2);
    expect(textOf(cards[0])).toContain('Angular Summit');
    expect(textOf(cards[0])).toContain('Medellín');
    expect(textOf(cards[1])).toContain('Cancelado');
    expect(textOf(page().querySelector('.registrations__count'))).toBe('2 inscripciones');

    const link = cards[0].querySelector<HTMLAnchorElement>('a.card__link');
    expect(link?.getAttribute('href')).toBe('/events/7');
    link?.click();
    await settle();

    expect(router.url).toBe('/events/7');
  });

  it('should show an empty state with a link to explore events', async () => {
    await openAsAttendee();
    registrationsRequest().flush([]);
    await settle();

    const empty = page().querySelector('app-empty-state');
    expect(textOf(empty)).toContain('Aún no te has inscrito en ningún evento');
    expect(empty?.querySelector('a')?.getAttribute('href')).toBe('/events');
  });

  it('should show an error state and retry the request', async () => {
    await openAsAttendee();
    registrationsRequest().flush(
      { message: 'Internal server error' },
      { status: 500, statusText: 'Error' },
    );
    await settle();

    const error = page().querySelector('app-error-state');
    expect(textOf(error)).toContain('No se pudieron cargar tus inscripciones');
    expect(textOf(error)).toContain('error en el servidor');

    error?.querySelector('button')?.click();
    registrationsRequest().flush([buildEvent()]);
    await settle();

    expect(page().querySelector('app-error-state')).toBeNull();
    expect(page().querySelectorAll('app-event-card').length).toBe(1);
  });

  it('should leave the page and not keep private data when the session is rejected', async () => {
    await openAsAttendee();
    registrationsRequest().flush(
      { message: 'Invalid or expired token' },
      { status: 401, statusText: 'Unauthorized' },
    );
    // The interceptor ends the session and retries the GET once without the token.
    http
      .expectOne(`${TEST_API_URL}/me/registrations`)
      .flush({ message: 'Missing bearer token' }, { status: 401, statusText: 'Unauthorized' });
    await settle();

    expect(router.url).toBe('/auth/login?returnUrl=%2Fprofile');
    expect(TestBed.inject(FlashMessageService).consume()?.text).toContain('Tu sesión ha expirado');
    expect(TestBed.inject(AuthService).isAuthenticated()).toBeFalse();
    // No further requests: verified by HttpTestingController in afterEach.
  });

  it('should drop the previous user registrations when the session ends', async () => {
    await openAsAttendee();
    registrationsRequest().flush([buildEvent({ id: 7, name: 'Evento privado' })]);
    await settle();
    expect(page().querySelectorAll('app-event-card').length).toBe(1);

    TestBed.inject(AuthService).logout();
    await settle();

    expect(page().querySelector('app-event-card')).toBeNull();
    expect(textOf(page())).not.toContain('Evento privado');
    expect(textOf(page())).not.toContain('attendee@test.dev');
  });
});
