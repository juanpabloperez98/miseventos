import { computed, inject, Injectable } from '@angular/core';

import { type UserRole } from './auth.models';
import { AuthService } from './auth.service';

const EVENT_MANAGER_ROLES: readonly UserRole[] = ['ADMIN', 'ORGANIZER'];

/**
 * Centralized UI permissions. Mirrors the backend RBAC rules so the interface only offers actions the
 * user can perform. The backend remains the authority: it re-checks every request against the role
 * stored in its database.
 */
@Injectable({ providedIn: 'root' })
export class AuthorizationService {
  private readonly auth = inject(AuthService);

  readonly canCreateEvents = computed(() => {
    const role = this.auth.user()?.role;
    return role !== undefined && EVENT_MANAGER_ROLES.includes(role);
  });

  canManageEvent(ownerId: number): boolean {
    const user = this.auth.user();
    if (!user) {
      return false;
    }
    return user.role === 'ADMIN' || (user.role === 'ORGANIZER' && user.id === ownerId);
  }
}
