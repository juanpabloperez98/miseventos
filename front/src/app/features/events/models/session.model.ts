/**
 * `SessionSchema` returned by `GET /events/{event_id}/sessions`.
 *
 * Only the `speaker_id` is included; the speaker's name comes from `GET /speakers`.
 */
export interface EventSession {
  id: number;
  event_id: number;
  speaker_id: number | null;
  title: string;
  description: string | null;
  start_time: string;
  end_time: string;
  capacity: number;
  created_at?: string;
  updated_at?: string;
}

/** Body of `POST /events/{id}/sessions` and `PUT /sessions/{id}` (`SessionWriteSchema`). */
export interface SessionPayload {
  title: string;
  description: string | null;
  start_time: string;
  end_time: string;
  capacity: number;
  /** Optional speaker; `null` (or omitted) means no speaker. */
  speaker_id: number | null;
}

/** Limits enforced by `SessionWriteSchema`. */
export const SESSION_LIMITS = {
  titleMaxLength: 200,
  descriptionMaxLength: 5000,
  capacityMax: 1_000_000,
} as const;
