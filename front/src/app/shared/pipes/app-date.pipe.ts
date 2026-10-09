import { Pipe, type PipeTransform } from '@angular/core';

import {
  formatAppDate,
  formatAppDateTime,
  formatAppDay,
  formatAppMonth,
  formatAppTime,
} from '../utils/date-time';

/**
 * - `date`: `10/10/2026`
 * - `time`: `2:45 PM`
 * - `datetime`: `10/10/2026, 2:45 PM`
 * - `day` / `month`: `10` / `oct`, for calendar-like badges.
 */
export type AppDateFormat = 'date' | 'time' | 'datetime' | 'day' | 'month';

const FORMATTERS: Record<AppDateFormat, (value: string | Date | null | undefined) => string> = {
  date: formatAppDate,
  time: formatAppTime,
  datetime: formatAppDateTime,
  day: formatAppDay,
  month: formatAppMonth,
};

/**
 * Shows a date in Colombia time (`America/Bogota`) with the formats of the application. Use it
 * instead of Angular's `date` pipe, which depends on the timezone of the device.
 */
@Pipe({ name: 'appDate' })
export class AppDatePipe implements PipeTransform {
  transform(value: string | Date | null | undefined, format: AppDateFormat = 'datetime'): string {
    return FORMATTERS[format](value);
  }
}
