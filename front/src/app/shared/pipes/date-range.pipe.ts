import { Pipe, type PipeTransform } from '@angular/core';

import { formatAppDateRange } from '../utils/date-time';

@Pipe({ name: 'dateRange' })
export class DateRangePipe implements PipeTransform {
  transform(start: string, end: string): string {
    return formatAppDateRange(start, end);
  }
}
