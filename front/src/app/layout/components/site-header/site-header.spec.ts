import { type ComponentFixture, TestBed } from '@angular/core/testing';

import { type User } from '../../../core/auth/auth.models';
import { AuthService } from '../../../core/auth/auth.service';
import {
  BlankPage,
  cleanUpAuth,
  provideTestDependencies,
  signInAs,
  TEST_USERS,
  textOf,
} from '../../../../testing/test-helpers';
import { SiteHeader } from './site-header';

describe('SiteHeader', () => {
  let fixture: ComponentFixture<SiteHeader>;

  const element = () => fixture.nativeElement as HTMLElement;
  const createLink = () => element().querySelector('a[href="/events/new"]');

  async function render(user?: User): Promise<void> {
    TestBed.configureTestingModule({
      providers: provideTestDependencies([{ path: 'events', component: BlankPage }]),
    });
    if (user) {
      signInAs(user);
    }
    fixture = TestBed.createComponent(SiteHeader);
    await fixture.whenStable();
  }

  afterEach(() => cleanUpAuth());

  it('should offer login and registration to anonymous users', async () => {
    await render();

    expect(element().querySelector('a[href="/auth/login"]')).not.toBeNull();
    expect(element().querySelector('a[href="/auth/register"]')).not.toBeNull();
    expect(createLink()).toBeNull();
  });

  it('should hide the create button for ATTENDEE', async () => {
    await render(TEST_USERS.attendee);

    expect(textOf(element())).toContain('Ana Attendee');
    expect(textOf(element())).toContain('Asistente');
    expect(createLink()).toBeNull();
  });

  it('should show the create button for ORGANIZER', async () => {
    await render(TEST_USERS.organizer);
    expect(createLink()).not.toBeNull();
  });

  it('should show the create button for ADMIN', async () => {
    await render(TEST_USERS.admin);
    expect(createLink()).not.toBeNull();
  });

  it('should log out and update the header', async () => {
    await render(TEST_USERS.organizer);

    [...element().querySelectorAll('button')]
      .find((button) => textOf(button) === 'Cerrar sesión')
      ?.click();
    await fixture.whenStable();

    expect(TestBed.inject(AuthService).isAuthenticated()).toBeFalse();
    expect(createLink()).toBeNull();
    expect(element().querySelector('a[href="/auth/login"]')).not.toBeNull();
  });

  it('should show the profile link only to signed-in users', async () => {
    await render(TEST_USERS.attendee);
    const profileLink = () => element().querySelector('nav a[href="/profile"]');
    expect(textOf(profileLink())).toBe('Mi perfil');

    [...element().querySelectorAll('button')]
      .find((button) => textOf(button) === 'Cerrar sesión')
      ?.click();
    await fixture.whenStable();

    expect(profileLink()).toBeNull();
  });

  it('should not show the profile link to anonymous users', async () => {
    await render();
    expect(element().querySelector('a[href="/profile"]')).toBeNull();
  });

  it('should toggle the mobile menu with aria-expanded', async () => {
    await render();
    const toggle = element().querySelector<HTMLButtonElement>('.menu-toggle')!;
    expect(toggle.getAttribute('aria-expanded')).toBe('false');

    toggle.click();
    await fixture.whenStable();

    expect(toggle.getAttribute('aria-expanded')).toBe('true');
    expect(element().querySelector('#site-menu')?.classList).toContain('menu--open');
  });
});
