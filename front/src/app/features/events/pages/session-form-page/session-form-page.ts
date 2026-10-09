import { HttpErrorResponse } from '@angular/common/http';
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
import { forkJoin, map, type Observable, of, switchMap } from 'rxjs';

import { AuthorizationService } from '../../../../core/auth/authorization.service';
import { describeApiError, type FieldErrors, toApiError } from '../../../../core/http/api-error';
import { FlashMessageService } from '../../../../core/services/flash-message.service';
import { Alert } from '../../../../shared/components/alert/alert';
import { Button } from '../../../../shared/components/button/button';
import { EmptyState } from '../../../../shared/components/empty-state/empty-state';
import { ErrorState } from '../../../../shared/components/error-state/error-state';
import { Loading } from '../../../../shared/components/loading/loading';
import { LOADING, toRequestState } from '../../../../shared/utils/request-state';
import { SessionForm } from '../../components/session-form/session-form';
import { type EventModel, isEventEditable } from '../../models/event.model';
import { type EventSession, type SessionPayload } from '../../models/session.model';
import { type Speaker } from '../../models/speaker.model';
import { EventsService } from '../../services/events.service';
import { SessionsService } from '../../services/sessions.service';
import { SpeakersService } from '../../services/speakers.service';

interface SessionFormData {
  event: EventModel;
  session: EventSession | null;
  speakers: Speaker[];
}

/**
 * Creates (`/events/:id/sessions/new`) or edits (`/events/:id/sessions/:sessionId/edit`) a session.
 * The route only matches for event managers; ownership and event status are checked here once the
 * event is loaded, and the backend checks them again on save.
 */
@Component({
  selector: 'app-session-form-page',
  imports: [RouterLink, Alert, Button, EmptyState, ErrorState, Loading, SessionForm],
  templateUrl: './session-form-page.html',
  styleUrl: '../event-form-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SessionFormPage {
  /** Event id (`:id`). */
  readonly id = input.required({ transform: numberAttribute });
  /** Session id (`:sessionId`), only when editing. */
  readonly sessionId = input<number | undefined, unknown>(undefined, {
    transform: (value: unknown) => (value === undefined ? undefined : numberAttribute(value)),
  });

  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);
  private readonly events = inject(EventsService);
  private readonly sessions = inject(SessionsService);
  private readonly speakersService = inject(SpeakersService);
  private readonly authorization = inject(AuthorizationService);
  private readonly flashMessages = inject(FlashMessageService);

  private readonly reloads = signal(0);

  protected readonly isEdit = computed(() => this.sessionId() !== undefined);

  /** Event, session (edit only) and speakers, requested in parallel. */
  protected readonly state = toSignal(
    toObservable(
      computed(() => ({ id: this.id(), sessionId: this.sessionId(), r: this.reloads() })),
    ).pipe(switchMap(({ id, sessionId }) => this.load(id, sessionId).pipe(toRequestState()))),
    { initialValue: LOADING },
  );

  protected readonly submitting = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly fieldErrors = signal<FieldErrors>({});

  /** Why the current user cannot manage this event's sessions, if that is the case. */
  protected readonly blockedReason = computed(() => {
    const state = this.state();
    if (state.status !== 'success') {
      return null;
    }
    if (!this.authorization.canManageEvent(state.data.event.created_by)) {
      return 'Solo quien creó el evento o un administrador puede gestionar sus sesiones.';
    }
    if (!isEventEditable(state.data.event)) {
      return 'Las sesiones de eventos cancelados o finalizados no se pueden modificar.';
    }
    return null;
  });

  protected readonly describe = describeApiError;

  protected retry(): void {
    this.reloads.update((value) => value + 1);
  }

  protected save(payload: SessionPayload): void {
    const eventId = this.id();
    const sessionId = this.sessionId();
    this.submitting.set(true);
    this.error.set(null);
    const request =
      sessionId === undefined
        ? this.sessions.create(eventId, payload)
        : this.sessions.update(sessionId, payload);

    request.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: () => {
        this.flashMessages.set(
          'success',
          sessionId === undefined ? 'Sesión creada.' : 'Los cambios de la sesión se guardaron.',
        );
        void this.router.navigate(['/events', eventId]);
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

  private load(eventId: number, sessionId: number | undefined): Observable<SessionFormData> {
    const session$: Observable<EventSession | null> =
      sessionId === undefined
        ? of(null)
        : this.sessions.get(sessionId).pipe(
            map((session) => {
              if (session.event_id !== eventId) {
                // The URL mixes a session with another event: same answer as the API (404).
                throw new HttpErrorResponse({
                  status: 404,
                  error: { message: 'Session not found' },
                });
              }
              return session;
            }),
          );
    return forkJoin({
      event: this.events.get(eventId),
      session: session$,
      speakers: this.speakersService.listAll(),
    });
  }
}
