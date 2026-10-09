import { AppDatePipe } from './app-date.pipe';
import { DateRangePipe } from './date-range.pipe';

describe('AppDatePipe', () => {
  const pipe = new AppDatePipe();
  const instant = '2026-10-10T19:45:00+00:00';

  it('should format date, time and both in Colombia time', () => {
    expect(pipe.transform(instant, 'date')).toBe('10/10/2026');
    expect(pipe.transform(instant, 'time')).toBe('2:45 PM');
    expect(pipe.transform(instant, 'datetime')).toBe('10/10/2026, 2:45 PM');
    expect(pipe.transform(instant)).toBe('10/10/2026, 2:45 PM');
  });

  it('should format the parts of calendar badges', () => {
    expect(pipe.transform(instant, 'day')).toBe('10');
    expect(pipe.transform(instant, 'month')).toBe('oct');
  });

  it('should show nothing for null values', () => {
    expect(pipe.transform(null, 'date')).toBe('');
    expect(pipe.transform(undefined)).toBe('');
  });
});

describe('DateRangePipe', () => {
  it('should format a schedule in Colombia time with AM/PM', () => {
    expect(new DateRangePipe().transform('2026-10-10T19:30:00Z', '2026-10-10T21:00:00Z')).toBe(
      '10/10/2026 · 2:30 PM – 4:00 PM',
    );
  });
});
