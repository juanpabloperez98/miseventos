import {
  ChangeDetectionStrategy,
  Component,
  computed,
  DestroyRef,
  inject,
  input,
  numberAttribute,
  signal,
} from '@angular/core';
import { takeUntilDestroyed, toObservable, toSignal } from '@angular/core/rxjs-interop';
import { Router, RouterLink } from '@angular/router';
import { switchMap } from 'rxjs';

import { AuthorizationService } from '../../../../core/auth/authorization.service';
import { describeApiError, type FieldErrors, toApiError } from '../../../../core/http/api-error';
import { FlashMessageService } from '../../../../core/services/flash-message.service';
import { Alert } from '../../../../shared/components/alert/alert';
import { Button } from '../../../../shared/components/button/button';
import { EmptyState } from '../../../../shared/components/empty-state/empty-state';
import { ErrorState } from '../../../../shared/components/error-state/error-state';
import { Loading } from '../../../../shared/components/loading/loading';
import { LOADING, toRequestState } from '../../../../shared/utils/request-state';
import { EventForm } from '../../components/event-form/event-form';
import { type EventUpdatePayload, isEventEditable } from '../../models/event.model';
import { EventsService } from '../../services/events.service';

/**
 * Edits an event with `PUT /events/{id}`. The route guard only lets event managers in; ownership and
 * status are checked here once the event is loaded, and the backend checks them again on save.
 */
@Component({
  selector: 'app-event-edit-page',
  imports: [RouterLink, Alert, Button, EmptyState, ErrorState, EventForm, Loading],
  templateUrl: './event-edit-page.html',
  styleUrl: '../event-form-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class EventEditPage {
  readonly id = input.required({ transform: numberAttribute });

  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);
  private readonly events = inject(EventsService);
  private readonly authorization = inject(AuthorizationService);
  private readonly flashMessages = inject(FlashMessageService);

  private readonly reloads = signal(0);

  protected readonly state = toSignal(
    toObservable(computed(() => ({ id: this.id(), reload: this.reloads() }))).pipe(
      switchMap(({ id }) => this.events.get(id).pipe(toRequestState())),
    ),
    { initialValue: LOADING },
  );

  protected readonly submitting = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly fieldErrors = signal<FieldErrors>({});

  /** Why the loaded event cannot be edited by the current user, if that is the case. */
  protected readonly blockedReason = computed(() => {
    const state = this.state();
    if (state.status !== 'success') {
      return null;
    }
    if (!this.authorization.canManageEvent(state.data.created_by)) {
      return 'Solo quien creó el evento o un administrador puede editarlo.';
    }
    if (!isEventEditable(state.data)) {
      return 'Los eventos cancelados o finalizados no se pueden modificar.';
    }
    return null;
  });

  protected readonly describe = describeApiError;

  protected retry(): void {
    this.reloads.update((value) => value + 1);
  }

  protected update(payload: EventUpdatePayload): void {
    const id = this.id();
    this.submitting.set(true);
    this.error.set(null);
    this.events
      .update(id, payload)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.flashMessages.set('success', 'Los cambios se guardaron correctamente.');
          void this.router.navigate(['/events', id]);
        },
        error: (error: unknown) => {
          const apiError = toApiError(error);
          this.submitting.set(false);
          this.fieldErrors.set(apiError.fieldErrors);
          this.error.set(describeApiError(apiError));
        },
      });
  }

  protected cancel(): void {
    void this.router.navigate(['/events', this.id()]);
  }
}
