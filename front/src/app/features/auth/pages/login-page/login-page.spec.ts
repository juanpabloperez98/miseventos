import { HttpTestingController } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';

import { AuthService } from '../../../../core/auth/auth.service';
import {
  BlankPage,
  cleanUpAuth,
  provideTestDependencies,
  TEST_API_URL,
  TEST_USERS,
  textOf,
} from '../../../../../testing/test-helpers';
import { LoginPage, safeReturnUrl } from './login-page';

describe('LoginPage', () => {
  let harness: RouterTestingHarness;
  let http: HttpTestingController;

  const page = () => harness.routeNativeElement as HTMLElement;

  function fill(type: string, value: string): void {
    const input = page().querySelector<HTMLInputElement>(`input[type="${type}"]`)!;
    input.value = value;
    input.dispatchEvent(new Event('input'));
  }

  async function submit(): Promise<void> {
    page().querySelector<HTMLButtonElement>('button[type="submit"]')?.click();
    await harness.fixture.whenStable();
  }

  beforeEach(async () => {
    TestBed.configureTestingModule({
      providers: provideTestDependencies([
        { path: 'auth/login', component: LoginPage },
        { path: 'events', component: BlankPage },
        { path: 'events/new', component: BlankPage },
      ]),
    });
    harness = await RouterTestingHarness.create();
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => cleanUpAuth());

  it('should validate the fields before calling the API', async () => {
    await harness.navigateByUrl('/auth/login', LoginPage);
    fill('email', 'not-an-email');
    await submit();

    expect(textOf(page())).toContain('Introduce un correo electrónico válido.');
    expect(textOf(page())).toContain('Este campo es obligatorio.');
    http.expectNone(`${TEST_API_URL}/auth/login`);
  });

  it('should sign in and go to the return URL', async () => {
    await harness.navigateByUrl('/auth/login?returnUrl=%2Fevents%2Fnew', LoginPage);
    fill('email', ' organizer@test.dev ');
    fill('password', 'password123');
    await submit();

    const login = http.expectOne(`${TEST_API_URL}/auth/login`);
    expect(login.request.body).toEqual({ email: 'organizer@test.dev', password: 'password123' });
    expect(page().querySelector<HTMLButtonElement>('button[type="submit"]')?.disabled).toBeTrue();
    login.flush({
      access_token: 'jwt',
      token_type: 'Bearer',
      expires_at: new Date(Date.now() + 60_000).toISOString(),
    });
    http.expectOne(`${TEST_API_URL}/auth/me`).flush(TEST_USERS.organizer);
    await harness.fixture.whenStable();

    expect(TestBed.inject(AuthService).user()).toEqual(TEST_USERS.organizer);
    expect(TestBed.inject(Router).url).toBe('/events/new');
  });

  it('should show a clear message for invalid credentials', async () => {
    await harness.navigateByUrl('/auth/login', LoginPage);
    fill('email', 'organizer@test.dev');
    fill('password', 'wrong');
    await submit();

    http
      .expectOne(`${TEST_API_URL}/auth/login`)
      .flush({ message: 'Invalid email or password' }, { status: 401, statusText: 'Unauthorized' });
    await harness.fixture.whenStable();

    expect(textOf(page().querySelector('app-alert'))).toBe(
      'El correo o la contraseña no son correctos.',
    );
    expect(page().querySelector<HTMLButtonElement>('button[type="submit"]')?.disabled).toBeFalse();
    expect(TestBed.inject(Router).url).toBe('/auth/login');
  });

  it('should only accept return URLs inside the app', () => {
    expect(safeReturnUrl('/events/3')).toBe('/events/3');
    expect(safeReturnUrl('https://evil.example')).toBe('/events');
    expect(safeReturnUrl('//evil.example')).toBe('/events');
    expect(safeReturnUrl(undefined)).toBe('/events');
  });
});
