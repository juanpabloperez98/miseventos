import { DecimalPipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, input, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { AppDatePipe } from '../../../../shared/pipes/app-date.pipe';
import { DateRangePipe } from '../../../../shared/pipes/date-range.pipe';
import { IMAGE_VARIANTS, responsiveImage } from '../../../../shared/utils/cloudinary-image';
import { type EventModel } from '../../models/event.model';
import { EventStatusBadge } from '../event-status-badge/event-status-badge';

export const DEFAULT_EVENT_COVER = 'images/event-cover-default.svg';

interface CardPicture {
  src: string;
  srcset: string | null;
  sizes: string | null;
  width: number;
  height: number;
  isDefault: boolean;
}

const [CARD_SIZE] = IMAGE_VARIANTS.card.variants;
const DEFAULT_PICTURE: CardPicture = {
  src: DEFAULT_EVENT_COVER,
  // No `srcset`: otherwise the browser would keep loading the failed Cloudinary variants.
  srcset: null,
  sizes: null,
  width: CARD_SIZE.width,
  height: CARD_SIZE.height,
  isDefault: true,
};

@Component({
  selector: 'app-event-card',
  imports: [RouterLink, AppDatePipe, DecimalPipe, DateRangePipe, EventStatusBadge],
  templateUrl: './event-card.html',
  styleUrl: './event-card.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class EventCard {
  readonly event = input.required<EventModel>();

  private readonly failedUrl = signal<string | null>(null);

  protected readonly picture = computed<CardPicture>(() => {
    const url = this.event().image?.secure_url?.trim();
    if (!url || url === this.failedUrl()) {
      return DEFAULT_PICTURE;
    }
    return { ...responsiveImage(url, 'card'), isDefault: false };
  });

  protected imageFailed(): void {
    // A failing default image is left as it is: replacing it again would loop forever.
    if (!this.picture().isDefault) {
      this.failedUrl.set(this.event().image?.secure_url?.trim() ?? null);
    }
  }
}
