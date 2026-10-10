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
import { catchError, map, type Observable, of, startWith, switchMap } from 'rxjs';

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
import { ResponsiveImagePipe } from '../../../../shared/pipes/responsive-image.pipe';
import { RegistrationsService } from '../../../registrations';
import { LOADING, type RequestState, toRequestState } from '../../../../shared/utils/request-state';
import { EventStatusBadge } from '../../components/event-status-badge/event-status-badge';
import {
  RegistrationPanel,
  type RegistrationStatus,
} from '../../components/registration-panel/registration-panel';
import { SessionList } from '../../components/session-list/session-list';
import { type EventModel, isEventEditable, removalAction } from '../../models/event.model';
import { type EventSession } from '../../models/session.model';
import { EventsService } from '../../services/events.service';
import { SessionsService } from '../../services/sessions.service';

type Membership = 'anonymous' | 'checking' | 'registered' | 'not-registered';

const ALREADY_REGISTERED = 'User is already registered to this event';

@Component({
  selector: 'app-event-detail-page',
  imports: [
    RouterLink,
    DecimalPipe,
    Alert,
    Button,
    DateRangePipe,
    ResponsiveImagePipe,
    EmptyState,
    ErrorState,
    EventStatusBadge,
    Loading,
    RegistrationPanel,
    SessionList,
  ],
  templateUrl: './event-detail-page.html',
  styleUrl: './event-detail-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class EventDetailPage {
  readonly id = input.required({ transform: numberAttribute });

  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);
  private readonly events = inject(EventsService);
  private readonly registrations = inject(RegistrationsService);
  private readonly sessionsService = inject(SessionsService);
  private readonly auth = inject(AuthService);
  private readonly authorization = inject(AuthorizationService);
  private readonly flashMessages = inject(FlashMessageService);

  private readonly eventReloads = signal(0);
  private readonly sessionReloads = signal(0);
  private readonly userId = computed(() => this.auth.user()?.id ?? null);

  private readonly viewKey = computed(() => ({ id: this.id(), user: this.userId() }));
  private readonly initialNotice = this.flashMessages.consume();

  protected readonly notice = linkedSignal<unknown, FlashMessage | null>({
    source: this.viewKey,
    computation: (_key, previous) => (previous === undefined ? this.initialNotice : null),
  });
  protected readonly confirmingRemoval = linkedSignal({
    source: this.viewKey,
    computation: () => false,
  });
  protected readonly removalError = linkedSignal<unknown, string | null>({
    source: this.viewKey,
    computation: () => null,
  });
  protected readonly removing = signal(false);

  protected readonly registering = signal(false);
  protected readonly registrationError = linkedSignal<unknown, string | null>({
    source: this.viewKey,
    computation: () => null,
  });
  private readonly registeredNow = linkedSignal({ source: this.viewKey, computation: () => false });

  private readonly membership = toSignal(
    toObservable(this.viewKey).pipe(
      switchMap(({ id, user }) =>
        user === null ? of<Membership>('anonymous') : this.loadMembership(id),
      ),
    ),
    { initialValue: 'checking' as Membership },
  );

  private readonly loadedEvent = toSignal(
    toObservable(
      computed(() => ({ id: this.id(), user: this.userId(), r: this.eventReloads() })),
    ).pipe(switchMap(({ id }) => this.events.get(id).pipe(toRequestState()))),
    { initialValue: LOADING },
  );

  protected readonly eventState = linkedSignal<RequestState<EventModel>>(() => this.loadedEvent());

  private readonly loadedSessions = toSignal(
    toObservable(
      computed(() => ({ id: this.id(), user: this.userId(), r: this.sessionReloads() })),
    ).pipe(switchMap(({ id }) => this.events.getSessions(id).pipe(toRequestState()))),
    { initialValue: LOADING },
  );

  protected readonly sessionsState = linkedSignal<RequestState<EventSession[]>>(() =>
    this.loadedSessions(),
  );

  protected readonly removingSessionId = signal<number | null>(null);
  protected readonly sessionError = linkedSignal<unknown, string | null>({
    source: this.viewKey,
    computation: () => null,
  });

  protected readonly event = computed(() => {
    const state = this.eventState();
    return state.status === 'success' ? state.data : null;
  });

  protected readonly canEdit = computed(() => {
    const event = this.event();
    return !!event && this.authorization.canManageEvent(event.created_by) && isEventEditable(event);
  });

  protected readonly sessionManagementNote = computed(() => {
    const event = this.event();
    if (!event || !this.authorization.canCreateEvents() || this.canEdit()) {
      return null;
    }
    if (!this.authorization.canManageEvent(event.created_by)) {
      return 'Solo quien creó este evento o un administrador puede gestionar sus sesiones.';
    }
    return event.status === 'CANCELLED'
      ? 'El evento está cancelado: sus sesiones ya no se pueden añadir, editar ni eliminar.'
      : 'El evento ha finalizado: sus sesiones ya no se pueden añadir, editar ni eliminar.';
  });

  protected readonly removal = computed(() => {
    const event = this.event();
    return event && this.authorization.canManageEvent(event.created_by)
      ? removalAction(event)
      : null;
  });

  protected readonly registrationStatus = computed<RegistrationStatus>(() => {
    const event = this.event();
    const membership = this.membership();
    if (membership === 'registered' || this.registeredNow()) {
      return 'registered';
    }
    if (!event || event.status !== 'PUBLISHED') {
      return 'closed';
    }
    if (membership === 'anonymous' || membership === 'checking') {
      return membership;
    }
    return 'available';
  });

  protected readonly returnUrl = computed(() => `/events/${this.id()}`);

  protected readonly describe = describeApiError;

  protected retryEvent(): void {
    this.eventReloads.update((value) => value + 1);
  }

  protected retrySessions(): void {
    this.sessionReloads.update((value) => value + 1);
  }

  protected removeSession(session: EventSession): void {
    if (this.removingSessionId() !== null) {
      return;
    }
    this.removingSessionId.set(session.id);
    this.sessionError.set(null);
    this.sessionsService
      .remove(session.id)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.removingSessionId.set(null);
          this.sessionsState.update((state) =>
            state.status === 'success'
              ? { status: 'success', data: state.data.filter(({ id }) => id !== session.id) }
              : state,
          );
          this.notice.set({ type: 'success', text: `Se eliminó la sesión «${session.title}».` });
        },
        error: (error: unknown) => {
          this.removingSessionId.set(null);
          this.sessionError.set(describeApiError(toApiError(error)));
        },
      });
  }

  protected register(): void {
    const eventId = this.id();
    if (this.registering() || this.registrationStatus() !== 'available') {
      return;
    }
    this.registering.set(true);
    this.registrationError.set(null);
    this.registrations
      .register(eventId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.registering.set(false);
          // Ignore a late answer if the user already moved to another event.
          if (this.id() === eventId) {
            this.registeredNow.set(true);
            this.notice.set({ type: 'success', text: 'Te has inscrito en el evento.' });
          }
        },
        error: (error: unknown) => {
          this.registering.set(false);
          if (this.id() !== eventId) {
            return;
          }
          const apiError = toApiError(error);
          if (apiError.status === 409 && apiError.serverMessage === ALREADY_REGISTERED) {
            this.registeredNow.set(true);
            this.notice.set({ type: 'info', text: 'Ya estabas inscrito en este evento.' });
            return;
          }
          this.registrationError.set(describeApiError(apiError));
        },
      });
  }

  private loadMembership(eventId: number): Observable<Membership> {
    return this.registrations.listMyEvents().pipe(
      map((events): Membership =>
        events.some((event) => event.id === eventId) ? 'registered' : 'not-registered',
      ),
      startWith<Membership>('checking'),
      catchError(() => of<Membership>('not-registered')),
    );
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
