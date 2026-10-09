import { ChangeDetectionStrategy, Component, input } from '@angular/core';

export type AlertType = 'success' | 'info' | 'error';

/**
 * Inline message for confirmations and operation errors. Errors use `role="alert"` (assertive);
 * confirmations and information use `role="status"` (polite).
 */
@Component({
  selector: 'app-alert',
  template: `<ng-content />`,
  styles: `
    :host {
      display: block;
      padding: var(--space-3) var(--space-4);
      border: var(--border-width) solid;
      border-left-width: 4px;
      border-radius: var(--radius-md);
      font-weight: var(--font-weight-medium);
    }

    :host(.alert--success) {
      border-color: var(--color-success);
      background: var(--color-success-subtle);
      color: #14532d;
    }

    :host(.alert--info) {
      border-color: var(--color-info);
      background: var(--color-info-subtle);
      color: #0c4a6e;
    }

    :host(.alert--error) {
      border-color: var(--color-danger);
      background: var(--color-danger-subtle);
      color: #7f1d1d;
    }
  `,
  host: {
    '[class]': "'alert--' + type()",
    '[attr.role]': "type() === 'error' ? 'alert' : 'status'",
  },
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Alert {
  readonly type = input<AlertType>('info');
}
