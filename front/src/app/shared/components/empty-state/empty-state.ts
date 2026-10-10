import { ChangeDetectionStrategy, Component, input } from '@angular/core';

@Component({
  selector: 'app-empty-state',
  template: `
    <div class="panel">
      <span class="icon" aria-hidden="true">∅</span>
      <h2 class="title">{{ title() }}</h2>
      @if (message()) {
        <p class="message">{{ message() }}</p>
      }
      <div class="actions"><ng-content /></div>
    </div>
  `,
  styleUrl: '../state-panel/state-panel.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class EmptyState {
  readonly title = input.required<string>();
  readonly message = input<string>();
}
