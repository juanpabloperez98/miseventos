import {
  APP_LOCALE,
  APP_TIME_ZONE,
  formatAppDate,
  formatAppDateRange,
  formatAppDateTime,
  formatAppDay,
  formatAppMonth,
  formatAppTime,
  fromColombiaInput,
  fromWallClock,
  toColombiaInput,
  toWallClock,
} from './date-time';

describe('date-time utilities', () => {
  it('should present dates in Spanish (Colombia) and in Colombia time', () => {
    expect(APP_LOCALE).toBe('es-CO');
    expect(APP_TIME_ZONE).toBe('America/Bogota');
  });

  describe('formats', () => {
    const instant = '2026-10-10T19:45:00+00:00';

    it('should format dates as dd/MM/yyyy', () => {
      expect(formatAppDate(instant)).toBe('10/10/2026');
      expect(formatAppDate('2026-03-05T17:00:00Z')).toBe('05/03/2026');
    });

    it('should format times in the 12-hour clock with AM/PM', () => {
      expect(formatAppTime('2026-10-10T14:30:00Z')).toBe('9:30 AM');
      expect(formatAppTime(instant)).toBe('2:45 PM');
    });

    it('should format date and time as dd/MM/yyyy, h:mm a', () => {
      expect(formatAppDateTime(instant)).toBe('10/10/2026, 2:45 PM');
    });

    it('should accept Date objects and any offset of the same instant', () => {
      expect(formatAppDateTime(new Date(Date.UTC(2026, 9, 10, 19, 45)))).toBe(
        '10/10/2026, 2:45 PM',
      );
      expect(formatAppDateTime('2026-10-10T14:45:00-05:00')).toBe('10/10/2026, 2:45 PM');
      expect(formatAppDateTime('2026-10-10T21:45:00+02:00')).toBe('10/10/2026, 2:45 PM');
    });

    it('should never use the 24-hour clock', () => {
      for (let hour = 0; hour < 24; hour++) {
        const text = formatAppTime(new Date(Date.UTC(2026, 9, 10, hour, 5)));
        expect(text).toMatch(/^(1[0-2]|[1-9]):05 (AM|PM)$/);
      }
    });

    it('should show midnight as 12 AM and noon as 12 PM', () => {
      expect(formatAppTime('2026-10-10T05:00:00Z')).toBe('12:00 AM');
      expect(formatAppTime('2026-10-10T17:00:00Z')).toBe('12:00 PM');
    });

    it('should return an empty text for missing or invalid values', () => {
      for (const value of [null, undefined, '', 'not a date']) {
        expect(formatAppDate(value)).toBe('');
        expect(formatAppTime(value)).toBe('');
        expect(formatAppDateTime(value)).toBe('');
        expect(formatAppDay(value)).toBe('');
        expect(formatAppMonth(value)).toBe('');
      }
    });

    it('should give the day and short month for calendar badges', () => {
      expect(formatAppDay(instant)).toBe('10');
      expect(formatAppMonth(instant)).toBe('oct');
    });
  });

  describe('Colombia timezone', () => {
    it('should keep the Colombian day for times close to midnight', () => {
      expect(formatAppDateTime('2026-10-11T04:30:00Z')).toBe('10/10/2026, 11:30 PM');
      expect(formatAppDateTime('2026-10-11T05:15:00Z')).toBe('11/10/2026, 12:15 AM');
      expect(formatAppDay('2026-10-11T04:30:00Z')).toBe('10');
      expect(formatAppMonth('2026-11-01T04:30:00Z')).toBe('oct');
    });

    it('should read instants as Colombian wall clocks', () => {
      expect(toWallClock('2026-10-10T19:30:00Z')).toEqual({
        year: 2026,
        month: 10,
        day: 10,
        hour: 14,
        minute: 30,
      });
      expect(toWallClock('invalid')).toBeNull();
    });

    it('should turn Colombian wall clocks into instants', () => {
      const instant = fromWallClock({ year: 2026, month: 12, day: 31, hour: 23, minute: 59 });

      expect(instant.toISOString()).toBe('2027-01-01T04:59:00.000Z');
    });
  });

  describe('civil dates', () => {
    it('should not move a date without time to the previous day', () => {
      expect(formatAppDate('2026-10-10')).toBe('10/10/2026');
      expect(formatAppDay('2026-10-01')).toBe('1');
      expect(formatAppMonth('2026-11-01')).toBe('nov');
    });
  });

  describe('schedule inputs', () => {
    it('should show the stored instant as Colombia time in the inputs', () => {
      expect(toColombiaInput('2026-10-10T19:30:00+00:00')).toBe('2026-10-10T14:30');
      expect(toColombiaInput('2026-10-11T04:59:00+00:00')).toBe('2026-10-10T23:59');
      expect(toColombiaInput('2026-10-11T05:00:00+00:00')).toBe('2026-10-11T00:00');
      expect(toColombiaInput('')).toBe('');
    });

    it('should send the Colombian time of the inputs as a UTC instant', () => {
      expect(fromColombiaInput('2026-10-10T14:30')).toBe('2026-10-10T19:30:00.000Z');
      expect(fromColombiaInput('2026-10-10T23:30')).toBe('2026-10-11T04:30:00.000Z');
      expect(fromColombiaInput('2026-10-10T00:00')).toBe('2026-10-10T05:00:00.000Z');
      expect(fromColombiaInput('')).toBe('');
      expect(fromColombiaInput('10/10/2026')).toBe('');
    });

    it('should not shift the value when loading and saving it again', () => {
      const stored = '2026-10-10T19:30:00.000Z';
      let value = stored;
      for (let round = 0; round < 3; round++) {
        value = fromColombiaInput(toColombiaInput(value));
      }

      expect(value).toBe(stored);
      expect(formatAppDateTime(value)).toBe('10/10/2026, 2:30 PM');
    });
  });

  describe('ranges', () => {
    it('should show a same-day range with the date once', () => {
      expect(formatAppDateRange('2026-10-10T14:00:00Z', '2026-10-10T23:00:00Z')).toBe(
        '10/10/2026 · 9:00 AM – 6:00 PM',
      );
    });

    it('should show both dates when the range spans several Colombian days', () => {
      expect(formatAppDateRange('2026-10-10T14:00:00Z', '2026-10-11T23:00:00Z')).toBe(
        '10/10/2026, 9:00 AM – 11/10/2026, 6:00 PM',
      );
    });

    it('should treat a range ending before midnight in Colombia as a single day', () => {
      expect(formatAppDateRange('2026-10-10T23:00:00Z', '2026-10-11T04:00:00Z')).toBe(
        '10/10/2026 · 6:00 PM – 11:00 PM',
      );
    });

    it('should return an empty text when a value is invalid', () => {
      expect(formatAppDateRange('', '2026-10-10T23:00:00Z')).toBe('');
    });
  });
});
