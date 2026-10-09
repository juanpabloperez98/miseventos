import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-site-footer',
  imports: [RouterLink],
  template: `
    <footer class="footer">
      <div class="footer__inner">
        <div>
          <p class="footer__brand">Mis Eventos</p>
          <p class="footer__tagline">Descubre, organiza y vive tus eventos.</p>
        </div>
        <nav aria-label="Enlaces del pie de página">
          <a routerLink="/events">Eventos</a>
        </nav>
        <small class="footer__copy">&copy; {{ currentYear }} Mis Eventos</small>
      </div>
    </footer>
  `,
  styles: `
    @use 'mixins' as mx;

    .footer {
      margin-top: var(--space-8);
      border-top: var(--border-width) solid var(--color-border);
      background: var(--color-surface);
      color: var(--color-text-muted);

      &__inner {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        justify-content: space-between;
        gap: var(--space-4);
        padding-block: var(--space-6);

        @include mx.container;
      }

      &__brand {
        font-weight: var(--font-weight-bold);
        color: var(--color-text);
      }

      &__copy {
        flex-basis: 100%;

        @include mx.respond-to(md) {
          flex-basis: auto;
        }
      }

      a {
        font-weight: var(--font-weight-semibold);
      }
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SiteFooter {
  protected readonly currentYear = new Date().getFullYear();
}
