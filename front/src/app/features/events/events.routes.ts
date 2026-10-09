import { type Routes } from '@angular/router';

import { eventManagerGuard } from '../../core/guards/auth.guards';

export const EVENTS_ROUTES: Routes = [
  {
    path: '',
    title: 'Eventos | Mis Eventos',
    loadComponent: () =>
      import('./pages/event-list-page/event-list-page').then((m) => m.EventListPage),
  },
  {
    path: 'new',
    title: 'Crear evento | Mis Eventos',
    canActivate: [eventManagerGuard],
    loadComponent: () =>
      import('./pages/event-create-page/event-create-page').then((m) => m.EventCreatePage),
  },
  {
    path: ':id',
    title: 'Detalle del evento | Mis Eventos',
    loadComponent: () =>
      import('./pages/event-detail-page/event-detail-page').then((m) => m.EventDetailPage),
  },
  {
    path: ':id/edit',
    title: 'Editar evento | Mis Eventos',
    canActivate: [eventManagerGuard],
    loadComponent: () =>
      import('./pages/event-edit-page/event-edit-page').then((m) => m.EventEditPage),
  },
];
