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
import { RegisterPage } from './register-page';

describe('RegisterPage', () => {
  let harness: RouterTestingHarness;
  let http: HttpTestingController;

  const page = () => harness.routeNativeElement as HTMLElement;

  function fill(values: Record<string, string>): void {
    const inputs = page().querySelectorAll<HTMLInputElement>('input');
    const order = ['name', 'email', 'password', 'confirmPassword'];
    order.forEach((key, index) => {
      if (key in values) {
        inputs[index].value = values[key];
        inputs[index].dispatchEvent(new Event('input'));
      }
    });
  }

  async function submit(): Promise<void> {
    page().querySelector<HTMLButtonElement>('button[type="submit"]')?.click();
    await harness.fixture.whenStable();
  }

  const validValues = {
    name: 'Ana',
    email: 'ana@test.dev',
    password: 'password123',
    confirmPassword: 'password123',
  };

  beforeEach(async () => {
    TestBed.configureTestingModule({
      providers: provideTestDependencies([
        { path: 'auth/register', component: RegisterPage },
        { path: 'auth/login', component: BlankPage },
        { path: 'events', component: BlankPage },
      ]),
    });
    harness = await RouterTestingHarness.create();
    http = TestBed.inject(HttpTestingController);
    await harness.navigateByUrl('/auth/register', RegisterPage);
  });

  afterEach(() => cleanUpAuth());

  it('should not offer any role selection', () => {
    expect(page().querySelector('select')).toBeNull();
    expect(textOf(page())).not.toContain('Organizador');
  });

  it('should validate password length and confirmation', async () => {
    fill({ ...validValues, password: 'short', confirmPassword: 'different' });
    await submit();

    expect(textOf(page())).toContain('Debe tener al menos 8 caracteres.');
    expect(textOf(page())).toContain('Las contraseñas no coinciden.');
    http.expectNone(`${TEST_API_URL}/auth/register`);
  });

  it('should register, sign in automatically and go to the events', async () => {
    fill(validValues);
    await submit();

    const register = http.expectOne(`${TEST_API_URL}/auth/register`);
    expect(register.request.body).toEqual({
      name: 'Ana',
      email: 'ana@test.dev',
      password: 'password123',
    });
    register.flush(TEST_USERS.attendee, { status: 201, statusText: 'Created' });
    http.expectOne(`${TEST_API_URL}/auth/login`).flush({
      access_token: 'jwt',
      token_type: 'Bearer',
      expires_at: new Date(Date.now() + 60_000).toISOString(),
    });
    http.expectOne(`${TEST_API_URL}/auth/me`).flush(TEST_USERS.attendee);
    await harness.fixture.whenStable();

    expect(TestBed.inject(AuthService).user()?.role).toBe('ATTENDEE');
    expect(TestBed.inject(Router).url).toBe('/events');
  });

  it('should show the duplicated email error on the email field', async () => {
    fill(validValues);
    await submit();

    http
      .expectOne(`${TEST_API_URL}/auth/register`)
      .flush({ message: 'Email is already registered' }, { status: 409, statusText: 'Conflict' });
    await harness.fixture.whenStable();

    const emailInput = page().querySelectorAll('input')[1];
    expect(emailInput.getAttribute('aria-invalid')).toBe('true');
    expect(textOf(page())).toContain('Este correo ya está registrado.');
    expect(TestBed.inject(AuthService).isAuthenticated()).toBeFalse();
  });

  it('should show backend validation errors per field', async () => {
    fill(validValues);
    await submit();

    http.expectOne(`${TEST_API_URL}/auth/register`).flush(
      {
        message: 'Request validation failed',
        errors: { json: { email: ['Not a valid email address.'] } },
      },
      { status: 422, statusText: 'Unprocessable Entity' },
    );
    await harness.fixture.whenStable();

    expect(textOf(page())).toContain('Not a valid email address.');
  });
});
