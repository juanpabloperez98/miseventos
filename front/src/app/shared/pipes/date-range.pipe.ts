import { Pipe, type PipeTransform } from '@angular/core';

import { formatAppDateRange } from '../utils/date-time';

/**
 * Formats a start/end pair (ISO 8601) in Colombia time (`America/Bogota`).
 * Same day: `10/10/2026 · 9:00 AM – 6:00 PM`. Different days: `10/10/2026, 9:00 AM – 11/10/2026,
 * 6:00 PM`.
 */
@Pipe({ name: 'dateRange' })
export class DateRangePipe implements PipeTransform {
  transform(start: string, end: string): string {
    return formatAppDateRange(start, end);
  }
}
