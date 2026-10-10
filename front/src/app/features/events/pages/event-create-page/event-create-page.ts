import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Router } from '@angular/router';

import { describeApiError, type FieldErrors, toApiError } from '../../../../core/http/api-error';
import { FlashMessageService } from '../../../../core/services/flash-message.service';
import { Alert } from '../../../../shared/components/alert/alert';
import { EventForm } from '../../components/event-form/event-form';
import { type EventPayload } from '../../models/event.model';
import {
  describeImageProgress,
  EventImageError,
  type EventImageSelection,
  EventImagesService,
  NO_IMAGE_CHANGE,
} from '../../services/event-images.service';
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
        [imageStatus]="imageStatus()"
        (imageChange)="image.set($event)"
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
  private readonly images = inject(EventImagesService);

  protected readonly image = signal<EventImageSelection>(NO_IMAGE_CHANGE);
  protected readonly imageStatus = signal<string | null>(null);
  protected readonly submitting = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly fieldErrors = signal<FieldErrors>({});

  protected create(payload: EventPayload): void {
    if (this.submitting()) {
      return;
    }
    this.submitting.set(true);
    this.error.set(null);
    this.events
      .create(payload)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (event) => this.uploadImage(event.id),
        error: (error: unknown) => {
          const apiError = toApiError(error);
          this.submitting.set(false);
          this.fieldErrors.set(apiError.fieldErrors);
          this.error.set(describeApiError(apiError));
        },
      });
  }

  /**
   * The image needs the event id, so it is uploaded after creating the event. If it fails the
   * event is kept and the user is told to add the image from the edit page.
   */
  private uploadImage(eventId: number): void {
    const done = (type: 'success' | 'error', message: string) => {
      this.flashMessages.set(type, message);
      void this.router.navigate(['/events', eventId]);
    };
    if (!this.image().file) {
      done('success', 'Evento creado como borrador.');
      return;
    }
    this.images
      .apply(eventId, this.image())
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (progress) => this.imageStatus.set(describeImageProgress(progress)),
        complete: () => done('success', 'Evento creado como borrador, con su imagen.'),
        error: (error: unknown) =>
          done(
            'error',
            `El evento se creó como borrador, pero la imagen no se pudo guardar: ${imageErrorMessage(error)} Puedes añadirla desde «Editar evento».`,
          ),
      });
  }

  protected cancel(): void {
    void this.router.navigateByUrl('/events');
  }
}

function imageErrorMessage(error: unknown): string {
  return error instanceof EventImageError ? error.message : 'Error inesperado.';
}
