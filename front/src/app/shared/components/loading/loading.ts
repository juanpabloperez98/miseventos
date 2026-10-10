import { ChangeDetectionStrategy, Component, input } from '@angular/core';

@Component({
  selector: 'app-loading',
  template: `
    <div class="loading" role="status">
      <span class="spinner" aria-hidden="true"></span>
      <span>{{ label() }}</span>
    </div>
  `,
  styles: `
    .loading {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: var(--space-3);
      padding: var(--space-7) var(--space-4);
      color: var(--color-text-muted);
    }

    .spinner {
      width: 1.5rem;
      height: 1.5rem;
      border: 3px solid var(--color-primary-subtle);
      border-top-color: var(--color-primary);
      border-radius: var(--radius-full);
      animation: spin 0.8s linear infinite;
    }

    @keyframes spin {
      to {
        transform: rotate(360deg);
      }
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Loading {
  readonly label = input('Cargando…');
}
