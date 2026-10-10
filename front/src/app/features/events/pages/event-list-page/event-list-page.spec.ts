import { HttpTestingController, type TestRequest } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';

import { type User } from '../../../../core/auth/auth.models';
import { AuthService } from '../../../../core/auth/auth.service';
import {
  BlankPage,
  buildEvent,
  buildImage,
  buildPage,
  cleanUpAuth,
  provideTestDependencies,
  signInAs,
  TEST_API_URL,
  TEST_USERS,
  textOf,
} from '../../../../../testing/test-helpers';
import { EventListPage } from './event-list-page';

describe('EventListPage', () => {
  let harness: RouterTestingHarness;
  let http: HttpTestingController;

  const page = () => harness.routeNativeElement as HTMLElement;
  const listRequest = (): TestRequest => {
    TestBed.tick();
    return http.expectOne((req) => req.url === `${TEST_API_URL}/events`);
  };
  const settle = () => harness.fixture.whenStable();

  async function open(url = '/events', user?: User): Promise<void> {
    if (user) {
      signInAs(user);
    }
    await harness.navigateByUrl(url, EventListPage);
  }

  beforeEach(async () => {
    TestBed.configureTestingModule({
      providers: provideTestDependencies([
        { path: 'events', component: EventListPage },
        { path: 'events/:id', component: BlankPage },
      ]),
    });
    harness = await RouterTestingHarness.create();
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => cleanUpAuth());

  it('should show a loading state and then the event cards', async () => {
    await open();
    const request = listRequest();
    expect(page().querySelector('app-loading')).not.toBeNull();

    request.flush(
      buildPage([
        buildEvent({ id: 1, name: 'Angular Summit' }),
        buildEvent({ id: 2, name: 'PyCon' }),
      ]),
    );
    await settle();

    expect(page().querySelector('app-loading')).toBeNull();
    const cards = page().querySelectorAll('app-event-card');
    expect(cards.length).toBe(2);
    expect(textOf(cards[0])).toContain('Angular Summit');
    expect(textOf(cards[0])).toContain('Medellín');
    expect(textOf(cards[0].querySelector('.card__meta'))).toContain(
      '10/05/2030 · 9:00 AM – 5:00 PM',
    );
    expect(textOf(cards[0].querySelector('.card__day'))).toBe('10');
    expect(textOf(cards[0].querySelector('.card__month'))).toBe('may');
    expect(textOf(page().querySelector('.results-header__count'))).toBe('2 eventos');
  });

  it('should show lazy, optimized card images and the default cover for the rest', async () => {
    await open();
    listRequest().flush(
      buildPage([buildEvent({ id: 1, image: buildImage() }), buildEvent({ id: 2, image: null })]),
    );
    await settle();

    const [withImage, withoutImage] = page().querySelectorAll('app-event-card');
    const image = withImage.querySelector('img.card__image');
    expect(image?.getAttribute('src')).toContain(
      '/upload/f_auto,q_auto,c_fill,g_auto,w_400,h_250/',
    );
    expect(image?.getAttribute('srcset')).toContain('800w');
    expect(image?.getAttribute('loading')).toBe('lazy');
    expect(withoutImage.querySelector('img')?.getAttribute('src')).toBe(
      'images/event-cover-default.svg',
    );
  });

  it('should request the page and search from the URL', async () => {
    await open('/events?page=3&search=angular');

    const request = listRequest();
    expect(request.request.params.get('page')).toBe('3');
    expect(request.request.params.get('per_page')).toBe('9');
    expect(request.request.params.get('search')).toBe('angular');
    request.flush(buildPage([], { page: 3 }));
  });

  it('should show an empty state when there are no events', async () => {
    await open();
    listRequest().flush(buildPage([]));
    await settle();

    expect(textOf(page().querySelector('app-empty-state'))).toContain('Todavía no hay eventos');
  });

  it('should show an error state and retry', async () => {
    await open();
    listRequest().flush({ message: 'Internal server error' }, { status: 500, statusText: 'Error' });
    await settle();

    const error = page().querySelector('app-error-state');
    expect(textOf(error)).toContain('No se pudieron cargar los eventos');

    error?.querySelector('button')?.click();
    listRequest().flush(buildPage([buildEvent()]));
    await settle();

    expect(page().querySelectorAll('app-event-card').length).toBe(1);
  });

  it('should navigate to the selected page with server-side pagination', async () => {
    await open();
    listRequest().flush(buildPage([buildEvent()], { total: 30, pages: 4 }));
    await settle();

    page().querySelector<HTMLButtonElement>('button[aria-label="Página 2"]')?.click();
    await settle();

    expect(TestBed.inject(Router).url).toBe('/events?page=2');
    const request = listRequest();
    expect(request.request.params.get('page')).toBe('2');
    request.flush(buildPage([buildEvent()], { page: 2, total: 30, pages: 4 }));
  });

  it('should put the search term in the URL', async () => {
    await open();
    listRequest().flush(buildPage([]));
    await settle();

    const input = page().querySelector<HTMLInputElement>('#event-search');
    input!.value = 'python';
    input!.dispatchEvent(new Event('input'));
    page().querySelector<HTMLFormElement>('form[role="search"]')?.requestSubmit();
    await settle();

    expect(TestBed.inject(Router).url).toBe('/events?search=python');
    listRequest().flush(buildPage([]));
  });

  describe('session transitions', () => {
    it('should reload anonymously after logout without keeping the previous results', async () => {
      await open('/events', TEST_USERS.organizer);
      const first = listRequest();
      expect(first.request.headers.get('Authorization')).toBe(
        `Bearer token-${TEST_USERS.organizer.id}`,
      );
      first.flush(buildPage([buildEvent({ id: 1, name: 'Borrador privado', status: 'DRAFT' })]));
      await settle();
      expect(textOf(page())).toContain('Borrador privado');

      TestBed.inject(AuthService).logout();
      await settle();

      expect(textOf(page())).not.toContain('Borrador privado');
      expect(page().querySelector('app-loading')).not.toBeNull();
      const second = listRequest();
      expect(second.request.headers.has('Authorization')).toBeFalse();
      second.flush(buildPage([buildEvent({ id: 2, name: 'Evento público' })]));
      await settle();

      expect(textOf(page())).toContain('Evento público');
      expect(page().querySelector('a[href="/events/new"]')).toBeNull();
    });

    it('should load the catalog of the new account after switching users', async () => {
      await open('/events', TEST_USERS.organizer);
      listRequest().flush(buildPage([buildEvent({ id: 1, name: 'Borrador de Olga' })]));
      await settle();

      TestBed.inject(AuthService).logout();
      await settle();
      listRequest().flush(buildPage([]));
      signInAs(TEST_USERS.otherOrganizer);
      await settle();

      const request = listRequest();
      expect(request.request.headers.get('Authorization')).toBe(
        `Bearer token-${TEST_USERS.otherOrganizer.id}`,
      );
      request.flush(buildPage([buildEvent({ id: 5, name: 'Borrador de Oscar' })]));
      await settle();

      expect(textOf(page())).toContain('Borrador de Oscar');
      expect(textOf(page())).not.toContain('Borrador de Olga');
    });

    it('should cancel an outdated request when the page changes before it answers', async () => {
      await open('/events');
      listRequest().flush(buildPage([buildEvent()], { total: 30, pages: 4 }));
      await settle();

      await TestBed.inject(Router).navigateByUrl('/events?page=2');
      const outdated = listRequest();
      await TestBed.inject(Router).navigateByUrl('/events?page=3');
      const current = listRequest();

      expect(outdated.cancelled).toBeTrue();
      current.flush(buildPage([buildEvent({ name: 'Página 3' })], { page: 3, pages: 4 }));
      await settle();

      expect(textOf(page())).toContain('Página 3');
    });
  });

  describe('create event button', () => {
    const createButton = () => page().querySelector('a[href="/events/new"]');

    async function openAs(user?: User): Promise<void> {
      await open('/events', user);
      listRequest().flush(buildPage([]));
      await settle();
    }

    it('should be hidden for anonymous users', async () => {
      await openAs();
      expect(createButton()).toBeNull();
    });

    it('should be hidden for ATTENDEE', async () => {
      await openAs(TEST_USERS.attendee);
      expect(createButton()).toBeNull();
    });

    it('should be visible for ORGANIZER', async () => {
      await openAs(TEST_USERS.organizer);
      expect(createButton()).not.toBeNull();
    });

    it('should be visible for ADMIN', async () => {
      await openAs(TEST_USERS.admin);
      expect(createButton()).not.toBeNull();
    });
  });
});
