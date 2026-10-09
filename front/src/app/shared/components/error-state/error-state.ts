import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';

import { Button } from '../button/button';

/** Error panel announced as an alert, with an optional retry action. */
@Component({
  selector: 'app-error-state',
  imports: [Button],
  template: `
    <div class="panel panel--error" role="alert">
      <span class="icon" aria-hidden="true">!</span>
      <h2 class="title">{{ title() }}</h2>
      <p class="message">{{ message() }}</p>
      <div class="actions">
        @if (retryable()) {
          <button appButton type="button" variant="secondary" (click)="retry.emit()">
            Reintentar
          </button>
        }
        <ng-content />
      </div>
    </div>
  `,
  styleUrl: '../state-panel/state-panel.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ErrorState {
  readonly title = input('No se pudo cargar la información');
  readonly message = input.required<string>();
  readonly retryable = input(true);
  readonly retry = output();
}
