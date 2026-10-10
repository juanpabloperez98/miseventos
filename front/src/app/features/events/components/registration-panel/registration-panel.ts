import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { RouterLink } from '@angular/router';

import { Alert } from '../../../../shared/components/alert/alert';
import { Button } from '../../../../shared/components/button/button';

export type RegistrationStatus = 'anonymous' | 'checking' | 'available' | 'registered' | 'closed';

@Component({
  selector: 'app-registration-panel',
  imports: [RouterLink, Alert, Button],
  template: `
    <section class="registration" aria-labelledby="registration-title">
      <h2 id="registration-title" class="registration__title">Inscripción</h2>

      @switch (status()) {
        @case ('anonymous') {
          <p class="registration__text">Inicia sesión para inscribirte en este evento.</p>
          <a appButton [routerLink]="['/auth/login']" [queryParams]="{ returnUrl: returnUrl() }">
            Iniciar sesión para inscribirme
          </a>
        }
        @case ('checking') {
          <p class="registration__text" role="status">Comprobando tu inscripción…</p>
        }
        @case ('registered') {
          <p class="registration__text registration__text--ok">
            <span aria-hidden="true">✓</span> Estás inscrito en este evento.
          </p>
          <a appButton variant="secondary" routerLink="/profile">Ver mis inscripciones</a>
        }
        @case ('closed') {
          <p class="registration__text">Este evento no admite inscripciones.</p>
        }
        @default {
          <p class="registration__text">Reserva tu plaza para asistir.</p>
          <button
            appButton
            type="button"
            [loading]="submitting()"
            [disabled]="submitting()"
            (click)="register.emit()"
          >
            {{ submitting() ? 'Inscribiendo…' : 'Inscribirme' }}
          </button>
        }
      }

      @if (error(); as message) {
        <app-alert type="error">{{ message }}</app-alert>
      }
    </section>
  `,
  styles: `
    .registration {
      display: grid;
      gap: var(--space-3);
      justify-items: start;
      padding: var(--space-4);
      border: var(--border-width) solid var(--color-border);
      border-radius: var(--radius-md);
      background: var(--color-surface);
    }

    .registration__title {
      font-size: var(--font-size-lg);
    }

    .registration__text {
      color: var(--color-text-muted);
    }

    .registration__text--ok {
      color: var(--color-success);
      font-weight: var(--font-weight-semibold);
    }

    app-alert {
      justify-self: stretch;
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RegistrationPanel {
  readonly status = input.required<RegistrationStatus>();
  readonly submitting = input(false);
  readonly error = input<string | null>(null);
  readonly returnUrl = input.required<string>();
  readonly register = output();
}
