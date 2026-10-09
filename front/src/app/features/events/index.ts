/**
 * Public API of the events feature. Other features import from here, never from internal paths,
 * so the events feature can reorganize its files without breaking them.
 */
export { EventCard } from './components/event-card/event-card';
export { type EventModel, type EventStatus } from './models/event.model';
