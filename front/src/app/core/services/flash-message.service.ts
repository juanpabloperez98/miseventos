import { Injectable } from '@angular/core';

export type FlashMessageType = 'success' | 'info' | 'error';

export interface FlashMessage {
  type: FlashMessageType;
  text: string;
}

/**
 * One-shot message handed from one page to the next one (e.g. "Evento creado" after saving and
 * navigating to the detail). The destination page consumes it, so it is shown only once.
 */
@Injectable({ providedIn: 'root' })
export class FlashMessageService {
  private pending: FlashMessage | null = null;

  set(type: FlashMessageType, text: string): void {
    this.pending = { type, text };
  }

  consume(): FlashMessage | null {
    const message = this.pending;
    this.pending = null;
    return message;
  }
}
