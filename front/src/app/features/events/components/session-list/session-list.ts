import { DecimalPipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, input } from '@angular/core';

import { DateRangePipe } from '../../../../shared/pipes/date-range.pipe';
import { type EventSession } from '../../models/session.model';

/** Timeline of the sessions of an event, as returned by the API (ordered by start time). */
@Component({
  selector: 'app-session-list',
  imports: [DateRangePipe, DecimalPipe],
  template: `
    <ol class="sessions">
      @for (session of sessions(); track session.id) {
        <li class="session">
          <p class="session__time">
            <time [attr.datetime]="session.start_time">{{
              session.start_time | dateRange: session.end_time
            }}</time>
          </p>
          <h3 class="session__title">{{ session.title }}</h3>
          @if (session.description) {
            <p class="session__description">{{ session.description }}</p>
          }
          <p class="session__capacity">Capacidad: {{ session.capacity | number }} personas</p>
        </li>
      }
    </ol>
  `,
  styles: `
    .sessions {
      display: grid;
      gap: var(--space-4);
      padding: 0;
      list-style: none;
    }

    .session {
      position: relative;
      display: grid;
      gap: var(--space-2);
      padding: var(--space-4) var(--space-5);
      border: var(--border-width) solid var(--color-border);
      border-left: 4px solid var(--color-primary);
      border-radius: var(--radius-md);
      background: var(--color-surface);
    }

    .session__time {
      font-size: var(--font-size-sm);
      font-weight: var(--font-weight-semibold);
      color: var(--color-primary);
    }

    .session__title {
      font-size: var(--font-size-lg);
    }

    .session__description {
      color: var(--color-text-muted);
      white-space: pre-line;
    }

    .session__capacity {
      font-size: var(--font-size-sm);
      color: var(--color-text-muted);
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SessionList {
  readonly sessions = input.required<readonly EventSession[]>();
}
