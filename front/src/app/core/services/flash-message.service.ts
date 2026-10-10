import { Injectable } from '@angular/core';

export type FlashMessageType = 'success' | 'info' | 'error';

export interface FlashMessage {
  type: FlashMessageType;
  text: string;
}

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
