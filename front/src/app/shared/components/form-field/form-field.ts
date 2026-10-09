import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { type FormControl, ReactiveFormsModule } from '@angular/forms';
import { startWith, switchMap } from 'rxjs';

import { validationMessage } from '../../utils/validation-messages';

export type FormFieldType =
  'text' | 'email' | 'password' | 'number' | 'datetime-local' | 'textarea' | 'select';

export interface FormFieldOption {
  value: string;
  label: string;
}

let nextId = 0;

/**
 * Labelled form control bound to a Reactive Forms `FormControl`, with hint and validation message.
 * The error is shown once the control is touched or dirty, and is linked through
 * `aria-describedby` / `aria-invalid` for assistive technologies.
 */
@Component({
  selector: 'app-form-field',
  imports: [ReactiveFormsModule],
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
  /** Custom messages per validation error key. */
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
