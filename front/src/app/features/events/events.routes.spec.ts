import { Location } from '@angular/common';
import { HttpTestingController } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { Title } from '@angular/platform-browser';
import { Router } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';

import { routes } from '../../app.routes';
import { AuthService } from '../../core/auth/auth.service';
import { MainLayout } from '../../layout/layouts/main-layout/main-layout';
import {
  buildEvent,
  cleanUpAuth,
  provideTestDependencies,
  signInAs,
  TEST_API_URL,
  TEST_USERS,
  textOf,
} from '../../../testing/test-helpers';

const PERMISSION_MESSAGE = 'Tu cuenta no tiene permiso para gestionar eventos.';

/** Event routes with the real application route tree, guards and layout. */
describe('Event routes (authentication vs authorization)', () => {
  let harness: RouterTestingHarness;
  let http: HttpTestingController;
  let router: Router;

  const rendered = () => harness.routeNativeElement as HTMLElement;
  const browserPath = () => TestBed.inject(Location).path();

  beforeEach(async () => {
    TestBed.configureTestingModule({ providers: provideTestDependencies(routes) });
    harness = await RouterTestingHarness.create();
    http = TestBed.inject(HttpTestingController);
    router = TestBed.inject(Router);
  });

  afterEach(() => cleanUpAuth());

  describe('case 1: anonymous user', () => {
    for (const url of ['/events/new', '/events/create']) {
      it(`should go to login keeping the creation route when opening ${url}`, async () => {
        await harness.navigateByUrl(url, MainLayout);
        TestBed.tick();

        expect(router.url).toBe('/auth/login?returnUrl=%2Fevents%2Fnew');
        expect(rendered().querySelector('app-login-page')).not.toBeNull();
        expect(textOf(rendered())).not.toContain(PERMISSION_MESSAGE);
        expect(textOf(rendered())).not.toContain('Evento no encontrado');
        // Regression: "create" used to be taken as an event id → GET /events/NaN.
        http.expectNone((req) => req.url.includes('/events/'));
      });
    }

    it('should go to login keeping the edit route', async () => {
      await harness.navigateByUrl('/events/7/edit', MainLayout);

      expect(router.url).toBe('/auth/login?returnUrl=%2Fevents%2F7%2Fedit');
    });

    it('should return to the creation form after signing in', async () => {
      await harness.navigateByUrl('/events/create', MainLayout);

      const fill = (type: string, value: string) => {
        const input = rendered().querySelector<HTMLInputElement>(`input[type="${type}"]`)!;
        input.value = value;
        input.dispatchEvent(new Event('input'));
      };
      fill('email', TEST_USERS.organizer.email);
      fill('password', 'password123');
      rendered().querySelector<HTMLButtonElement>('button[type="submit"]')?.click();
      await harness.fixture.whenStable();
      http.expectOne(`${TEST_API_URL}/auth/login`).flush({
        access_token: 'jwt',
        token_type: 'Bearer',
        expires_at: new Date(Date.now() + 60_000).toISOString(),
      });
      http.expectOne(`${TEST_API_URL}/auth/me`).flush(TEST_USERS.organizer);
      await harness.fixture.whenStable();

      expect(router.url).toBe('/events/new');
      expect(rendered().querySelector('app-event-create-page app-event-form')).not.toBeNull();
    });
  });

  describe('case 2: authenticated user without permission', () => {
    for (const url of ['/events/new', '/events/create', '/events/7/edit']) {
      it(`should show access denied on ${url} and keep the session`, async () => {
        signInAs(TEST_USERS.attendee);

        await harness.navigateByUrl(url, MainLayout);

        expect(rendered().querySelector('app-forbidden-page')).not.toBeNull();
        expect(textOf(rendered().querySelector('h1'))).toBe('Acceso denegado');
        expect(textOf(rendered().querySelector('[role="alert"]'))).toBe(PERMISSION_MESSAGE);
        expect(TestBed.inject(Title).getTitle()).toBe('Acceso denegado | Mis Eventos');
        // Not sent to login nor to the catalog: access denied is shown at the requested URL.
        expect(browserPath()).toBe(url === '/events/create' ? '/events/new' : url);
        expect(router.url).toBe(browserPath());
        expect(router.url).not.toContain('/auth/login');
        expect(TestBed.inject(AuthService).isAuthenticated()).toBeTrue();
        http.expectNone((req) => req.url.includes('/events'));
      });
    }
  });

  describe('case 2 after signing in', () => {
    it('should show access denied at the return URL when the account has no permission', async () => {
      await harness.navigateByUrl('/events/new', MainLayout);
      expect(router.url).toBe('/auth/login?returnUrl=%2Fevents%2Fnew');

      const fill = (type: string, value: string) => {
        const input = rendered().querySelector<HTMLInputElement>(`input[type="${type}"]`)!;
        input.value = value;
        input.dispatchEvent(new Event('input'));
      };
      fill('email', TEST_USERS.attendee.email);
      fill('password', 'password123');
      rendered().querySelector<HTMLButtonElement>('button[type="submit"]')?.click();
      await harness.fixture.whenStable();
      http.expectOne(`${TEST_API_URL}/auth/login`).flush({
        access_token: 'jwt',
        token_type: 'Bearer',
        expires_at: new Date(Date.now() + 60_000).toISOString(),
      });
      http.expectOne(`${TEST_API_URL}/auth/me`).flush(TEST_USERS.attendee);
      await harness.fixture.whenStable();

      expect(browserPath()).toBe('/events/new');
      expect(rendered().querySelector('app-forbidden-page')).not.toBeNull();
      expect(textOf(rendered().querySelector('[role="alert"]'))).toBe(PERMISSION_MESSAGE);
      expect(TestBed.inject(AuthService).isAuthenticated()).toBeTrue();
    });
  });

  describe('case 3: authenticated user with permission', () => {
    for (const role of ['organizer', 'admin'] as const) {
      it(`should open the creation form for ${role.toUpperCase()}`, async () => {
        signInAs(TEST_USERS[role]);

        await harness.navigateByUrl('/events/new', MainLayout);

        expect(router.url).toBe('/events/new');
        expect(rendered().querySelector('app-event-form')).not.toBeNull();
        expect(textOf(rendered().querySelector('h1'))).toBe('Crear evento');
        expect(rendered().querySelector('app-forbidden-page')).toBeNull();
        expect(textOf(rendered())).not.toContain(PERMISSION_MESSAGE);
      });
    }

    it('should open the edit form of an owned event', async () => {
      signInAs(TEST_USERS.organizer);

      await harness.navigateByUrl('/events/7/edit', MainLayout);
      TestBed.tick();
      http.expectOne(`${TEST_API_URL}/events/7`).flush(buildEvent({ id: 7 }));
      await harness.fixture.whenStable();

      expect(router.url).toBe('/events/7/edit');
      expect(rendered().querySelector('app-event-edit-page app-event-form')).not.toBeNull();
    });
  });

  describe('event detail', () => {
    it('should still load real numeric ids', async () => {
      await harness.navigateByUrl('/events/7', MainLayout);
      TestBed.tick();
      http
        .expectOne(`${TEST_API_URL}/events/7`)
        .flush(buildEvent({ id: 7, name: 'Angular Summit' }));
      http.expectOne(`${TEST_API_URL}/events/7/sessions`).flush([]);
      await harness.fixture.whenStable();

      expect(textOf(rendered().querySelector('h1'))).toBe('Angular Summit');
    });

    it('should show the not found state for an id that does not exist', async () => {
      await harness.navigateByUrl('/events/999', MainLayout);
      TestBed.tick();
      http
        .expectOne(`${TEST_API_URL}/events/999`)
        .flush({ message: 'Event not found' }, { status: 404, statusText: 'Not Found' });
      http
        .expectOne(`${TEST_API_URL}/events/999/sessions`)
        .flush({ message: 'Event not found' }, { status: 404, statusText: 'Not Found' });
      await harness.fixture.whenStable();

      expect(textOf(rendered().querySelector('app-empty-state'))).toContain('Evento no encontrado');
    });

    it('should treat non-numeric segments as an unknown page without calling the API', async () => {
      await harness.navigateByUrl('/events/abc', MainLayout);
      TestBed.tick();

      expect(rendered().querySelector('app-not-found-page')).not.toBeNull();
      http.expectNone((req) => req.url.includes('/events/'));
    });
  });
});
