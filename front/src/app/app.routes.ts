import { type Routes } from '@angular/router';

import { MainLayout } from './layout/layouts/main-layout/main-layout';

/**
 * Application route tree.
 *
 * The layout is part of the initial bundle because every page renders inside it. Each feature is
 * lazy loaded: it exposes its own `<feature>.routes.ts` and is registered here with `loadChildren`
 * (or `loadComponent` for a single standalone page).
 */
export const routes: Routes = [
  {
    path: '',
    component: MainLayout,
    children: [
      { path: '', pathMatch: 'full', redirectTo: 'events' },
      {
        path: 'events',
        loadChildren: () => import('./features/events/events.routes').then((m) => m.EVENTS_ROUTES),
      },
      {
        path: 'auth',
        loadChildren: () => import('./features/auth/auth.routes').then((m) => m.AUTH_ROUTES),
      },
      {
        path: 'profile',
        loadChildren: () =>
          import('./features/profile/profile.routes').then((m) => m.PROFILE_ROUTES),
      },
      {
        // Access denied: rendered by guards with skipLocationChange (the URL stays the requested one).
        path: 'forbidden',
        title: 'Acceso denegado | Mis Eventos',
        loadComponent: () =>
          import('./features/forbidden/pages/forbidden-page/forbidden-page').then(
            (m) => m.ForbiddenPage,
          ),
      },
      {
        path: '**',
        title: 'Página no encontrada | Mis Eventos',
        loadComponent: () =>
          import('./features/not-found/pages/not-found-page/not-found-page').then(
            (m) => m.NotFoundPage,
          ),
      },
    ],
  },
];
