import { DecimalPipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { RouterLink } from '@angular/router';

import { AppDatePipe } from '../../../../shared/pipes/app-date.pipe';
import { DateRangePipe } from '../../../../shared/pipes/date-range.pipe';
import { type EventModel } from '../../models/event.model';
import { EventStatusBadge } from '../event-status-badge/event-status-badge';

/** Event summary. The whole card is clickable through the title link (stretched link). */
@Component({
  selector: 'app-event-card',
  imports: [RouterLink, AppDatePipe, DecimalPipe, DateRangePipe, EventStatusBadge],
  templateUrl: './event-card.html',
  styleUrl: './event-card.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class EventCard {
  readonly event = input.required<EventModel>();
}
