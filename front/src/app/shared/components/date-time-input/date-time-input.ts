import {
  ChangeDetectionStrategy,
  Component,
  computed,
  forwardRef,
  input,
  signal,
} from '@angular/core';
import { type ControlValueAccessor, NG_VALUE_ACCESSOR } from '@angular/forms';

import {
  formatAppDateTime,
  formatLocalDateTime,
  fromColombiaInput,
  parseLocalDateTime,
} from '../../utils/date-time';

type Period = 'AM' | 'PM';

const HOURS = Array.from({ length: 12 }, (_, index) => String(index + 1));
const MINUTES = Array.from({ length: 60 }, (_, index) => String(index).padStart(2, '0'));
const DATE_LENGTH = 'yyyy-MM-dd'.length;

/**
 * Date and time of a schedule in Colombia time, with the time always in the 12-hour clock
 * (hour, minutes and AM/PM). Native `datetime-local` and `time` inputs follow the locale of the
 * browser and may show the 24-hour clock, so the time is chosen with selects instead.
 *
 * The form value keeps the `datetime-local` format (`yyyy-MM-ddTHH:mm`, 24-hour clock), so
 * validators and conversions work as before. Until date, hour, minutes and AM/PM are all chosen the
 * value is `''` (reported as a missing value by `Validators.required`).
 */
@Component({
  selector: 'app-date-time-input',
  templateUrl: './date-time-input.html',
  styleUrl: './date-time-input.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [
    { provide: NG_VALUE_ACCESSOR, useExisting: forwardRef(() => DateTimeInput), multi: true },
  ],
})
export class DateTimeInput implements ControlValueAccessor {
  /** Id of the date input, so an external `<label for>` focuses it. */
  readonly inputId = input.required<string>();
  /** Bounds as `yyyy-MM-ddTHH:mm`; only their date limits the date picker. */
  readonly min = input<string>();
  readonly max = input<string>();
  readonly required = input(false);
  readonly invalid = input(false);
  readonly describedBy = input<string | null>(null);

  protected readonly hours = HOURS;
  protected readonly minutes = MINUTES;

  protected readonly date = signal('');
  protected readonly hour = signal('');
  protected readonly minute = signal('');
  protected readonly period = signal<Period | ''>('');
  protected readonly disabled = signal(false);

  protected readonly minDate = computed(() => this.min()?.slice(0, DATE_LENGTH) || null);
  protected readonly maxDate = computed(() => this.max()?.slice(0, DATE_LENGTH) || null);

  /** Chosen value in the formats of the application, e.g. `10/10/2026, 2:30 PM`. */
  protected readonly summary = computed(() => formatAppDateTime(fromColombiaInput(this.value())));

  private readonly value = computed(() => {
    const [year, month, day] = this.date().split('-').map(Number);
    const period = this.period();
    if (!year || !month || !day || !this.hour() || !this.minute() || !period) {
      return '';
    }
    const hour = (Number(this.hour()) % 12) + (period === 'PM' ? 12 : 0);
    return formatLocalDateTime({ year, month, day, hour, minute: Number(this.minute()) });
  });

  private onChange: (value: string) => void = () => undefined;
  private onTouched: () => void = () => undefined;

  writeValue(value: unknown): void {
    const wall = typeof value === 'string' ? parseLocalDateTime(value) : null;
    if (!wall) {
      this.date.set('');
      this.hour.set('');
      this.minute.set('');
      this.period.set('');
      return;
    }
    this.date.set(formatLocalDateTime(wall).slice(0, DATE_LENGTH));
    this.hour.set(String(wall.hour % 12 === 0 ? 12 : wall.hour % 12));
    this.minute.set(String(wall.minute).padStart(2, '0'));
    this.period.set(wall.hour < 12 ? 'AM' : 'PM');
  }

  registerOnChange(fn: (value: string) => void): void {
    this.onChange = fn;
  }

  registerOnTouched(fn: () => void): void {
    this.onTouched = fn;
  }

  setDisabledState(isDisabled: boolean): void {
    this.disabled.set(isDisabled);
  }

  protected update(part: 'date' | 'hour' | 'minute' | 'period', event: Event): void {
    const value = (event.target as HTMLInputElement | HTMLSelectElement).value;
    if (part === 'period') {
      this.period.set(value === 'AM' || value === 'PM' ? value : '');
    } else {
      this[part].set(value);
    }
    this.onChange(this.value());
  }

  protected touch(event: FocusEvent): void {
    // Only when the focus leaves the whole group, not when moving between its parts.
    const host = event.currentTarget as HTMLElement;
    if (!host.contains(event.relatedTarget as Node | null)) {
      this.onTouched();
    }
  }
}
