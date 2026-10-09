import { type Routes } from '@angular/router';

import { authGuard } from '../../core/guards/auth.guards';

export const PROFILE_ROUTES: Routes = [
  {
    path: '',
    title: 'Mi perfil | Mis Eventos',
    canActivate: [authGuard],
    loadComponent: () => import('./pages/profile-page/profile-page').then((m) => m.ProfilePage),
  },
];
