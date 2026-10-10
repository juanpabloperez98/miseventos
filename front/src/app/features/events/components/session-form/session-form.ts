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
import { takeUntilDestroyed, toSignal } from '@angular/core/rxjs-interop';
import {
  type AbstractControl,
  NonNullableFormBuilder,
  ReactiveFormsModule,
  type ValidationErrors,
  Validators,
} from '@angular/forms';

import { type FieldErrors } from '../../../../core/http/api-error';
import { Button } from '../../../../shared/components/button/button';
import {
  FormField,
  type FormFieldOption,
} from '../../../../shared/components/form-field/form-field';
import { DateRangePipe } from '../../../../shared/pipes/date-range.pipe';
import { INVALID_CONTROL_SELECTOR } from '../../../../shared/utils/forms';
import { fromColombiaInput, toColombiaInput } from '../../../../shared/utils/date-time';
import { compareWithSibling, integer, notBlank } from '../../../../shared/utils/validators';
import { type EventModel } from '../../models/event.model';
import { type EventSession, SESSION_LIMITS, type SessionPayload } from '../../models/session.model';
import { type Speaker } from '../../models/speaker.model';

@Component({
  selector: 'app-session-form',
  imports: [ReactiveFormsModule, Button, DateRangePipe, FormField],
  templateUrl: './session-form.html',
  styleUrl: '../event-form/event-form.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SessionForm {
  readonly event = input.required<EventModel>();
  readonly session = input<EventSession | null>(null);
  readonly speakers = input<readonly Speaker[]>([]);
  readonly submitting = input(false);
  readonly serverErrors = input<FieldErrors>({});
  readonly submitLabel = input('Guardar');

  readonly save = output<SessionPayload>();
  readonly cancelled = output();

  private readonly host = inject<ElementRef<HTMLElement>>(ElementRef);
  private readonly fb = inject(NonNullableFormBuilder);
  protected readonly limits = SESSION_LIMITS;

  protected readonly bounds = computed(() => ({
    min: toColombiaInput(this.event().start_date),
    max: toColombiaInput(this.event().end_date),
  }));

  protected readonly maxCapacity = computed(() =>
    Math.min(this.event().capacity, SESSION_LIMITS.capacityMax),
  );

  private readonly withinEventCapacity = (
    control: AbstractControl<number | null>,
  ): ValidationErrors | null => {
    const value = control.value;
    if (value === null || String(value) === '') {
      // Also avoids reading the `event` input while the form is being built.
      return null;
    }
    const max = this.maxCapacity();
    return Number(value) > max ? { eventCapacity: { max } } : null;
  };

  private readonly withinEvent = (control: AbstractControl<string>): ValidationErrors | null => {
    const value = control.value;
    if (!value) {
      // Also avoids reading the `event` input while the form is being built.
      return null;
    }
    const { min, max } = this.bounds();
    return value < min || value > max ? { outsideEvent: true } : null;
  };

  protected readonly form = this.fb.group({
    title: [
      '',
      [Validators.required, notBlank, Validators.maxLength(SESSION_LIMITS.titleMaxLength)],
    ],
    description: ['', [Validators.maxLength(SESSION_LIMITS.descriptionMaxLength)]],
    start_time: ['', [Validators.required, this.withinEvent]],
    end_time: [
      '',
      [
        Validators.required,
        this.withinEvent,
        compareWithSibling('start_time', 'after', 'timeOrder'),
      ],
    ],
    capacity: this.fb.control<number | null>(null, [
      Validators.required,
      integer,
      Validators.min(1),
      this.withinEventCapacity,
    ]),
    speaker_id: [''],
  });

  protected readonly speakerOptions = computed<FormFieldOption[]>(() => [
    { value: '', label: 'Sin ponente' },
    ...this.speakers().map((speaker) => ({ value: String(speaker.id), label: speaker.name })),
  ]);

  protected readonly messages = computed(() => ({
    outsideEvent: 'La sesión debe estar dentro del horario del evento.',
    timeOrder: 'La hora de finalización debe ser posterior a la de inicio.',
    min: 'La capacidad debe ser al menos 1.',
    eventCapacity: `La capacidad no puede superar la del evento (${this.maxCapacity().toLocaleString('es')} personas).`,
  }));

  /** Emits on every change of the capacity control, so the computed below stays up to date. */
  private readonly capacityEvents = toSignal(this.form.controls.capacity.events);

  protected readonly capacityOutOfRange = computed(() => {
    this.capacityEvents();
    const control = this.form.controls.capacity;
    return control.value !== null && String(control.value) !== '' && control.invalid;
  });

  constructor() {
    this.form.controls.start_time.valueChanges
      .pipe(takeUntilDestroyed(inject(DestroyRef)))
      .subscribe(() => this.form.controls.end_time.updateValueAndValidity());

    effect(() => {
      const session = this.session();
      this.form.reset(
        session
          ? {
              title: session.title,
              description: session.description ?? '',
              start_time: toColombiaInput(session.start_time),
              end_time: toColombiaInput(session.end_time),
              capacity: session.capacity,
              speaker_id: session.speaker_id === null ? '' : String(session.speaker_id),
            }
          : undefined,
      );
      if (session && this.form.controls.capacity.invalid) {
        this.form.controls.capacity.markAsTouched();
      }
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
      this.host.nativeElement.querySelector<HTMLElement>(INVALID_CONTROL_SELECTOR)?.focus();
      return;
    }
    const value = this.form.getRawValue();
    const description = value.description.trim();
    this.save.emit({
      title: value.title.trim(),
      description: description === '' ? null : description,
      start_time: fromColombiaInput(value.start_time),
      end_time: fromColombiaInput(value.end_time),
      capacity: Number(value.capacity),
      speaker_id: value.speaker_id === '' ? null : Number(value.speaker_id),
    });
  }
}
