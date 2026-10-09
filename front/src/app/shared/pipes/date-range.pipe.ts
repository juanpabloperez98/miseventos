import { formatDate } from '@angular/common';
import { inject, LOCALE_ID, Pipe, type PipeTransform } from '@angular/core';

const DAY_FORMAT = 'EEE d MMM y';
const TIME_FORMAT = 'HH:mm';

/**
 * Formats a start/end pair (ISO 8601) in the user's timezone and the app locale.
 * Same day: `sáb 8 nov 2026 · 09:00 – 18:00`. Different days: `sáb 8 nov 2026, 09:00 – dom 9 nov
 * 2026, 18:00`.
 */
@Pipe({ name: 'dateRange' })
export class DateRangePipe implements PipeTransform {
  private readonly locale = inject(LOCALE_ID);

  transform(start: string, end: string): string {
    const format = (value: string, pattern: string) => formatDate(value, pattern, this.locale);
    const startDay = format(start, DAY_FORMAT);
    const endDay = format(end, DAY_FORMAT);

    if (startDay === endDay) {
      return `${startDay} · ${format(start, TIME_FORMAT)} – ${format(end, TIME_FORMAT)}`;
    }
    return `${startDay}, ${format(start, TIME_FORMAT)} – ${endDay}, ${format(end, TIME_FORMAT)}`;
  }
}
