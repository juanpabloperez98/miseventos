import { HttpTestingController } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { Title } from '@angular/platform-browser';
import { Router } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';

import {
  buildEvent,
  buildPage,
  cleanUpAuth,
  provideTestDependencies,
  TEST_API_URL,
  TEST_USERS,
  textOf,
} from '../testing/test-helpers';
import { routes } from './app.routes';
import { MainLayout } from './layout/layouts/main-layout/main-layout';

describe('App routes', () => {
  let harness: RouterTestingHarness;
  let http: HttpTestingController;

  const rendered = () => harness.routeNativeElement as HTMLElement;

  beforeEach(async () => {
    TestBed.configureTestingModule({ providers: provideTestDependencies(routes) });
    harness = await RouterTestingHarness.create();
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => cleanUpAuth());

  it('should redirect the root path to the lazy events catalog inside the layout', async () => {
    await harness.navigateByUrl('/', MainLayout);
    TestBed.tick();
    http.expectOne((req) => req.url === `${TEST_API_URL}/events`).flush(buildPage([buildEvent()]));
    await harness.fixture.whenStable();

    expect(TestBed.inject(Router).url).toBe('/events');
    expect(rendered().querySelector('main#main-content app-event-list-page')).not.toBeNull();
    expect(textOf(rendered().querySelector('h1'))).toContain('Descubre eventos');
    expect(TestBed.inject(Title).getTitle()).toBe('Eventos | Mis Eventos');
  });

  it('should render the not found page for unknown paths', async () => {
    await harness.navigateByUrl('/ruta/que-no-existe', MainLayout);

    expect(rendered().querySelector('app-not-found-page')).not.toBeNull();
    expect(textOf(rendered().querySelector('h1'))).toContain('Página no encontrada');
    expect(TestBed.inject(Title).getTitle()).toBe('Página no encontrada | Mis Eventos');
  });

  it('should lazy load the login page', async () => {
    await harness.navigateByUrl('/auth/login', MainLayout);

    expect(rendered().querySelector('app-login-page')).not.toBeNull();
    expect(TestBed.inject(Title).getTitle()).toBe('Iniciar sesión | Mis Eventos');
  });

  it('should protect /profile and return to it after signing in', async () => {
    await harness.navigateByUrl('/profile', MainLayout);
    expect(TestBed.inject(Router).url).toBe('/auth/login?returnUrl=%2Fprofile');

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
    TestBed.tick();
    http
      .expectOne(`${TEST_API_URL}/me/registrations`)
      .flush([buildEvent({ id: 3, name: 'Angular Summit' })]);
    await harness.fixture.whenStable();

    expect(TestBed.inject(Router).url).toBe('/profile');
    expect(TestBed.inject(Title).getTitle()).toBe('Mi perfil | Mis Eventos');
    expect(rendered().querySelector('main#main-content app-profile-page')).not.toBeNull();
    expect(textOf(rendered().querySelector('app-event-card'))).toContain('Angular Summit');
    expect(rendered().querySelector('nav a[href="/profile"]')?.getAttribute('aria-current')).toBe(
      'page',
    );
  });
});
