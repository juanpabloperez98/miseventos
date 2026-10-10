export type EventStatus = 'DRAFT' | 'PUBLISHED' | 'CANCELLED' | 'COMPLETED';

export interface EventImage {
  public_id: string;
  secure_url: string;
  width: number;
  height: number;
  format: string;
}

export interface EventModel {
  id: number;
  name: string;
  description: string | null;
  location: string;
  start_date: string;
  end_date: string;
  capacity: number;
  status: EventStatus;
  created_by: number;
  image?: EventImage | null;
  created_at?: string;
  updated_at?: string;
}

export interface EventPage {
  items: EventModel[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface EventQuery {
  page: number;
  perPage: number;
  search?: string;
  status?: EventStatus;
}

export interface EventPayload {
  name: string;
  description: string | null;
  location: string;
  start_date: string;
  end_date: string;
  capacity: number;
}

export interface EventUpdatePayload extends EventPayload {
  status?: EventStatus;
}

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

const STATUS_TRANSITIONS: Record<EventStatus, readonly EventStatus[]> = {
  DRAFT: ['PUBLISHED', 'CANCELLED'],
  PUBLISHED: ['CANCELLED', 'COMPLETED'],
  CANCELLED: [],
  COMPLETED: [],
};

export function availableStatuses(current: EventStatus): EventStatus[] {
  return [current, ...STATUS_TRANSITIONS[current]];
}

export function isEventEditable(event: Pick<EventModel, 'status'>): boolean {
  return STATUS_TRANSITIONS[event.status].length > 0;
}

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
