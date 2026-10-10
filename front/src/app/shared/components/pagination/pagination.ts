import { ChangeDetectionStrategy, Component, computed, input, output } from '@angular/core';

type PageItem = { kind: 'page'; page: number } | { kind: 'gap'; key: string };

const SIBLINGS = 1;

@Component({
  selector: 'app-pagination',
  templateUrl: './pagination.html',
  styleUrl: './pagination.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Pagination {
  readonly page = input.required<number>();
  readonly pages = input.required<number>();
  readonly label = input('Paginación');
  readonly pageChange = output<number>();

  protected readonly items = computed<PageItem[]>(() => {
    const current = this.page();
    const last = this.pages();
    const first = Math.max(2, current - SIBLINGS);
    const end = Math.min(last - 1, current + SIBLINGS);

    const items: PageItem[] = [{ kind: 'page', page: 1 }];
    if (first > 2) {
      items.push({ kind: 'gap', key: 'start' });
    }
    for (let page = first; page <= end; page++) {
      items.push({ kind: 'page', page });
    }
    if (end < last - 1) {
      items.push({ kind: 'gap', key: 'end' });
    }
    if (last > 1) {
      items.push({ kind: 'page', page: last });
    }
    return items;
  });

  protected go(page: number): void {
    if (page >= 1 && page <= this.pages() && page !== this.page()) {
      this.pageChange.emit(page);
    }
  }
}
