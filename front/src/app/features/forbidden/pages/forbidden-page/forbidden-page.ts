import { ChangeDetectionStrategy, Component, computed, inject, input } from '@angular/core';
import { RouterLink } from '@angular/router';

import { FlashMessageService } from '../../../../core/services/flash-message.service';
import { Button } from '../../../../shared/components/button/button';

const DEFAULT_REASON = 'No tienes permiso para acceder a esta página.';

/**
 * Access denied (authenticated user without the required role). Rendered at the requested URL by a
 * fallback route (see events.routes.ts), which provides the reason through its route `data`.
 * A guard redirecting here may provide it through the flash message instead.
 */
@Component({
  selector: 'app-forbidden-page',
  imports: [RouterLink, Button],
  template: `
    <section class="forbidden" aria-labelledby="forbidden-title">
      <p class="forbidden__code" aria-hidden="true">403</p>
      <h1 id="forbidden-title">Acceso denegado</h1>
      <p class="forbidden__text" role="alert">{{ message() }}</p>
      <div class="forbidden__actions">
        <a appButton routerLink="/events">Ver eventos</a>
        <a appButton variant="secondary" routerLink="/profile">Ir a mi perfil</a>
      </div>
    </section>
  `,
  styles: `
    @use 'mixins' as mx;

    :host {
      display: block;

      @include mx.container;
    }

    .forbidden {
      max-width: 36rem;
      margin-inline: auto;
      text-align: center;

      &__code {
        font-size: var(--font-size-4xl);
        font-weight: var(--font-weight-bold);
        color: var(--color-danger);
      }

      &__text {
        margin-block: var(--space-4) var(--space-5);
        color: var(--color-text-muted);
      }

      &__actions {
        display: flex;
        flex-wrap: wrap;
        justify-content: center;
        gap: var(--space-3);
      }
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ForbiddenPage {
  /** Route `data.reason`, bound by `withComponentInputBinding()`. */
  readonly reason = input<string>();

  private readonly flashReason = inject(FlashMessageService).consume()?.text;
  protected readonly message = computed(() => this.reason() ?? this.flashReason ?? DEFAULT_REASON);
}
