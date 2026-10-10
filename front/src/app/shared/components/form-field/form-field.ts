import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { type FormControl, ReactiveFormsModule } from '@angular/forms';
import { startWith, switchMap } from 'rxjs';

import { validationMessage } from '../../utils/validation-messages';
import { DateTimeInput } from '../date-time-input/date-time-input';

export type FormFieldType =
  'text' | 'email' | 'password' | 'number' | 'datetime' | 'textarea' | 'select';

export interface FormFieldOption {
  value: string;
  label: string;
}

let nextId = 0;

@Component({
  selector: 'app-form-field',
  imports: [ReactiveFormsModule, DateTimeInput],
  templateUrl: './form-field.html',
  styleUrl: './form-field.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FormField {
  readonly control = input.required<FormControl<unknown>>();
  readonly label = input.required<string>();
  readonly type = input<FormFieldType>('text');
  readonly fieldId = input(`field-${nextId++}`);
  readonly hint = input<string>();
  readonly placeholder = input<string>();
  readonly autocomplete = input<string>();
  readonly required = input(false);
  readonly rows = input(4);
  readonly min = input<string | number>();
  readonly max = input<string | number>();
  readonly maxLength = input<number>();
  readonly options = input<readonly FormFieldOption[]>([]);
  readonly messages = input<Record<string, string>>({});

  /** Emits on every value/status/touched change, so OnPush views react to `markAllAsTouched()`. */
  private readonly controlEvents = toSignal(
    toObservable(this.control).pipe(switchMap((control) => control.events.pipe(startWith(null)))),
  );

  protected readonly hintId = computed(() => `${this.fieldId()}-hint`);
  protected readonly errorId = computed(() => `${this.fieldId()}-error`);

  protected readonly errorMessage = computed(() => {
    this.controlEvents();
    const control = this.control();
    const visible = control.invalid && (control.touched || control.dirty);
    return visible ? validationMessage(control.errors, this.messages()) : null;
  });

  protected readonly describedBy = computed(() => {
    const ids = [this.hint() ? this.hintId() : null, this.errorMessage() ? this.errorId() : null];
    return ids.filter(Boolean).join(' ') || null;
  });
}
