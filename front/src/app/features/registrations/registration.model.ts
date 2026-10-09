/** `RegistrationSchema` returned by `POST /events/{event_id}/registrations` (201). */
export interface Registration {
  id: number;
  event_id: number;
  user_id: number;
  /** ISO 8601 date with timezone. */
  registered_at: string;
}
