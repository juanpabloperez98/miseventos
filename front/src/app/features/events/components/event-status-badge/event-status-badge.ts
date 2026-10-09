import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

import { EVENT_STATUS_LABELS, type EventStatus } from '../../models/event.model';

@Component({
  selector: 'app-event-status-badge',
  template: `{{ label() }}`,
  styles: `
    :host {
      display: inline-flex;
      align-items: center;
      padding: 0.125rem var(--space-3);
      border-radius: var(--radius-full);
      font-size: var(--font-size-xs);
      font-weight: var(--font-weight-semibold);
      letter-spacing: 0.02em;
      text-transform: uppercase;
    }

    :host(.status--published) {
      background: var(--color-success-subtle);
      color: #166534;
    }

    :host(.status--draft) {
      background: var(--color-warning-subtle);
      color: #92400e;
    }

    :host(.status--cancelled) {
      background: var(--color-danger-subtle);
      color: #991b1b;
    }

    :host(.status--completed) {
      background: #eef0f4;
      color: #374151;
    }
  `,
  host: { '[class]': "'status--' + status().toLowerCase()" },
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class EventStatusBadge {
  readonly status = input.required<EventStatus>();
  protected readonly label = computed(() => EVENT_STATUS_LABELS[this.status()]);
}
