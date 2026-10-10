/** Statuses defined by the backend (`EventStatus`). */
export type EventStatus = 'DRAFT' | 'PUBLISHED' | 'CANCELLED' | 'COMPLETED';

/** `EventImageSchema`: cover image stored in Cloudinary (verified by the backend). */
export interface EventImage {
  public_id: string;
  secure_url: string;
  width: number;
  height: number;
  format: string;
}

/** `EventSchema`. Dates are ISO 8601 strings in UTC. */
export interface EventModel {
  id: number;
  name: string;
  description: string | null;
  location: string;
  start_date: string;
  end_date: string;
  capacity: number;
  status: EventStatus;
  /** Id of the user who created (and owns) the event. */
  created_by: number;
  /** Cover image; `null` (or absent) when the event has none. */
  image?: EventImage | null;
  created_at?: string;
  updated_at?: string;
}

/** `EventPageSchema` returned by `GET /events`. */
export interface EventPage {
  items: EventModel[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

/** Query parameters accepted by `GET /events` (`EventQuerySchema`). */
export interface EventQuery {
  page: number;
  perPage: number;
  /** Case-insensitive partial match on the event name (max 100 characters). */
  search?: string;
  status?: EventStatus;
}

/** Body of `POST /events` (`EventCreateSchema`). */
export interface EventPayload {
  name: string;
  description: string | null;
  location: string;
  start_date: string;
  end_date: string;
  capacity: number;
}

/** Body of `PUT /events/{id}` (`EventUpdateSchema`): omit `status` to keep the current one. */
export interface EventUpdatePayload extends EventPayload {
  status?: EventStatus;
}

/** Limits enforced by the backend schemas. */
export const EVENT_LIMITS = {
  nameMaxLength: 200,
  descriptionMaxLength: 5000,
  locationMaxLength: 255,
  capacityMax: 1_000_000,
  searchMaxLength: 100,
} as const;

export const EVENT_STATUS_LABELS: Record<EventStatus, string> = {
  DRAFT: 'Borrador',
  PUBLISHED: 'Publicado',
  CANCELLED: 'Cancelado',
  COMPLETED: 'Finalizado',
};

/** Status workflow of the backend: `DRAFT → PUBLISHED | CANCELLED`, `PUBLISHED → CANCELLED | COMPLETED`. */
const STATUS_TRANSITIONS: Record<EventStatus, readonly EventStatus[]> = {
  DRAFT: ['PUBLISHED', 'CANCELLED'],
  PUBLISHED: ['CANCELLED', 'COMPLETED'],
  CANCELLED: [],
  COMPLETED: [],
};

/** Statuses the event can move to, including its current one. */
export function availableStatuses(current: EventStatus): EventStatus[] {
  return [current, ...STATUS_TRANSITIONS[current]];
}

/** `CANCELLED` and `COMPLETED` are final: they cannot be edited (409). */
export function isEventEditable(event: Pick<EventModel, 'status'>): boolean {
  return STATUS_TRANSITIONS[event.status].length > 0;
}

/**
 * What `DELETE /events/{id}` does for the event: drafts are deleted, published events are
 * cancelled, final events cannot be removed.
 */
export function removalAction(event: Pick<EventModel, 'status'>): 'delete' | 'cancel' | null {
  switch (event.status) {
    case 'DRAFT':
      return 'delete';
    case 'PUBLISHED':
      return 'cancel';
    default:
      return null;
  }
}
