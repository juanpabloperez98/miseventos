import { type Route, type Routes, type UrlMatchResult, type UrlSegment } from '@angular/router';

import { authGuard, canManageEventsMatch, eventManagerGuard } from '../../core/guards/auth.guards';

const EVENT_ID = /^[1-9]\d*$/;

/**
 * Matches `<id>` (or `<id>/<suffix>`) only when the id is numeric, and exposes it as the `id`
 * param. Any other segment (`new`, `create`, typos...) is never taken as an event id, so it never
 * reaches the detail page nor triggers `GET /events/NaN`; unknown paths fall through to the 404 page.
 */
function eventIdMatcher(suffix?: string) {
  return (segments: UrlSegment[]): UrlMatchResult | null => {
    const expectedLength = suffix ? 2 : 1;
    const [id, last] = segments;
    if (
      segments.length !== expectedLength ||
      !EVENT_ID.test(id.path) ||
      (suffix !== undefined && last.path !== suffix)
    ) {
      return null;
    }
    return { consumed: segments, posParams: { id } };
  };
}

function sessionMatcher(kind: 'new' | 'edit') {
  return (segments: UrlSegment[]): UrlMatchResult | null => {
    const [id, sessions, third, fourth] = segments;
    const matches =
      kind === 'new'
        ? segments.length === 3 && third.path === 'new'
        : segments.length === 4 && EVENT_ID.test(third.path) && fourth.path === 'edit';
    if (!matches || !EVENT_ID.test(id.path) || sessions.path !== 'sessions') {
      return null;
    }
    return {
      consumed: segments,
      posParams: kind === 'new' ? { id } : { id, sessionId: third },
    };
  };
}

/**
 * Event management page plus its "access denied" twin at the same URL:
 *
 * 1. Anonymous user: the page does not match (`canMatch`), the twin's `authGuard` sends them to
 *    login with `returnUrl` → after signing in they come back to this URL.
 * 2. Authenticated without permission (ATTENDEE): the twin renders "access denied" at the requested
 *    URL; the session is kept and there is no redirect.
 * 3. ADMIN / ORGANIZER: the page matches. `eventManagerGuard` re-checks session and role, and lets
 *    `SessionExpiryRedirect` recognize the page as protected.
 *
 * Ownership of a specific event is checked by the edit page, and every operation by the backend.
 */
function managerPage(page: Route): Route[] {
  const url: Pick<Route, 'path' | 'matcher'> = page.matcher
    ? { matcher: page.matcher }
    : { path: page.path };
  return [
    { ...page, canMatch: [canManageEventsMatch], canActivate: [eventManagerGuard] },
    {
      ...url,
      title: 'Acceso denegado | Mis Eventos',
      canActivate: [authGuard],
      data: { reason: 'Tu cuenta no tiene permiso para gestionar eventos.' },
      loadComponent: () => import('../forbidden').then((m) => m.ForbiddenPage),
    },
  ];
}

export const EVENTS_ROUTES: Routes = [
  {
    path: '',
    title: 'Eventos | Mis Eventos',
    loadComponent: () =>
      import('./pages/event-list-page/event-list-page').then((m) => m.EventListPage),
  },
  ...managerPage({
    path: 'new',
    title: 'Crear evento | Mis Eventos',
    loadComponent: () =>
      import('./pages/event-create-page/event-create-page').then((m) => m.EventCreatePage),
  }),
  { path: 'create', pathMatch: 'full', redirectTo: 'new' },
  {
    matcher: eventIdMatcher(),
    title: 'Detalle del evento | Mis Eventos',
    loadComponent: () =>
      import('./pages/event-detail-page/event-detail-page').then((m) => m.EventDetailPage),
  },
  ...managerPage({
    matcher: eventIdMatcher('edit'),
    title: 'Editar evento | Mis Eventos',
    loadComponent: () =>
      import('./pages/event-edit-page/event-edit-page').then((m) => m.EventEditPage),
  }),
  ...managerPage({
    matcher: sessionMatcher('new'),
    title: 'Nueva sesión | Mis Eventos',
    loadComponent: () =>
      import('./pages/session-form-page/session-form-page').then((m) => m.SessionFormPage),
  }),
  ...managerPage({
    matcher: sessionMatcher('edit'),
    title: 'Editar sesión | Mis Eventos',
    loadComponent: () =>
      import('./pages/session-form-page/session-form-page').then((m) => m.SessionFormPage),
  }),
];
