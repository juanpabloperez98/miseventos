import { DecimalPipe } from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  DestroyRef,
  inject,
  input,
  linkedSignal,
  numberAttribute,
  signal,
} from '@angular/core';
import { takeUntilDestroyed, toObservable, toSignal } from '@angular/core/rxjs-interop';
import { Router, RouterLink } from '@angular/router';
import { switchMap } from 'rxjs';

import { AuthService } from '../../../../core/auth/auth.service';
import { AuthorizationService } from '../../../../core/auth/authorization.service';
import { describeApiError, toApiError } from '../../../../core/http/api-error';
import {
  type FlashMessage,
  FlashMessageService,
} from '../../../../core/services/flash-message.service';
import { Alert } from '../../../../shared/components/alert/alert';
import { Button } from '../../../../shared/components/button/button';
import { EmptyState } from '../../../../shared/components/empty-state/empty-state';
import { ErrorState } from '../../../../shared/components/error-state/error-state';
import { Loading } from '../../../../shared/components/loading/loading';
import { DateRangePipe } from '../../../../shared/pipes/date-range.pipe';
import { LOADING, type RequestState, toRequestState } from '../../../../shared/utils/request-state';
import { EventStatusBadge } from '../../components/event-status-badge/event-status-badge';
import { SessionList } from '../../components/session-list/session-list';
import { type EventModel, isEventEditable, removalAction } from '../../models/event.model';
import { EventsService } from '../../services/events.service';

/**
 * Event detail. The event and its sessions come from two endpoints, requested in parallel and
 * rendered independently: a failure loading sessions does not hide the event.
 */
@Component({
  selector: 'app-event-detail-page',
  imports: [
    RouterLink,
    DecimalPipe,
    Alert,
    Button,
    DateRangePipe,
    EmptyState,
    ErrorState,
    EventStatusBadge,
    Loading,
    SessionList,
  ],
  templateUrl: './event-detail-page.html',
  styleUrl: './event-detail-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class EventDetailPage {
  /** `:id` route param. */
  readonly id = input.required({ transform: numberAttribute });

  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);
  private readonly events = inject(EventsService);
  private readonly auth = inject(AuthService);
  private readonly authorization = inject(AuthorizationService);
  private readonly flashMessages = inject(FlashMessageService);

  protected readonly notice = signal<FlashMessage | null>(this.flashMessages.consume());
  protected readonly confirmingRemoval = signal(false);
  protected readonly removing = signal(false);
  protected readonly removalError = signal<string | null>(null);

  private readonly eventReloads = signal(0);
  private readonly sessionReloads = signal(0);
  /** Visibility depends on the user, so the data is reloaded when the session changes. */
  private readonly userId = computed(() => this.auth.user()?.id ?? null);

  private readonly loadedEvent = toSignal(
    toObservable(
      computed(() => ({ id: this.id(), user: this.userId(), r: this.eventReloads() })),
    ).pipe(switchMap(({ id }) => this.events.get(id).pipe(toRequestState()))),
    { initialValue: LOADING },
  );

  /** Writable copy, so a cancellation can update the view with the event returned by the API. */
  protected readonly eventState = linkedSignal<RequestState<EventModel>>(() => this.loadedEvent());

  protected readonly sessionsState = toSignal(
    toObservable(
      computed(() => ({ id: this.id(), user: this.userId(), r: this.sessionReloads() })),
    ).pipe(switchMap(({ id }) => this.events.getSessions(id).pipe(toRequestState()))),
    { initialValue: LOADING },
  );

  protected readonly event = computed(() => {
    const state = this.eventState();
    return state.status === 'success' ? state.data : null;
  });

  protected readonly canEdit = computed(() => {
    const event = this.event();
    return !!event && this.authorization.canManageEvent(event.created_by) && isEventEditable(event);
  });

  protected readonly removal = computed(() => {
    const event = this.event();
    return event && this.authorization.canManageEvent(event.created_by)
      ? removalAction(event)
      : null;
  });

  protected readonly describe = describeApiError;

  protected retryEvent(): void {
    this.eventReloads.update((value) => value + 1);
  }

  protected retrySessions(): void {
    this.sessionReloads.update((value) => value + 1);
  }

  protected askRemoval(): void {
    this.removalError.set(null);
    this.confirmingRemoval.set(true);
  }

  protected confirmRemoval(): void {
    const event = this.event();
    if (!event || this.removing()) {
      return;
    }
    this.removing.set(true);
    this.events
      .remove(event.id)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (cancelled) => {
          this.removing.set(false);
          this.confirmingRemoval.set(false);
          if (cancelled) {
            this.eventState.set({ status: 'success', data: cancelled });
            this.notice.set({ type: 'success', text: 'El evento ha sido cancelado.' });
          } else {
            this.flashMessages.set('success', `Se eliminó el borrador «${event.name}».`);
            void this.router.navigateByUrl('/events');
          }
        },
        error: (error: unknown) => {
          this.removing.set(false);
          this.removalError.set(describeApiError(toApiError(error)));
        },
      });
  }
}
