/**
 * Conversions between API dates (ISO 8601 with timezone, stored in UTC by the backend) and the
 * value of `<input type="datetime-local">`, which is expressed in the user's local time.
 */

/** `2026-11-08T14:00:00+00:00` → `2026-11-08T09:00` (for a UTC-5 browser). */
export function toDateTimeLocal(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return '';
  }
  const pad = (value: number) => String(value).padStart(2, '0');
  return (
    `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}` +
    `T${pad(date.getHours())}:${pad(date.getMinutes())}`
  );
}

/** `2026-11-08T09:00` (local time) → `2026-11-08T14:00:00.000Z`. */
export function fromDateTimeLocal(value: string): string {
  return new Date(value).toISOString();
}
