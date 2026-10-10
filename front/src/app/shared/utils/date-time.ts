export const APP_LOCALE = 'es-CO';
export const APP_TIME_ZONE = 'America/Bogota';

export interface WallClock {
  year: number;
  month: number;
  day: number;
  hour: number;
  minute: number;
}

const CIVIL_DATE = /^(\d{4})-(\d{2})-(\d{2})$/;
const LOCAL_DATE_TIME = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})$/;
const MINUTE_MS = 60_000;

const wallClockFormatter = new Intl.DateTimeFormat('en-US', {
  timeZone: APP_TIME_ZONE,
  numberingSystem: 'latn',
  year: 'numeric',
  month: 'numeric',
  day: 'numeric',
  hour: 'numeric',
  minute: 'numeric',
  hourCycle: 'h23',
});

const monthFormatter = new Intl.DateTimeFormat(APP_LOCALE, {
  timeZone: APP_TIME_ZONE,
  month: 'short',
});

const pad = (value: number) => String(value).padStart(2, '0');

function toInstant(value: string | Date): Date | null {
  const date = value instanceof Date ? value : new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

export function toWallClock(value: string | Date): WallClock | null {
  const date = toInstant(value);
  if (!date) {
    return null;
  }
  const parts: Record<string, number> = {};
  for (const part of wallClockFormatter.formatToParts(date)) {
    if (part.type !== 'literal') {
      parts[part.type] = Number(part.value);
    }
  }
  return {
    year: parts['year'],
    month: parts['month'],
    day: parts['day'],
    // Some engines report midnight as 24 even with `h23`.
    hour: parts['hour'] % 24,
    minute: parts['minute'],
  };
}

/**
 * Instant for a wall clock in Colombia. The offset comes from the timezone database: it is
 * resolved twice so the result is right even around an offset change.
 */
export function fromWallClock(wall: WallClock): Date {
  const asUtc = Date.UTC(wall.year, wall.month - 1, wall.day, wall.hour, wall.minute);
  const offsetAt = (instant: number) => {
    const seen = toWallClock(new Date(instant)) as WallClock;
    const minute = instant - (((instant % MINUTE_MS) + MINUTE_MS) % MINUTE_MS);
    return Date.UTC(seen.year, seen.month - 1, seen.day, seen.hour, seen.minute) - minute;
  };
  const first = asUtc - offsetAt(asUtc);
  return new Date(asUtc - offsetAt(first));
}

export function parseLocalDateTime(value: string): WallClock | null {
  const match = LOCAL_DATE_TIME.exec(value);
  if (!match) {
    return null;
  }
  const [year, month, day, hour, minute] = match.slice(1).map(Number);
  return { year, month, day, hour, minute };
}

export function formatLocalDateTime(wall: WallClock): string {
  return (
    `${wall.year}-${pad(wall.month)}-${pad(wall.day)}` + `T${pad(wall.hour)}:${pad(wall.minute)}`
  );
}

export function toColombiaInput(iso: string): string {
  const wall = toWallClock(iso);
  return wall ? formatLocalDateTime(wall) : '';
}

export function fromColombiaInput(value: string): string {
  const wall = parseLocalDateTime(value);
  return wall ? fromWallClock(wall).toISOString() : '';
}

function wallClockOf(value: string | Date): WallClock | null {
  if (typeof value === 'string') {
    const civil = CIVIL_DATE.exec(value);
    if (civil) {
      const [year, month, day] = civil.slice(1).map(Number);
      return { year, month, day, hour: 0, minute: 0 };
    }
  }
  return toWallClock(value);
}

function dateText(wall: WallClock): string {
  return `${pad(wall.day)}/${pad(wall.month)}/${wall.year}`;
}

function timeText(wall: WallClock): string {
  const period = wall.hour < 12 ? 'AM' : 'PM';
  const hour = wall.hour % 12 === 0 ? 12 : wall.hour % 12;
  return `${hour}:${pad(wall.minute)} ${period}`;
}

export function formatAppDate(value: string | Date | null | undefined): string {
  const wall = value ? wallClockOf(value) : null;
  return wall ? dateText(wall) : '';
}

export function formatAppTime(value: string | Date | null | undefined): string {
  const wall = value ? wallClockOf(value) : null;
  return wall ? timeText(wall) : '';
}

export function formatAppDateTime(value: string | Date | null | undefined): string {
  const wall = value ? wallClockOf(value) : null;
  return wall ? `${dateText(wall)}, ${timeText(wall)}` : '';
}

export function formatAppDay(value: string | Date | null | undefined): string {
  const wall = value ? wallClockOf(value) : null;
  return wall ? String(wall.day) : '';
}

export function formatAppMonth(value: string | Date | null | undefined): string {
  const wall = value ? wallClockOf(value) : null;
  // Noon of that day in Colombia, so civil dates keep their month.
  const date = wall ? fromWallClock({ ...wall, hour: 12, minute: 0 }) : null;
  return date ? monthFormatter.format(date).replace(/\.$/, '') : '';
}

export function formatAppDateRange(start: string, end: string): string {
  const from = wallClockOf(start);
  const to = wallClockOf(end);
  if (!from || !to) {
    return '';
  }
  if (dateText(from) === dateText(to)) {
    return `${dateText(from)} · ${timeText(from)} – ${timeText(to)}`;
  }
  return `${dateText(from)}, ${timeText(from)} – ${dateText(to)}, ${timeText(to)}`;
}
