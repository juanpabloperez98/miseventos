import {
  ChangeDetectionStrategy,
  Component,
  computed,
  DestroyRef,
  effect,
  inject,
  input,
  output,
  signal,
  untracked,
} from '@angular/core';

import { Button } from '../../../../shared/components/button/button';
import { responsiveImage } from '../../../../shared/utils/cloudinary-image';
import { type EventImage } from '../../models/event.model';
import {
  EVENT_IMAGE_RULES,
  type EventImageSelection,
  NO_IMAGE_CHANGE,
  validateEventImage,
} from '../../services/event-images.service';

let nextId = 0;

/**
 * Cover image picker of the event form. It only chooses: the page uploads the file after saving
 * the event. Shows the current image (optimized by Cloudinary) or a local preview of the new file,
 * which never leaves the browser until the upload is authorized.
 */
@Component({
  selector: 'app-event-image-field',
  imports: [Button],
  templateUrl: './event-image-field.html',
  styleUrl: './event-image-field.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class EventImageField {
  /** Image saved for the event, if any. */
  readonly image = input<EventImage | null>(null);
  readonly disabled = input(false);
  /** Progress of an upload in course, shown as a live status. */
  readonly status = input<string | null>(null);

  readonly selectionChange = output<EventImageSelection>();

  protected readonly inputId = `event-image-${nextId++}`;
  protected readonly accept = EVENT_IMAGE_RULES.types.join(',');
  protected readonly file = signal<File | null>(null);
  protected readonly removed = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly previewUrl = signal<string | null>(null);

  protected readonly current = computed(() => {
    const image = this.image();
    return image && !this.removed() ? responsiveImage(image.secure_url, 'cover') : null;
  });

  constructor() {
    inject(DestroyRef).onDestroy(() => this.revokePreview());
    // Another event loaded in the form: forget the previous choice.
    effect(() => {
      this.image();
      untracked(() => this.reset());
    });
  }

  protected select(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0] ?? null;
    input.value = '';
    if (!file) {
      return;
    }
    const problem = validateEventImage(file);
    if (problem) {
      this.error.set(problem);
      return;
    }
    this.error.set(null);
    this.revokePreview();
    this.previewUrl.set(URL.createObjectURL(file));
    this.file.set(file);
    this.removed.set(false);
    this.emit();
  }

  /** Discards the new file, or marks the current image for removal. */
  protected clear(): void {
    this.error.set(null);
    if (this.file()) {
      this.revokePreview();
      this.file.set(null);
    } else {
      this.removed.set(true);
    }
    this.emit();
  }

  protected undoRemoval(): void {
    this.removed.set(false);
    this.emit();
  }

  private reset(): void {
    this.revokePreview();
    this.file.set(null);
    this.removed.set(false);
    this.error.set(null);
  }

  private emit(): void {
    this.selectionChange.emit(
      this.file() || this.removed()
        ? { file: this.file(), remove: this.removed() }
        : NO_IMAGE_CHANGE,
    );
  }

  private revokePreview(): void {
    const url = this.previewUrl();
    if (url) {
      URL.revokeObjectURL(url);
      this.previewUrl.set(null);
    }
  }
}
