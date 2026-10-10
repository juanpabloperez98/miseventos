import { Pipe, type PipeTransform } from '@angular/core';

import {
  formatAppDate,
  formatAppDateTime,
  formatAppDay,
  formatAppMonth,
  formatAppTime,
} from '../utils/date-time';

export type AppDateFormat = 'date' | 'time' | 'datetime' | 'day' | 'month';

const FORMATTERS: Record<AppDateFormat, (value: string | Date | null | undefined) => string> = {
  date: formatAppDate,
  time: formatAppTime,
  datetime: formatAppDateTime,
  day: formatAppDay,
  month: formatAppMonth,
};

@Pipe({ name: 'appDate' })
export class AppDatePipe implements PipeTransform {
  transform(value: string | Date | null | undefined, format: AppDateFormat = 'datetime'): string {
    return FORMATTERS[format](value);
  }
}
