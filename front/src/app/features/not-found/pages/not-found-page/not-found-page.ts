import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-not-found-page',
  imports: [RouterLink],
  template: `
    <section class="not-found" aria-labelledby="not-found-title">
      <p class="not-found__code">404</p>
      <h1 id="not-found-title">Página no encontrada</h1>
      <p class="not-found__text">La página que buscas no existe o ha cambiado de dirección.</p>
      <a class="not-found__link" routerLink="/">Volver al inicio</a>
    </section>
  `,
  styles: `
    @use 'mixins' as mx;

    :host {
      display: block;

      @include mx.container;
    }

    .not-found {
      max-width: 36rem;
      margin-inline: auto;
      text-align: center;

      &__code {
        font-size: var(--font-size-4xl);
        font-weight: var(--font-weight-bold);
        color: var(--color-primary);
      }

      &__text {
        margin-block: var(--space-4) var(--space-5);
        color: var(--color-text-muted);
      }

      &__link {
        font-weight: var(--font-weight-semibold);
      }
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class NotFoundPage {}
