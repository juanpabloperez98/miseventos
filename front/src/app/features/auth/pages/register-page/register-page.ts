import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { switchMap, tap } from 'rxjs';

import { AuthService } from '../../../../core/auth/auth.service';
import { describeApiError, toApiError } from '../../../../core/http/api-error';
import { FlashMessageService } from '../../../../core/services/flash-message.service';
import { Alert } from '../../../../shared/components/alert/alert';
import { Button } from '../../../../shared/components/button/button';
import { FormField } from '../../../../shared/components/form-field/form-field';
import { compareWithSibling, notBlank } from '../../../../shared/utils/validators';

const PASSWORD_MIN = 8;
const PASSWORD_MAX = 128;

@Component({
  selector: 'app-register-page',
  imports: [ReactiveFormsModule, RouterLink, Alert, Button, FormField],
  templateUrl: './register-page.html',
  styleUrl: '../auth-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RegisterPage {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);
  private readonly flashMessages = inject(FlashMessageService);

  protected readonly submitting = signal(false);
  protected readonly error = signal<string | null>(null);

  protected readonly form = inject(NonNullableFormBuilder).group({
    name: ['', [Validators.required, notBlank, Validators.maxLength(120)]],
    email: ['', [Validators.required, Validators.email, Validators.maxLength(255)]],
    password: [
      '',
      [Validators.required, Validators.minLength(PASSWORD_MIN), Validators.maxLength(PASSWORD_MAX)],
    ],
    confirmPassword: [
      '',
      [Validators.required, compareWithSibling('password', 'same', 'passwordMismatch')],
    ],
  });

  protected readonly confirmMessages = { passwordMismatch: 'Las contraseñas no coinciden.' };

  constructor() {
    this.form.controls.password.valueChanges
      .pipe(takeUntilDestroyed())
      .subscribe(() => this.form.controls.confirmPassword.updateValueAndValidity());
  }

  protected submit(): void {
    if (this.submitting()) {
      return;
    }
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const { name, email, password } = this.form.getRawValue();
    const credentials = { email: email.trim(), password };
    this.submitting.set(true);
    this.error.set(null);
    let registered = false;

    this.auth
      .register({ name: name.trim(), ...credentials })
      .pipe(
        tap(() => (registered = true)),
        switchMap(() => this.auth.login(credentials)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (user) => {
          this.flashMessages.set('success', `¡Te damos la bienvenida, ${user.name}!`);
          void this.router.navigateByUrl('/events');
        },
        error: (error: unknown) => this.handleError(error, registered),
      });
  }

  private handleError(error: unknown, registered: boolean): void {
    this.submitting.set(false);
    if (registered) {
      this.flashMessages.set(
        'info',
        'Tu cuenta se creó correctamente. Inicia sesión para continuar.',
      );
      void this.router.navigateByUrl('/auth/login');
      return;
    }
    const apiError = toApiError(error);
    if (apiError.status === 409) {
      this.form.controls.email.setErrors({ server: 'Este correo ya está registrado.' });
      this.form.controls.email.markAsTouched();
    }
    for (const [field, messages] of Object.entries(apiError.fieldErrors)) {
      this.form.get(field)?.setErrors({ server: messages.join(' ') });
    }
    this.error.set(describeApiError(apiError));
  }
}
