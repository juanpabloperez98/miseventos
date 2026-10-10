import { DecimalPipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, input, output, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { Button } from '../../../../shared/components/button/button';
import { DateRangePipe } from '../../../../shared/pipes/date-range.pipe';
import { type EventSession } from '../../models/session.model';

@Component({
  selector: 'app-session-list',
  imports: [RouterLink, DateRangePipe, DecimalPipe, Button],
  templateUrl: './session-list.html',
  styleUrl: './session-list.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SessionList {
  readonly sessions = input.required<readonly EventSession[]>();
  readonly manageable = input(false);
  readonly removingId = input<number | null>(null);
  readonly remove = output<EventSession>();

  protected readonly confirmingId = signal<number | null>(null);

  protected confirm(session: EventSession): void {
    this.confirmingId.set(null);
    this.remove.emit(session);
  }
}
