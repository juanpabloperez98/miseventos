import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'inverse';
export type ButtonSize = 'md' | 'sm';

@Component({
  // eslint-disable-next-line @angular-eslint/component-selector -- attribute selector keeps native semantics.
  selector: 'button[appButton], a[appButton]',
  template: `
    @if (loading()) {
      <span class="spinner" aria-hidden="true"></span>
    }
    <ng-content />
  `,
  styleUrl: './button.scss',
  host: {
    '[class]': 'classes()',
    '[attr.aria-busy]': 'loading() || null',
  },
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Button {
  readonly variant = input<ButtonVariant>('primary');
  readonly size = input<ButtonSize>('md');
  readonly loading = input(false);
  readonly block = input(false);

  protected readonly classes = computed(
    () => `btn btn--${this.variant()} btn--${this.size()}` + (this.block() ? ' btn--block' : ''),
  );
}
