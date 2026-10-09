/**
 * `SessionSchema` returned by `GET /events/{event_id}/sessions`.
 *
 * The backend only exposes `speaker_id`: there is no speakers endpoint yet, so speaker details
 * cannot be shown.
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
