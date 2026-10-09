import { provideZonelessChangeDetection } from '@angular/core';
import { type ComponentFixture, TestBed } from '@angular/core/testing';

import { Pagination } from './pagination';

describe('Pagination', () => {
  let fixture: ComponentFixture<Pagination>;
  let requested: number[];

  const element = () => fixture.nativeElement as HTMLElement;
  const labels = () =>
    [...element().querySelectorAll('.pagination__pages li')].map((item) =>
      item.textContent?.trim(),
    );

  async function render(page: number, pages: number): Promise<void> {
    fixture.componentRef.setInput('page', page);
    fixture.componentRef.setInput('pages', pages);
    await fixture.whenStable();
  }

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideZonelessChangeDetection()] });
    fixture = TestBed.createComponent(Pagination);
    requested = [];
    fixture.componentInstance.pageChange.subscribe((page) => requested.push(page));
  });

  it('should render nothing for a single page', async () => {
    await render(1, 1);
    expect(element().querySelector('nav')).toBeNull();
  });

  it('should show a window of pages around the current one', async () => {
    await render(5, 10);
    expect(labels()).toEqual(['1', '…', '4', '5', '6', '…', '10']);
    expect(element().querySelector('[aria-current="page"]')?.textContent?.trim()).toBe('5');
  });

  it('should emit the requested page and disable steps at the edges', async () => {
    await render(1, 3);
    const [previous, next] = [
      ...element().querySelectorAll<HTMLButtonElement>('.pagination__step'),
    ];

    expect(previous.disabled).toBeTrue();
    next.click();
    element().querySelector<HTMLButtonElement>('button[aria-label="Página 3"]')?.click();
    element().querySelector<HTMLButtonElement>('button[aria-label="Página 1"]')?.click();

    expect(requested).toEqual([2, 3]);
  });
});
