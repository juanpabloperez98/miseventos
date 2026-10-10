import {
  ChangeDetectionStrategy,
  Component,
  computed,
  DestroyRef,
  effect,
  ElementRef,
  inject,
  input,
  output,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';

import { type FieldErrors } from '../../../../core/http/api-error';
import { Button } from '../../../../shared/components/button/button';
import {
  FormField,
  type FormFieldOption,
} from '../../../../shared/components/form-field/form-field';
import { fromColombiaInput, toColombiaInput } from '../../../../shared/utils/date-time';
import { INVALID_CONTROL_SELECTOR } from '../../../../shared/utils/forms';
import { compareWithSibling, integer, notBlank } from '../../../../shared/utils/validators';
import {
  availableStatuses,
  EVENT_LIMITS,
  EVENT_STATUS_LABELS,
  type EventModel,
  type EventStatus,
  type EventUpdatePayload,
} from '../../models/event.model';
import { type EventImageSelection } from '../../services/event-images.service';
import { EventImageField } from '../event-image-field/event-image-field';

/**
 * Create/edit form for events. Presentational: it validates and emits the payload, and the page
 * performs the request. Validation mirrors `EventCreateSchema` / `EventUpdateSchema`. The cover
 * image is reported separately (`imageChange`): it is uploaded once the event exists.
 */
@Component({
  selector: 'app-event-form',
  imports: [ReactiveFormsModule, FormField, Button, EventImageField],
  templateUrl: './event-form.html',
  styleUrl: './event-form.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class EventForm {
  /** Event being edited. When absent the form creates a new event. */
  readonly event = input<EventModel | null>(null);
  readonly submitting = input(false);
  /** Field errors returned by the API (422), keyed by payload field. */
  readonly serverErrors = input<FieldErrors>({});
  readonly submitLabel = input('Guardar');
  /** Progress of the cover image upload, shown under the image picker. */
  readonly imageStatus = input<string | null>(null);

  readonly save = output<EventUpdatePayload>();
  /** Cover image chosen by the user; the page applies it after saving the event. */
  readonly imageChange = output<EventImageSelection>();
  readonly cancelled = output();

  private readonly host = inject<ElementRef<HTMLElement>>(ElementRef);
  protected readonly limits = EVENT_LIMITS;

  private readonly fb = inject(NonNullableFormBuilder);

  protected readonly form = this.fb.group({
    name: ['', [Validators.required, notBlank, Validators.maxLength(EVENT_LIMITS.nameMaxLength)]],
    description: ['', [Validators.maxLength(EVENT_LIMITS.descriptionMaxLength)]],
    location: [
      '',
      [Validators.required, notBlank, Validators.maxLength(EVENT_LIMITS.locationMaxLength)],
    ],
    start_date: ['', [Validators.required]],
    end_date: ['', [Validators.required, compareWithSibling('start_date', 'after', 'dateOrder')]],
    capacity: this.fb.control<number | null>(null, [
      Validators.required,
      integer,
      Validators.min(1),
      Validators.max(EVENT_LIMITS.capacityMax),
    ]),
    status: ['' as EventStatus | ''],
  });

  protected readonly statusOptions = computed<FormFieldOption[]>(() => {
    const event = this.event();
    return event
      ? availableStatuses(event.status).map((status) => ({
          value: status,
          label: EVENT_STATUS_LABELS[status],
        }))
      : [];
  });

  protected readonly messages = {
    dateOrder: 'La fecha de finalización debe ser posterior a la de inicio.',
    min: 'La capacidad debe ser al menos 1.',
    max: `La capacidad no puede superar ${EVENT_LIMITS.capacityMax.toLocaleString('es')}.`,
  };

  constructor() {
    this.form.controls.start_date.valueChanges
      .pipe(takeUntilDestroyed(inject(DestroyRef)))
      .subscribe(() => this.form.controls.end_date.updateValueAndValidity());

    effect(() => {
      const event = this.event();
      this.form.reset(
        event
          ? {
              name: event.name,
              description: event.description ?? '',
              location: event.location,
              start_date: toColombiaInput(event.start_date),
              end_date: toColombiaInput(event.end_date),
              capacity: event.capacity,
              status: event.status,
            }
          : undefined,
      );
    });

    effect(() => {
      for (const [field, messages] of Object.entries(this.serverErrors())) {
        const control = this.form.get(field);
        if (control && messages.length > 0) {
          control.setErrors({ server: messages.join(' ') });
          control.markAsTouched();
        }
      }
    });
  }

  protected submit(): void {
    if (this.submitting()) {
      return;
    }
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      this.focusFirstInvalid();
      return;
    }
    const value = this.form.getRawValue();
    const description = value.description.trim();
    const payload: EventUpdatePayload = {
      name: value.name.trim(),
      description: description === '' ? null : description,
      location: value.location.trim(),
      start_date: fromColombiaInput(value.start_date),
      end_date: fromColombiaInput(value.end_date),
      capacity: Number(value.capacity),
    };
    const event = this.event();
    // Only send the status when it changes; omitting it keeps the current one.
    if (event && value.status && value.status !== event.status) {
      payload.status = value.status;
    }
    this.save.emit(payload);
  }

  private focusFirstInvalid(): void {
    this.host.nativeElement.querySelector<HTMLElement>(INVALID_CONTROL_SELECTOR)?.focus();
  }
}
