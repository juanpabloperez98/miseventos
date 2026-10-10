import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';
import { of, switchMap } from 'rxjs';

import { ROLE_LABELS } from '../../../../core/auth/auth.models';
import { AuthService } from '../../../../core/auth/auth.service';
import { describeApiError } from '../../../../core/http/api-error';
import { Button } from '../../../../shared/components/button/button';
import { EmptyState } from '../../../../shared/components/empty-state/empty-state';
import { ErrorState } from '../../../../shared/components/error-state/error-state';
import { Loading } from '../../../../shared/components/loading/loading';
import { LOADING, type RequestState, toRequestState } from '../../../../shared/utils/request-state';
import { EventCard, type EventModel } from '../../../events';
import { RegistrationsService } from '../../../registrations';

const SESSION_ENDED: RequestState<EventModel[]> = {
  status: 'error',
  error: { status: 401, serverMessage: null, fieldErrors: {} },
};

@Component({
  selector: 'app-profile-page',
  imports: [RouterLink, Button, EmptyState, ErrorState, EventCard, Loading],
  templateUrl: './profile-page.html',
  styleUrl: './profile-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ProfilePage {
  private readonly auth = inject(AuthService);
  private readonly registrations = inject(RegistrationsService);

  protected readonly user = this.auth.user;
  protected readonly roleLabel = computed(() => {
    const user = this.user();
    return user ? ROLE_LABELS[user.role] : '';
  });

  private readonly reloads = signal(0);

  protected readonly state = toSignal(
    toObservable(computed(() => ({ user: this.user()?.id, reload: this.reloads() }))).pipe(
      switchMap(({ user }) =>
        user === undefined
          ? of(SESSION_ENDED)
          : this.registrations.listMyEvents().pipe(toRequestState()),
      ),
    ),
    { initialValue: LOADING },
  );

  protected readonly describe = describeApiError;

  protected retry(): void {
    this.reloads.update((value) => value + 1);
  }
}
