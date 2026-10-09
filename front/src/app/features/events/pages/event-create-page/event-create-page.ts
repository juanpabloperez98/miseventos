import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Router } from '@angular/router';

import { describeApiError, type FieldErrors, toApiError } from '../../../../core/http/api-error';
import { FlashMessageService } from '../../../../core/services/flash-message.service';
import { Alert } from '../../../../shared/components/alert/alert';
import { EventForm } from '../../components/event-form/event-form';
import { type EventPayload } from '../../models/event.model';
import { EventsService } from '../../services/events.service';

@Component({
  selector: 'app-event-create-page',
  imports: [Alert, EventForm],
  template: `
    <header class="page-header">
      <h1>Crear evento</h1>
      <p class="page-header__lead">
        El evento se guardará como borrador. Podrás publicarlo después desde «Editar evento».
      </p>
    </header>

    <div class="panel">
      @if (error(); as message) {
        <app-alert class="panel__alert" type="error">{{ message }}</app-alert>
      }
      <app-event-form
        submitLabel="Crear evento"
        [submitting]="submitting()"
        [serverErrors]="fieldErrors()"
        (save)="create($event)"
        (cancelled)="cancel()"
      />
    </div>
  `,
  styleUrl: '../event-form-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class EventCreatePage {
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);
  private readonly events = inject(EventsService);
  private readonly flashMessages = inject(FlashMessageService);

  protected readonly submitting = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly fieldErrors = signal<FieldErrors>({});

  protected create(payload: EventPayload): void {
    this.submitting.set(true);
    this.error.set(null);
    this.events
      .create(payload)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (event) => {
          this.flashMessages.set('success', 'Evento creado como borrador.');
          void this.router.navigate(['/events', event.id]);
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
    void this.router.navigateByUrl('/events');
  }
}
