import { DecimalPipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, input, output, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { Button } from '../../../../shared/components/button/button';
import { DateRangePipe } from '../../../../shared/pipes/date-range.pipe';
import { type EventSession } from '../../models/session.model';

/**
 * Timeline of the sessions of an event, as returned by the API (ordered by start time).
 * With `manageable`, each session offers edit and delete (with an inline confirmation); the parent
 * performs the deletion.
 */
@Component({
  selector: 'app-session-list',
  imports: [RouterLink, DateRangePipe, DecimalPipe, Button],
  templateUrl: './session-list.html',
  styleUrl: './session-list.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SessionList {
  readonly sessions = input.required<readonly EventSession[]>();
  /** Speaker names by id (from `GET /speakers`). */
  readonly speakerNames = input<ReadonlyMap<number, string>>(new Map());
  /** The current user can create, edit and delete the sessions of this event. */
  readonly manageable = input(false);
  /** Session whose deletion is in progress. */
  readonly removingId = input<number | null>(null);
  readonly remove = output<EventSession>();

  protected readonly confirmingId = signal<number | null>(null);

  protected confirm(session: EventSession): void {
    this.confirmingId.set(null);
    this.remove.emit(session);
  }
}
